# agents/interfaces.py
# THE TEAM CONTRACT — every member imports from here.
# Member 1 owns this file. All other members build against it.
# DO NOT change field names without telling the whole team.

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class SensorReading:
    sensor_id: str          # e.g. "G-01"
    sensor_type: str        # "H2S", "CO", "CH4", "O2", "TEMP", "PRESSURE"
    zone: str               # e.g. "Z-01"
    zone_name: str          # e.g. "Coke Oven Battery A"
    value: Optional[float]  # None if offline
    unit: str               # "ppm", "% LEL", "%", "°C", "bar"
    status: str             # "SAFE", "WARNING", "DANGER", "CRITICAL", "OFFLINE"
    timestamp: str          # ISO 8601
    offline: bool = False


@dataclass
class Permit:
    permit_id: str          # e.g. "P-2024-1847"
    type: str               # "Hot Work", "Confined Space", "General Access"
    zone: str
    zone_name: str
    flagged: bool           # True = dangerous combination detected
    flag_reason: Optional[str]
    issued_at: str


@dataclass
class PlantSnapshot:
    """Raw plant state — produced by simulator, consumed by risk engine."""
    scenario: str
    scenario_label: str
    timestamp: str
    sensors: list[SensorReading]
    permits: list[Permit]
    shift_changeover_active: bool
    entry_check_logged: bool


@dataclass
class RiskFactor:
    name: str               # "gas_level", "active_hot_work", etc.
    score: float            # 0–100
    weight: float           # from COMPOUND_RISK_WEIGHTS
    contribution: float     # score × weight
    detail: str             # human-readable explanation


@dataclass
class RiskAssessment:
    """Fully processed output — what the WebSocket sends to frontend."""
    snapshot: PlantSnapshot
    compound_risk_score: float          # 0–100
    alert_level: str                    # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    predicted_breach_minutes: Optional[int]  # None = no breach predicted
    risk_factors: list[RiskFactor]
    rag_context: Optional[str]          # Relevant incident/regulation from RAG
    recommended_actions: list[str]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())