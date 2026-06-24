# data/simulator.py — Realistic SCADA sensor data simulator
# Run: python3 data/simulator.py --scenario vizag_pattern [--stream]

import json, time, random, argparse, sys, os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SENSOR_THRESHOLDS, ZONES, VIZAG_INCIDENT


def jitter(value: float, pct: float = 0.05) -> float:
    return round(value * (1 + random.uniform(-pct, pct)), 2)

def classify(sensor: str, value: float) -> str:
    t = SENSOR_THRESHOLDS[sensor]
    if t.get("invert"):
        if value <= t["critical"]: return "CRITICAL"
        if value <= t["danger"]:   return "DANGER"
        if value <= t["warning"]:  return "WARNING"
        return "SAFE"
    else:
        if value >= t["critical"]: return "CRITICAL"
        if value >= t["danger"]:   return "DANGER"
        if value >= t["warning"]:  return "WARNING"
        return "SAFE"

def make_sensor(sensor, value, zone, sid, offline=False):
    return {
        "sensor_id": sid, "sensor_type": sensor,
        "zone": zone, "zone_name": ZONES.get(zone, zone),
        "value": None if offline else jitter(value),
        "unit": SENSOR_THRESHOLDS[sensor]["unit"],
        "status": "OFFLINE" if offline else classify(sensor, jitter(value)),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "offline": offline
    }

def make_permit(pid, ptype, zone, flagged=False, reason=None):
    return {
        "permit_id": pid, "type": ptype,
        "zone": zone, "zone_name": ZONES.get(zone, zone),
        "flagged": flagged,
        "flag_reason": reason or ("Hot work active in gas-elevated zone" if flagged else None),
        "issued_at": datetime.now(timezone.utc).isoformat()
    }

SCENARIOS = {
    "normal": {
        "label": "Normal Operations",
        "compound_risk_score": 5,
        "predicted_breach_minutes": None,
        "shift_changeover_active": False,
        "entry_check_logged": True,
        "sensors": [
            ("H2S", 2.1, "Z-01", "G-01"), ("CO", 18.0, "Z-01", "G-02"),
            ("CH4", 4.0, "Z-02", "G-03"), ("O2", 20.8, "Z-08", "G-04"),
            ("TEMP", 31.0, "Z-03", "T-01"), ("PRESSURE", 1.8, "Z-05", "P-01"),
        ],
        "permits": [],
    },
    "gas_rising": {
        "label": "Gas Levels Rising — Early Warning Window",
        "compound_risk_score": 34,
        "predicted_breach_minutes": 82,
        "shift_changeover_active": False,
        "entry_check_logged": True,
        "sensors": [
            ("H2S", 8.7, "Z-01", "G-01"), ("CO", 42.0, "Z-01", "G-02"),
            ("CH4", 7.0, "Z-02", "G-03"), ("O2", 20.4, "Z-08", "G-04"),
            ("TEMP", 38.0, "Z-03", "T-01"), ("PRESSURE", 2.3, "Z-05", "P-01"),
        ],
        "permits": [],
    },
    "hot_work_gas": {
        "label": "Hot Work + Elevated Gas — Compound Risk Forming",
        "compound_risk_score": 61,
        "predicted_breach_minutes": 29,
        "shift_changeover_active": False,
        "entry_check_logged": True,
        "sensors": [
            ("H2S", 14.2, "Z-01", "G-01"), ("CO", 78.0, "Z-01", "G-02"),
            ("CH4", 18.0, "Z-02", "G-03"), ("O2", 19.2, "Z-08", "G-04"),
            ("TEMP", 51.0, "Z-03", "T-01"), ("PRESSURE", 3.8, "Z-05", "P-01"),
        ],
        "permits": [
            make_permit("P-2024-1847", "Hot Work", "Z-02", flagged=True),
            make_permit("P-2024-1851", "Confined Space", "Z-08"),
            make_permit("P-2024-1852", "General Access", "Z-03"),
        ],
    },
    "vizag_pattern": {
        "label": "⚠ Vizag Pattern Detected — ALL 5 PRECURSORS ACTIVE",
        "compound_risk_score": 91,
        "predicted_breach_minutes": VIZAG_INCIDENT["lead_time_minutes"],  # 47
        "shift_changeover_active": True,
        "entry_check_logged": False,
        "sensors": [
            ("H2S", 38.0, "Z-01", "G-01"), ("CO", 160.0, "Z-01", "G-02"),
            ("CH4", 35.0, "Z-02", "G-03"), ("O2", 17.5, "Z-08", "G-04"),
            ("TEMP", 67.0, "Z-03", "T-01"), ("PRESSURE", 5.8, "Z-05", "P-01"),
            # G-09 OFFLINE — the blind spot that killed 8 people
            ("H2S", None, "Z-04", "G-09"),
        ],
        "permits": [
            make_permit("P-2024-1847", "Hot Work", "Z-04", flagged=True),
            make_permit("P-2024-1851", "Confined Space", "Z-08", flagged=True,
                        reason="O2 at 17.5% — below safe entry threshold (19.5%)"),
            make_permit("P-2024-1852", "General Access", "Z-03"),
        ],
    }
}

def build_snapshot(scenario_key: str) -> dict:
    s = SCENARIOS[scenario_key]
    sensors = []
    for row in s["sensors"]:
        offline = row[1] is None
        sensors.append(make_sensor(row[0], row[1] if not offline else 0, row[2], row[3], offline))

    critical = sum(1 for r in sensors if r["status"] == "CRITICAL")
    offline  = sum(1 for r in sensors if r["offline"])

    return {
        "scenario": scenario_key,
        "scenario_label": s["label"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "compound_risk_score": s["compound_risk_score"],
        "predicted_breach_minutes": s["predicted_breach_minutes"],
        "alert_level": (
            "CRITICAL" if s["compound_risk_score"] >= 75 else
            "HIGH"     if s["compound_risk_score"] >= 50 else
            "MEDIUM"   if s["compound_risk_score"] >= 25 else "LOW"
        ),
        "sensors": sensors,
        "permits": s["permits"],
        "shift_changeover_active": s["shift_changeover_active"],
        "entry_check_logged": s["entry_check_logged"],
        "summary": {
            "total_sensors": len(sensors),
            "offline_sensors": offline,
            "critical_readings": critical,
            "active_permits": len(s["permits"]),
            "flagged_permits": sum(1 for p in s["permits"] if p["flagged"]),
        }
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), default="vizag_pattern")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    if args.stream:
        print(f"Streaming: {args.scenario}  (Ctrl+C to stop)\n")
        while True:
            print(json.dumps(build_snapshot(args.scenario), indent=2))
            print("─" * 60)
            time.sleep(args.interval)
    else:
        print(json.dumps(build_snapshot(args.scenario), indent=2))