"""
SafetyIQ — shared data contract
Member 1 owns the logic. Member 2 owns the adapter that produces PlantReading.
Member 3 consumes RiskAssessment via WebSocket JSON.
DO NOT rename fields without telling the whole team.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class RiskLevel(str, Enum):
    LOW      = "LOW"       # 0–34   green
    WARNING  = "WARNING"   # 35–59  amber
    HIGH     = "HIGH"      # 60–79  red
    CRITICAL = "CRITICAL"  # 80–100 flashing red


class SensorStatus(str, Enum):
    NORMAL   = "NORMAL"
    WARNING  = "WARNING"
    CRITICAL = "CRITICAL"
    IDLH     = "IDLH"     # immediately dangerous to life and health
    OFFLINE  = "OFFLINE"  # sensor under maintenance — blind spot


class PermitType(str, Enum):
    HOT_WORK       = "HOT_WORK"
    CONFINED_SPACE = "CONFINED_SPACE"
    ELECTRICAL     = "ELECTRICAL"
    GENERAL        = "GENERAL"


@dataclass
class SensorReading:
    sensor_id: str
    sensor_type: str
    value: Optional[float]   # None when OFFLINE
    unit: str
    status: SensorStatus
    threshold_warning: float
    threshold_critical: float
    regulatory_ref: str


@dataclass
class PermitRecord:
    permit_id: str
    permit_type: PermitType
    zone: str
    description: str
    issued_at: str
    valid_until: str
    risk_flag: bool
    conflict_reason: Optional[str]


@dataclass
class ShiftContext:
    shift: str
    supervisor: str
    in_changeover_window: bool
    handover_complete: bool
    workers_in_hazardous_zones: Dict[str, int]
    fatigue_flag: bool
    notes: str


@dataclass
class PlantReading:
    """Member 2 produces this. Member 1's risk engine consumes it."""
    timestamp: str
    scenario: str
    elapsed_minutes: float
    sensors: Dict[str, SensorReading]
    active_permits: List[PermitRecord]
    shift: ShiftContext
    raw_alerts: List[Dict]


@dataclass
class RiskFactor:
    factor_id: str
    active: bool
    weight: float
    contribution: float
    description: str
    regulatory_ref: Optional[str]
    evidence: List[str]


@dataclass
class CompoundTrigger:
    trigger_id: str
    factors_involved: List[str]
    multiplier: float
    description: str
    historical_match: Optional[str]
    regulatory_refs: List[str]


@dataclass
class PredictionWindow:
    minutes_to_next_threshold: Optional[float]
    next_threshold: Optional[RiskLevel]
    confidence: float
    basis: str
    single_sensor_minutes: Optional[float]
    lead_time_advantage_minutes: Optional[float]


@dataclass
class RecommendedAction:
    priority: int
    action: str
    rationale: str
    regulatory_basis: str
    zone: Optional[str]
    time_sensitive: bool


@dataclass
class RiskAssessment:
    """Member 1 produces this. Member 2 streams it. Member 3 renders it."""
    timestamp: str
    elapsed_minutes: float
    risk_score: float
    risk_level: RiskLevel
    previous_score: Optional[float]
    risk_factors: List[RiskFactor]
    compound_triggers: List[CompoundTrigger]
    prediction: PredictionWindow
    recommended_actions: List[RecommendedAction]
    rag_context: str = ""
    regulatory_violations: List[str] = field(default_factory=list)
    incident_report_draft: Optional[str] = None
    evacuation_triggered: bool = False

    def to_dict(self) -> Dict:
        import dataclasses
        def _convert(obj):
            if isinstance(obj, Enum): return obj.value
            if dataclasses.is_dataclass(obj):
                return {k: _convert(v) for k, v in dataclasses.asdict(obj).items()}
            if isinstance(obj, list): return [_convert(i) for i in obj]
            if isinstance(obj, dict): return {k: _convert(v) for k, v in obj.items()}
            return obj
        return _convert(self)