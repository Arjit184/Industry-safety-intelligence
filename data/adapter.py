# data/adapter.py
# Converts raw simulator dict → typed PlantSnapshot for Member 1's risk engine.
# This is the seam between Member 2 (data) and Member 1 (AI).

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.interfaces import PlantSnapshot, SensorReading, Permit
from data.simulator import build_snapshot


def dict_to_sensor(d: dict) -> SensorReading:
    return SensorReading(
        sensor_id=d["sensor_id"],
        sensor_type=d["sensor_type"],
        zone=d["zone"],
        zone_name=d["zone_name"],
        value=d["value"],
        unit=d["unit"],
        status=d["status"],
        timestamp=d["timestamp"],
        offline=d["offline"]
    )

def dict_to_permit(d: dict) -> Permit:
    return Permit(
        permit_id=d["permit_id"],
        type=d["type"],
        zone=d["zone"],
        zone_name=d["zone_name"],
        flagged=d["flagged"],
        flag_reason=d.get("flag_reason"),
        issued_at=d["issued_at"]
    )

def snapshot_to_typed(raw: dict) -> PlantSnapshot:
    """Convert raw simulator output dict → typed PlantSnapshot."""
    return PlantSnapshot(
        scenario=raw["scenario"],
        scenario_label=raw["scenario_label"],
        timestamp=raw["timestamp"],
        sensors=[dict_to_sensor(s) for s in raw["sensors"]],
        permits=[dict_to_permit(p) for p in raw["permits"]],
        shift_changeover_active=raw["shift_changeover_active"],
        entry_check_logged=raw["entry_check_logged"]
    )

def get_typed_snapshot(scenario: str) -> PlantSnapshot:
    """One-call convenience — get typed snapshot directly."""
    return snapshot_to_typed(build_snapshot(scenario))


if __name__ == "__main__":
    snap = get_typed_snapshot("vizag_pattern")
    print(f"Scenario: {snap.scenario_label}")
    print(f"Sensors: {len(snap.sensors)} ({sum(1 for s in snap.sensors if s.offline)} offline)")
    print(f"Permits: {len(snap.permits)} ({sum(1 for p in snap.permits if p.flagged)} flagged)")
    print(f"Shift changeover: {snap.shift_changeover_active}")
    print(f"Entry check logged: {snap.entry_check_logged}")
    print("\nCritical sensors:")
    for s in snap.sensors:
        if s.status in ("CRITICAL", "DANGER", "OFFLINE"):
            print(f"  {s.sensor_id} ({s.sensor_type}): {s.value} {s.unit} — {s.status}")