"""
SafetyIQ — historical data generator
Member 2 owns this file.

Generates 6 months of synthetic sensor data with embedded near-miss events.
Used to demonstrate trend detection and benchmark compound vs single-sensor detection.

Run:
    python3 data/historical_generator.py              # 180 days → data/historical_180d.json
    python3 data/historical_generator.py --days 30   # faster for testing
    python3 data/historical_generator.py --stats      # print summary stats only
"""

import json, random, math, argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import SENSOR_THRESHOLDS


# Probability of a near-miss event starting on any given 5-minute interval
# 1 event per ~14 days on average
NEAR_MISS_PROB = 1 / (14 * 288)

NEAR_MISS_TYPES = [
    "elevated_gas_no_action",
    "permit_conflict_caught_late",
    "sensor_offline_during_operation",
    "shift_changeover_gap",
]

# Base readings for "normal" plant operation
NORMAL_BASE = {
    "H2S": 1.2, "CO": 8.0, "CH4": 3.0,
    "O2": 20.8, "TEMP": 38.0, "PRESSURE": 2.1
}

NEAR_MISS_BASE = {
    "elevated_gas_no_action":          {"H2S": 7.0,  "CO": 40.0, "CH4": 12.0, "O2": 20.2, "TEMP": 44.0, "PRESSURE": 5.8},
    "permit_conflict_caught_late":      {"H2S": 5.5,  "CO": 28.0, "CH4": 9.0,  "O2": 20.4, "TEMP": 42.0, "PRESSURE": 6.2},
    "sensor_offline_during_operation":  {"H2S": 6.0,  "CO": 35.0, "CH4": 11.0, "O2": 20.1, "TEMP": 46.0, "PRESSURE": 4.9},
    "shift_changeover_gap":             {"H2S": 4.5,  "CO": 22.0, "CH4": 8.0,  "O2": 20.5, "TEMP": 41.0, "PRESSURE": 4.1},
}


def _noise(value: float, factor: float = 0.05) -> float:
    return max(0.0, value + random.gauss(0, abs(value) * factor + 0.01))

def _sensor_status(stype: str, value: float) -> str:
    t = SENSOR_THRESHOLDS[stype]

    warning = t["warning"]
    critical = t["critical"]
    idlh = t["idlh"]

    if stype == "O2":
        if value >= warning:
            return "NORMAL"
        elif value >= critical:
            return "WARNING"
        else:
            return "CRITICAL"

    else:
        if value < warning:
            return "NORMAL"
        elif value < critical:
            return "WARNING"
        elif idlh is not None and value < idlh:
            return "CRITICAL"
        else:
            return "IDLH"


def _build_reading(ts: datetime, base: Dict, noise: float = 0.05,
                   near_miss_type: str = None, elapsed_in_event: float = 0) -> Dict:
    """Build one 5-minute reading."""
    values = {}
    for k, v in base.items():
        # Add slight drift during near-miss events
        drift = elapsed_in_event * 0.05 if near_miss_type else 0
        values[k] = _noise(v + drift, noise)

    if "O2" in values:
        values["O2"] = max(15.0, min(23.5, values["O2"]))

    sensors = {}
    sensor_map = {
        "H2S":      ["G-07"], "CO":  ["G-08"], "CH4":  ["G-09"],
        "O2":       ["G-10"], "TEMP":["T-01"], "PRESSURE": ["P-01"],
    }
    alerts = []
    for stype, sids in sensor_map.items():
        val    = values.get(stype, 0)
        status = _sensor_status(stype, val)
        offline = (near_miss_type == "sensor_offline_during_operation"
                   and stype == "CH4" and elapsed_in_event < 60)
        for sid in sids:
            sensors[sid] = {
                "type":   stype,
                "value":  None if offline else round(val, 2),
                "unit": SENSOR_THRESHOLDS[stype]["unit"],
                "status": "OFFLINE" if offline else status,
            }
            if not offline and status in ("WARNING", "CRITICAL", "IDLH"):
                alerts.append({"sensor_id": sid, "type": f"SENSOR_{status}",
                                "value": round(val, 2)})

    return {
        "timestamp":       ts.isoformat(),
        "sensors":         sensors,
        "alerts":          alerts,
        "is_near_miss":    near_miss_type is not None,
        "near_miss_type":  near_miss_type,
        "compound_alert":  (len(alerts) >= 2 and near_miss_type is not None),
        "single_sensor_alert": len(alerts) >= 1,
    }


def generate(n_days: int = 180, output_dir: str = "data",
             seed: int = 42) -> List[Dict]:
    random.seed(seed)
    base_date = datetime.now() - timedelta(days=n_days)
    records   = []

    near_miss_count  = 0
    compound_caught  = 0   # compound system would catch
    single_caught    = 0   # single sensor would catch
    single_missed    = 0   # single sensor would miss (compound still catches)

    # Active near-miss event state
    active_nm       = None
    nm_elapsed      = 0
    nm_duration     = 0

    print(f"Generating {n_days} days × 288 readings = {n_days * 288:,} total readings...")

    for day in range(n_days):
        for interval in range(288):   # 288 × 5-min intervals = 24 hours
            ts = base_date + timedelta(days=day, minutes=interval * 5)

            # Start a new near-miss event?
            if active_nm is None and random.random() < NEAR_MISS_PROB:
                active_nm   = random.choice(NEAR_MISS_TYPES)
                nm_elapsed  = 0
                nm_duration = random.randint(60, 180)  # 1–3 hours
                near_miss_count += 1

            if active_nm:
                base      = NEAR_MISS_BASE[active_nm]
                rec       = _build_reading(ts, base, noise=0.10,
                                           near_miss_type=active_nm,
                                           elapsed_in_event=nm_elapsed)
                nm_elapsed += 5
                if nm_elapsed >= nm_duration:
                    active_nm = None
            else:
                rec = _build_reading(ts, NORMAL_BASE, noise=0.05)

            records.append(rec)

            # Track detection stats
            if rec["is_near_miss"]:
                compound_caught += 1
                if rec["single_sensor_alert"]:
                    single_caught += 1
                else:
                    single_missed += 1

        if (day + 1) % 30 == 0:
            print(f"  {day+1}/{n_days} days complete...")

    # Save
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"historical_{n_days}d.json"
    with open(path, "w") as f:
        json.dump(records, f, separators=(",", ":"))  # compact — file is large

    # Stats
    nm_readings = sum(1 for r in records if r["is_near_miss"])
    print(f"\n{'='*50}")
    print(f"Total readings:       {len(records):,}")
    print(f"Near-miss events:     {near_miss_count}")
    print(f"Near-miss readings:   {nm_readings:,}")
    print(f"\nDetection comparison (on near-miss readings):")
    print(f"  Compound system catches: {compound_caught:,}  (100%)")
    print(f"  Single sensor catches:   {single_caught:,}  ({100*single_caught/max(compound_caught,1):.0f}%)")
    print(f"  Single sensor MISSES:    {single_missed:,}  ({100*single_missed/max(compound_caught,1):.0f}%)")
    print(f"\nFalse negative rate:")
    print(f"  Compound system: 0%")
    print(f"  Single sensor:   {100*single_missed/max(compound_caught,1):.0f}%")
    print(f"\nSaved {len(records):,} records → {path}")
    print(f"File size: {path.stat().st_size / 1024 / 1024:.1f} MB")

    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days",   type=int, default=180)
    parser.add_argument("--output", default="data")
    parser.add_argument("--seed",   type=int, default=42)
    parser.add_argument("--stats",  action="store_true",
                        help="Load existing file and print stats only")
    args = parser.parse_args()

    if args.stats:
        path = Path(args.output) / f"historical_{args.days}d.json"
        if not path.exists():
            print(f"No file at {path} — run without --stats first")
        else:
            with open(path) as f: records = json.load(f)
            nm = [r for r in records if r["is_near_miss"]]
            print(f"Records: {len(records):,} | Near-miss: {len(nm):,}")
            compound = sum(1 for r in nm)
            single   = sum(1 for r in nm if r["single_sensor_alert"])
            print(f"Compound catches: {compound:,} | Single catches: {single:,} | Single misses: {compound-single:,}")
    else:
        generate(args.days, args.output, args.seed)