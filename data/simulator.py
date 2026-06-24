"""
SafetyIQ — IoT / SCADA data simulator
Member 2 owns this file.

Generates realistic industrial sensor data with noise, drift, correlation,
and baked-in incident patterns for all 4 demo scenarios.

Run:
    python3 data/simulator.py --scenario vizag_pattern --stream
    python3 data/simulator.py --scenario normal_ops           # single snapshot
"""

import json, random, math, time, argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Generator, Optional
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SENSOR_THRESHOLDS, INCIDENT_SCENARIOS


class SensorSimulator:

    def __init__(self, scenario_name: str = "normal_ops", seed: int = 42):
        if scenario_name not in INCIDENT_SCENARIOS:
            raise ValueError(f"Unknown scenario '{scenario_name}'. "
                             f"Options: {list(INCIDENT_SCENARIOS.keys())}")
        random.seed(seed)
        self.scenario_name   = scenario_name
        self.scenario        = INCIDENT_SCENARIOS[scenario_name]
        self.elapsed_minutes = 0.0
        self.start_time      = datetime.now()
        self._values         = dict(self.scenario["base_values"])
        self._triggered      = set()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _noise(self, value: float, factor: float) -> float:
        return max(0.0, value + random.gauss(0, abs(value) * factor + 0.01))

    def _apply_drift(self, values: Dict, minutes: float) -> Dict:
        rates  = self.scenario.get("drift", {})
        result = {}
        for k, v in values.items():
            rate        = rates.get(k, 0.0)
            sine        = math.sin(minutes * 0.1) * rate * 0.3
            result[k]  = v + (rate + sine) * minutes
        return result

    def _correlate(self, values: Dict) -> Dict:
        """H2S leak → CO and pressure also rise; O2 drops in confined spaces."""
        h2s   = values.get("H2S", 0)
        base  = self.scenario["base_values"].get("H2S", 1)
        ratio = h2s / max(base, 0.1)
        out   = dict(values)
        if ratio > 1.5:
            out["CO"]       = values.get("CO", 0)       * (1 + (ratio - 1) * 0.40)
            out["PRESSURE"] = values.get("PRESSURE", 0) * (1 + (ratio - 1) * 0.25)
            out["O2"]       = values.get("O2", 20.8)    - (ratio - 1) * 0.30
        return out

    def _status(self, stype: str, value: float) -> str:
        t = SENSOR_THRESHOLDS[stype]
        if stype == "O2":
            if value >= t.normal_max: return "NORMAL"
            if value >= t.warning:    return "WARNING"
            if value >= t.critical:   return "CRITICAL"
            return "IDLH"
        else:
            if value <= t.normal_max: return "NORMAL"
            if value <= t.warning:    return "WARNING"
            if value <= t.critical:   return "CRITICAL"
            return "IDLH"

    @staticmethod
    def _sensor_ids(stype: str) -> List[str]:
        return {
            "H2S":      ["G-01", "G-04", "G-07"],
            "CO":       ["G-02", "G-05", "G-08"],
            "CH4":      ["G-03", "G-06", "G-09"],
            "O2":       ["G-10"],
            "TEMP":     ["T-01", "T-02"],
            "PRESSURE": ["P-01", "P-02"],
        }.get(stype, [])

    # ── Public API ────────────────────────────────────────────────────────────

    def get_reading(self) -> Dict:
        drifted  = self._apply_drift(self._values, self.elapsed_minutes)
        corr     = self._correlate(drifted)
        noisy    = {k: self._noise(v, self.scenario["noise_factor"]) for k, v in corr.items()}
        if "O2" in noisy:
            noisy["O2"] = max(15.0, min(23.5, noisy["O2"]))

        offline = self.scenario.get("maintenance_offline", [])
        reading = {
            "timestamp":       (self.start_time + timedelta(minutes=self.elapsed_minutes)).isoformat(),
            "scenario":        self.scenario_name,
            "elapsed_minutes": round(self.elapsed_minutes, 1),
            "sensors":         {},
            "alerts":          [],
        }

        for stype, thresh in SENSOR_THRESHOLDS.items():
            val    = noisy.get(stype, thresh.normal_max * 0.3)
            status = self._status(stype, val)

            for sid in self._sensor_ids(stype):
                is_off  = sid in offline
                out_val = None if is_off else round(val + random.gauss(0, val * 0.02), 2)

                reading["sensors"][sid] = {
                    "type":               stype,
                    "value":              out_val,
                    "unit":               thresh.unit,
                    "status":             "OFFLINE" if is_off else status,
                    "threshold_warning":  thresh.warning,
                    "threshold_critical": thresh.critical,
                    "regulatory_ref":     thresh.regulatory_ref,
                }

                if not is_off and status in ("CRITICAL", "IDLH"):
                    reading["alerts"].append({
                        "sensor_id":    sid,
                        "type":         f"SENSOR_{status}",
                        "value":        round(val, 2),
                        "unit":         thresh.unit,
                        "message":      f"{sid} ({stype}) at {val:.1f} {thresh.unit} — {status}",
                        "regulatory_ref": thresh.regulatory_ref,
                    })
                elif is_off and stype in ("H2S", "CO", "CH4"):
                    reading["alerts"].append({
                        "sensor_id": sid,
                        "type":      "SENSOR_OFFLINE",
                        "severity":  "WARNING",
                        "message":   f"{sid} ({stype}) OFFLINE — blind spot in coverage",
                    })

        for incident in self.scenario.get("incidents", []):
            key = f"{incident['at_minute']}_{incident['type']}"
            if self.elapsed_minutes >= incident["at_minute"] and key not in self._triggered:
                reading["alerts"].append({
                    "type":      incident["type"],
                    "message":   incident["message"],
                    "severity":  "CRITICAL" if "CRITICAL" in incident["type"] else "INFO",
                    "at_minute": incident["at_minute"],
                })
                self._triggered.add(key)

        return reading

    def get_active_permits(self) -> List[Dict]:
        permits = []
        for i, raw in enumerate(self.scenario.get("active_permits", [])):
            is_hot      = "HOT WORK"  in raw
            is_confined = "Confined"  in raw or "CONFINED" in raw
            conflict    = "CONFLICT"  in raw or "NO PRE-ENTRY" in raw
            zone = "Zone C" if "Zone C" in raw else "Zone B" if "Zone B" in raw else "Zone A"
            pid  = raw.split(":")[0].strip() if ":" in raw else f"PTW-{100+i}"
            permits.append({
                "permit_id":       pid,
                "type":            "HOT_WORK" if is_hot else "CONFINED_SPACE" if is_confined else "ELECTRICAL",
                "zone":            zone,
                "description":     raw,
                "issued_at":       (self.start_time - timedelta(hours=2)).isoformat(),
                "valid_until":     (self.start_time + timedelta(hours=6)).isoformat(),
                "risk_flag":       conflict,
                "conflict_reason": ("Gas readings exceed safe limit for hot work" if conflict and is_hot
                                    else "No pre-entry gas check logged" if conflict else None),
            })
        return permits

    def get_shift_log(self) -> Dict:
        now  = self.start_time + timedelta(minutes=self.elapsed_minutes)
        chng = now.hour >= 22 or now.hour < 1
        return {
            "shift":                    "B" if 14 <= now.hour < 22 else "C" if now.hour >= 22 or now.hour < 6 else "A",
            "supervisor":               "R. Venkatesh",
            "start_time":               now.replace(hour=22, minute=0, second=0).isoformat(),
            "handover_complete":        not chng,
            "in_changeover_window":     chng,
            "headcount":                24,
            "workers_in_hazardous_zones": {"Zone A": 3, "Zone B": 4, "Zone C": 2, "MAINTENANCE_BAY": 5},
            "notes": ("Battery 3 showing elevated readings since 21:30. "
                      "G-09 offline for calibration. PTW-047 active in Zone C."),
            "fatigue_flag": chng,
        }

    def full_snapshot(self) -> Dict:
        r = self.get_reading()
        r["permits"]   = self.get_active_permits()
        r["shift_log"] = self.get_shift_log()
        return r

    def stream(self, interval_seconds: float = 2.0,
               time_acceleration: float = 10.0) -> Generator[Dict, None, None]:
        limit = self.scenario["duration_minutes"]
        while self.elapsed_minutes < limit:
            yield self.full_snapshot()
            time.sleep(interval_seconds)
            self.elapsed_minutes += interval_seconds * time_acceleration / 60.0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="normal_ops",
                        choices=list(INCIDENT_SCENARIOS.keys()))
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args()

    sim = SensorSimulator(args.scenario)
    if args.stream:
        print(f"Streaming '{args.scenario}' (Ctrl-C to stop)\n")
        try:
            for r in sim.stream(interval_seconds=1.0):
                g07  = r["sensors"].get("G-07", {}).get("value", "—")
                co   = r["sensors"].get("G-08", {}).get("value", "—")
                alts = len(r["alerts"])
                print(f"t={r['elapsed_minutes']:6.1f}m | H2S={g07!s:>6} ppm | CO={co!s:>6} ppm | alerts={alts}")
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        print(json.dumps(sim.full_snapshot(), indent=2, default=str))