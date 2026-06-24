"""
SafetyIQ — simulator → PlantReading adapter
Member 2 owns this file.

Converts the raw simulator dict into typed dataclasses
so Member 1's risk engine can consume it.

Usage:
    from data.adapter import to_plant_reading
    reading = to_plant_reading(sim.full_snapshot())
    assessment = risk_engine.assess(reading)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.interfaces import (
    PlantReading, SensorReading, PermitRecord, ShiftContext,
    SensorStatus, PermitType,
)


def _sensor_status(raw: str) -> SensorStatus:
    try:    return SensorStatus(raw)
    except: return SensorStatus.NORMAL


def _permit_type(raw: str) -> PermitType:
    try:    return PermitType(raw)
    except: return PermitType.GENERAL


def to_plant_reading(raw: dict) -> PlantReading:
    """Convert simulator full_snapshot() dict → typed PlantReading."""

    sensors = {
        sid: SensorReading(
            sensor_id          = sid,
            sensor_type        = s.get("type", "UNKNOWN"),
            value              = s.get("value"),
            unit               = s.get("unit", ""),
            status             = _sensor_status(s.get("status", "NORMAL")),
            threshold_warning  = float(s.get("threshold_warning", 0)),
            threshold_critical = float(s.get("threshold_critical", 0)),
            regulatory_ref     = s.get("regulatory_ref", ""),
        )
        for sid, s in raw.get("sensors", {}).items()
    }

    permits = [
        PermitRecord(
            permit_id       = p.get("permit_id", "UNKNOWN"),
            permit_type     = _permit_type(p.get("type", "GENERAL")),
            zone            = p.get("zone", ""),
            description     = p.get("description", ""),
            issued_at       = p.get("issued_at", ""),
            valid_until     = p.get("valid_until", ""),
            risk_flag       = bool(p.get("risk_flag", False)),
            conflict_reason = p.get("conflict_reason"),
        )
        for p in raw.get("permits", [])
    ]

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