"""
SafetyIQ — IoT/SCADA sensor simulator
Member 1's version — uses SCENARIO_CONFIGS from settings.
"""

import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from typing import Dict, List, Any
from config.settings import SCENARIO_CONFIGS, SENSOR_THRESHOLDS


class SensorSimulator:
    SENSOR_LAYOUT = {
        "G-01": ("H2S",      "Zone A"),
        "G-02": ("CO",       "Zone A"),
        "G-03": ("CH4",      "Zone A"),
        "G-04": ("H2S",      "Zone B"),
        "G-05": ("CO",       "Zone B"),
        "G-06": ("CH4",      "Zone B"),
        "G-07": ("H2S",      "Zone C"),
        "G-08": ("CO",       "Zone C"),
        "G-09": ("CH4",      "Zone C"),
        "T-01": ("TEMP",     "Zone C"),
        "P-01": ("PRESSURE", "Zone C"),
        "O-01": ("O2",       "Zone C"),
    }

    def __init__(self, scenario: str = "normal_ops"):
        if scenario not in SCENARIO_CONFIGS:
            raise ValueError(f"Unknown scenario: {scenario}. Choose from {list(SCENARIO_CONFIGS.keys())}")
        self.scenario = scenario
        self.cfg = SCENARIO_CONFIGS[scenario]
        self.elapsed_minutes: float = 0.0
        self._rng = random.Random(42)

    def get_reading(self) -> Dict[str, Any]:
        sensors = {}
        alerts = []
        for sensor_id, (stype, zone) in self.SENSOR_LAYOUT.items():
            reading = self._simulate_sensor(sensor_id, stype, zone)
            sensors[sensor_id] = reading
            if reading["status"] not in ("NORMAL", "OFFLINE"):
                alerts.append({
                    "sensor_id": sensor_id,
                    "type": stype,
                    "status": reading["status"],
                    "value": reading["value"],
                })
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scenario": self.scenario,
            "elapsed_minutes": self.elapsed_minutes,
            "sensors": sensors,
            "alerts": alerts,
        }

    def get_active_permits(self) -> List[Dict[str, Any]]:
        permits = []
        t = self.elapsed_minutes
        if "HOT_WORK" in self.cfg["permits"]:
            gas_elevated = t > 5
            permits.append({
                "permit_id": "HW-2025-0112-003",
                "type": "HOT_WORK",
                "zone": "Zone C",
                "description": "Angle grinding — repair of coke oven door seal",
                "issued_at": "2025-01-12T05:30:00+05:30",
                "valid_until": "2025-01-12T13:30:00+05:30",
                "risk_flag": gas_elevated,
                "conflict_reason": "H2S elevated in Zone C" if gas_elevated else None,
            })
        if "CONFINED_SPACE" in self.cfg["permits"]:
            permits.append({
                "permit_id": "CS-2025-0112-001",
                "type": "CONFINED_SPACE",
                "zone": "Zone C",
                "description": "Tank inspection — pit below coke oven battery",
                "issued_at": "2025-01-12T06:00:00+05:30",
                "valid_until": "2025-01-12T14:00:00+05:30",
                "risk_flag": True,
                "conflict_reason": "No pre-entry gas check logged",
            })
        return permits

    def get_shift_log(self) -> Dict[str, Any]:
        t = self.elapsed_minutes
        changeover = self.cfg.get("shift_changeover", False)
        in_changeover = changeover and t >= 6
        handover_done = not (changeover and 6 <= t <= 12)
        return {
            "shift": "B",
            "supervisor": "R. Krishnamurthy",
            "in_changeover_window": in_changeover,
            "handover_complete": handover_done,
            "workers_in_hazardous_zones": {"Zone A": 4, "Zone B": 3, "Zone C": 6},
            "fatigue_flag": changeover and t > 10,
            "notes": "Night shift handover in progress" if in_changeover else "",
        }

    def full_snapshot(self) -> Dict:
        r = self.get_reading()
        r["permits"]   = self.get_active_permits()
        r["shift_log"] = self.get_shift_log()
        return r

    def _simulate_sensor(self, sensor_id, stype, zone):
        thresholds  = SENSOR_THRESHOLDS.get(stype, {})
        warn_thresh = thresholds.get("warning", 999)
        crit_thresh = thresholds.get("critical", 9999)
        idlh_thresh = thresholds.get("idlh")
        unit        = thresholds.get("unit", "")
        reg_ref     = thresholds.get("regulatory_ref", "")

        if sensor_id in self.cfg.get("offline_sensors", []):
            return {"type": stype, "value": None, "unit": unit, "status": "OFFLINE",
                    "threshold_warning": warn_thresh, "threshold_critical": crit_thresh,
                    "regulatory_ref": reg_ref}

        value = self._compute_value(sensor_id, stype, zone)

        if stype == "O2":
            status = "CRITICAL" if value <= thresholds.get("critical", 16.0) \
                     else "WARNING" if value <= warn_thresh else "NORMAL"
        else:
            status = ("IDLH"     if idlh_thresh and value >= idlh_thresh else
                      "CRITICAL" if value >= crit_thresh else
                      "WARNING"  if value >= warn_thresh else "NORMAL")

        return {"type": stype, "value": round(value, 2), "unit": unit, "status": status,
                "threshold_warning": warn_thresh, "threshold_critical": crit_thresh,
                "regulatory_ref": reg_ref}

    def _compute_value(self, sensor_id, stype, zone):
        base  = self.cfg.get("gas_base", {}).get(stype, 0.0)
        rate  = self.cfg.get("gas_rate", {}).get(stype, 0.0)
        t     = self.elapsed_minutes
        zf    = 1.4 if (zone == "Zone C" and self.scenario == "vizag_pattern") else 1.0
        noise = self._rng.uniform(-0.1, 0.1) * base

        if stype in ("H2S", "CO", "CH4"): value = base + (rate * t * zf) + noise
        elif stype == "TEMP":              value = 65.0 + (rate * t * 0.5 * zf) + noise
        elif stype == "PRESSURE":          value = 100.0 + (rate * t * 0.3 * zf) + noise
        elif stype == "O2":                value = 20.9 - (rate * t * 0.15 * zf) + noise
        else:                              value = base + noise
        return max(0.0, value)