"""
SafetyIQ — adapter
Converts simulator JSON dict → typed PlantReading dataclass.
Member 2 owns this file.

Exposes TWO function names so both calling styles work:
  parse_plant_reading(raw)  ← Member 1's tests use this
  to_plant_reading(raw)     ← Member 2's backend uses this
Both do exactly the same thing.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.interfaces import (
    PlantReading, SensorReading, PermitRecord, ShiftContext,
    SensorStatus, PermitType,
)


def parse_plant_reading(raw: dict) -> PlantReading:
    """Convert simulator full_snapshot() dict → typed PlantReading."""

    # ── Sensors ───────────────────────────────────────────────────────────────
    sensors = {}
    for sid, s in raw.get("sensors", {}).items():
        try:    status = SensorStatus(s.get("status", "NORMAL"))
        except: status = SensorStatus.NORMAL
        sensors[sid] = SensorReading(
            sensor_id          = sid,
            sensor_type        = s.get("type", "UNKNOWN"),
            value              = s.get("value"),
            unit               = s.get("unit", ""),
            status             = status,
            threshold_warning  = float(s.get("threshold_warning", 0)),
            threshold_critical = float(s.get("threshold_critical", 0)),
            regulatory_ref     = s.get("regulatory_ref", ""),
        )

    # ── Permits ───────────────────────────────────────────────────────────────
    permits = []
    for p in raw.get("permits", []):
        try:    ptype = PermitType(p.get("type", "GENERAL"))
        except: ptype = PermitType.GENERAL
        permits.append(PermitRecord(
            permit_id       = p.get("permit_id", ""),
            permit_type     = ptype,
            zone            = p.get("zone", ""),
            description     = p.get("description", ""),
            issued_at       = p.get("issued_at", ""),
            valid_until     = p.get("valid_until", ""),
            risk_flag       = bool(p.get("risk_flag", False)),
            conflict_reason = p.get("conflict_reason"),
        ))

    # ── Shift ─────────────────────────────────────────────────────────────────
    sl = raw.get("shift_log", {})
    shift = ShiftContext(
        shift                      = sl.get("shift", "A"),
        supervisor                 = sl.get("supervisor", "Unknown"),
        in_changeover_window       = bool(sl.get("in_changeover_window", False)),
        handover_complete          = bool(sl.get("handover_complete", True)),
        workers_in_hazardous_zones = sl.get("workers_in_hazardous_zones", {}),
        fatigue_flag               = bool(sl.get("fatigue_flag", False)),
        notes                      = sl.get("notes", ""),
    )

    return PlantReading(
        timestamp       = raw.get("timestamp", ""),
        scenario        = raw.get("scenario", ""),
        elapsed_minutes = float(raw.get("elapsed_minutes", 0.0)),
        sensors         = sensors,
        active_permits  = permits,
        shift           = shift,
        raw_alerts      = raw.get("alerts", []),
    )


# Alias — Member 2's backend calls this name
to_plant_reading = parse_plant_reading