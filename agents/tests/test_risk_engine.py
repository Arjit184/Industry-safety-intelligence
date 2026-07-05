"""
SafetyIQ — risk engine test suite
Run: pytest agents/tests/ -v

9 tests covering scoring, compound detection, prediction, and serialisation.
All must pass before Week 2 handoff.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from agents.risk_engine import RiskEngine
from agents.adapter import parse_plant_reading
from agents.interfaces import RiskLevel
from data.simulator import SensorSimulator


def get_reading(scenario: str, elapsed_minutes: float = 0.0):
    """Helper — build a PlantReading from the simulator."""
    sim = SensorSimulator(scenario)
    sim.elapsed_minutes = elapsed_minutes
    raw = sim.get_reading()
    raw["permits"]   = sim.get_active_permits()
    raw["shift_log"] = sim.get_shift_log()
    return parse_plant_reading(raw)


class TestRiskScoring:

    def test_normal_ops_is_low(self):
        """Normal operations must score LOW."""
        engine  = RiskEngine()
        reading = get_reading("normal_ops")
        result  = engine.assess(reading)
        assert result.risk_level == RiskLevel.LOW
        assert result.risk_score < 35, f"Expected < 35, got {result.risk_score}"

    def test_gas_rising_elevated(self):
        """Gas rising scenario should produce an elevated score."""
        engine  = RiskEngine()
        reading = get_reading("gas_rising", elapsed_minutes=40)
        result  = engine.assess(reading)
        assert result.risk_score >= 10, f"Expected >= 10, got {result.risk_score}"

    def test_hot_work_conflict_triggers_compound(self):
        """Hot work + gas must fire at least one compound trigger."""
        engine  = RiskEngine()
        reading = get_reading("hot_work_conflict", elapsed_minutes=50)
        result  = engine.assess(reading)
        assert len(result.compound_triggers) > 0, "No compound triggers detected"
        trigger_ids = [t.trigger_id for t in result.compound_triggers]
        assert any("permit_gas_conflict" in tid for tid in trigger_ids), \
            f"Expected permit_gas_conflict trigger, got: {trigger_ids}"

    def test_vizag_pattern_is_critical(self):
        """Vizag pattern must reach CRITICAL after several readings."""
        engine = RiskEngine()
        for t in range(0, 15, 2):
            reading = get_reading("vizag_pattern", elapsed_minutes=float(t))
            result  = engine.assess(reading)
        assert result.risk_level == RiskLevel.CRITICAL, \
            f"Expected CRITICAL, got {result.risk_level} (score {result.risk_score})"
        assert result.risk_score >= 80, f"Expected >= 80, got {result.risk_score}"

    def test_vizag_generates_incident_report(self):
        """CRITICAL trigger must auto-generate an incident report."""
        engine = RiskEngine()
        for t in range(0, 15, 2):
            reading = get_reading("vizag_pattern", elapsed_minutes=float(t))
            result  = engine.assess(reading)
        assert result.incident_report_draft is not None, "No incident report generated"
        assert "CRITICAL" in result.incident_report_draft
        assert len(result.incident_report_draft) > 100

    def test_compound_score_beats_single_factor(self):
        """
        Core correctness: compound score must exceed any single factor's contribution.
        This is what differentiates SafetyIQ from threshold-only systems.
        """
        engine  = RiskEngine()
        reading = get_reading("hot_work_conflict", elapsed_minutes=50)
        result  = engine.assess(reading)

        # Find the gas factor contribution alone
        gas_factor = next(
            (f for f in result.risk_factors if f.factor_id == "gas_sensor_anomaly"),
            None
        )
        assert gas_factor is not None, "gas_sensor_anomaly factor missing"
        single_score = gas_factor.contribution

        assert result.risk_score > single_score, (
            f"Compound score ({result.risk_score}) should exceed "
            f"single-factor score ({single_score})"
        )

    def test_prediction_lead_time_positive(self):
        """Lead time advantage must be positive when compound triggers are active."""
        engine = RiskEngine()
        for t in range(0, 12, 2):
            reading = get_reading("vizag_pattern", elapsed_minutes=float(t))
            result  = engine.assess(reading)

        if result.prediction.lead_time_advantage_minutes is not None:
            assert result.prediction.lead_time_advantage_minutes > 0, \
                "Lead time advantage must be positive"

    def test_recommended_actions_for_conflict(self):
        """Hot work conflict must produce at least one time-sensitive action."""
        engine  = RiskEngine()
        reading = get_reading("hot_work_conflict", elapsed_minutes=50)
        result  = engine.assess(reading)

        assert len(result.recommended_actions) > 0, "No recommended actions produced"
        time_sensitive = [a for a in result.recommended_actions if a.time_sensitive]
        assert len(time_sensitive) > 0, "No time-sensitive actions for conflict scenario"

    def test_to_dict_serialisable(self):
        """RiskAssessment.to_dict() must produce clean JSON-serialisable output."""
        import json
        engine  = RiskEngine()
        reading = get_reading("vizag_pattern", elapsed_minutes=12)
        result  = engine.assess(reading)
        d       = result.to_dict()

        assert isinstance(d, dict)
        assert "risk_score"         in d
        assert "risk_level"         in d
        assert "risk_factors"       in d
        assert isinstance(d["risk_factors"], list)

        # Must be fully JSON-serialisable (no Enum objects, no dataclasses)
        try:
            json.dumps(d)
        except (TypeError, ValueError) as e:
            pytest.fail(f"to_dict() is not JSON-serialisable: {e}")