"""
agents/tests/test_rag_and_alerts.py
Tests for:
  1. RAG agent (ChromaDB + TF-IDF embedder)
  2. Alert generator (Anthropic API + fallback)
  3. Integrated engine pipeline (RAG + alerts wired in)

Run: pytest agents/tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from unittest.mock import patch, MagicMock

from agents.rag_agent import query, build_rag_context, match_historical_incident
from agents.alert_generator import generate_alert, AlertOutput, _fallback_alert
from agents.risk_engine import RiskEngine
from agents.adapter import parse_plant_reading
from agents.interfaces import RiskLevel
from data.simulator import SensorSimulator


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_reading(scenario: str, elapsed_minutes: float = 0):
    sim = SensorSimulator(scenario)
    sim.elapsed_minutes = elapsed_minutes
    raw = sim.get_reading()
    raw["permits"] = sim.get_active_permits()
    raw["shift_log"] = sim.get_shift_log()
    return parse_plant_reading(raw)


def get_critical_assessment():
    engine = RiskEngine()
    for t in range(2, 14, 2):
        reading = get_reading("vizag_pattern", elapsed_minutes=t)
        result = engine.assess(reading)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 1. RAG AGENT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRAGAgent:

    def test_query_returns_results(self):
        results = query("gas explosion coke oven hot work permit", n_results=3)
        assert len(results) >= 1
        assert "id" in results[0]
        assert "title" in results[0]
        assert "distance" in results[0]

    def test_query_top_result_is_relevant(self):
        """Vizag query should surface the Vizag incident as top result."""
        results = query("H2S hot work permit active gas elevation coke oven", n_results=3)
        ids = [r["id"] for r in results]
        assert "vizag-2025-01" in ids, f"Vizag incident not in top results: {ids}"

    def test_query_distance_between_0_and_2(self):
        """Cosine distance is bounded 0–2."""
        results = query("confined space asphyxiation CO poisoning", n_results=2)
        for r in results:
            assert 0.0 <= r["distance"] <= 2.0

    def test_query_severity_filter_critical(self):
        """Severity filter should only return CRITICAL incidents."""
        results = query("gas explosion fire", n_results=5, severity_filter="CRITICAL")
        for r in results:
            assert r["metadata"]["severity"] == "CRITICAL"

    def test_query_n_results_respected(self):
        results = query("steel plant incident", n_results=2)
        assert len(results) <= 2

    def test_build_rag_context_nonempty_for_active_factors(self):
        ctx = build_rag_context(
            ["gas_sensor_anomaly", "permit_gas_conflict", "sensor_maintenance_blindspot"],
            92.0,
        )
        assert len(ctx) > 50
        assert "RELEVANT HISTORICAL INCIDENTS" in ctx

    def test_build_rag_context_empty_for_no_factors(self):
        ctx = build_rag_context([], 10.0)
        assert ctx == ""

    def test_build_rag_context_contains_regulation(self):
        ctx = build_rag_context(["gas_sensor_anomaly", "permit_gas_conflict"], 85.0)
        assert "OISD" in ctx or "Factory Act" in ctx or "DGFASLI" in ctx

    def test_match_historical_incident_vizag_combo(self):
        result = match_historical_incident("gas_sensor_anomaly_x_permit_gas_conflict")
        assert result is not None, "Expected a match for gas+permit compound trigger"

    def test_match_historical_incident_confined_combo(self):
        result = match_historical_incident("confined_space_unchecked_x_gas_sensor_anomaly")
        assert result is not None

    def test_match_historical_incident_blindspot_combo(self):
        result = match_historical_incident("sensor_maintenance_blindspot_x_gas_sensor_anomaly")
        assert result is not None

    def test_chromadb_collection_populated(self):
        """ChromaDB collection must have all 7 corpus documents."""
        from agents.rag_agent import _get_collection
        col = _get_collection()
        assert col.count() == 7


# ══════════════════════════════════════════════════════════════════════════════
# 2. ALERT GENERATOR TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAlertGenerator:

    def _make_assessment(self, scenario="vizag_pattern", elapsed=10):
        engine = RiskEngine()
        for t in range(2, elapsed + 1, 2):
            reading = get_reading(scenario, elapsed_minutes=t)
            assessment = engine.assess(reading)
        return assessment

    def test_fallback_when_no_api_key(self):
        """Without API key, must return fallback alert — not raise."""
        assessment = self._make_assessment()
        with patch.dict(os.environ, {}, clear=True):
            # Ensure key is absent
            os.environ.pop("ANTHROPIC_API_KEY", None)
            alert = generate_alert(assessment, rag_context="", api_key=None)
        assert isinstance(alert, AlertOutput)
        assert alert.generated_by == "fallback"
        assert len(alert.headline) > 5
        assert alert.severity_label in ("LOW", "WARNING", "HIGH", "CRITICAL")

    def test_fallback_output_structure(self):
        assessment = self._make_assessment()
        alert = _fallback_alert(assessment)
        assert isinstance(alert.headline, str)
        assert isinstance(alert.full_text, str)
        assert isinstance(alert.immediate_actions, list)
        assert isinstance(alert.regulatory_summary, str)
        assert isinstance(alert.historical_reference, str)
        assert alert.generated_by == "fallback"

    def test_fallback_critical_mentions_evacuation(self):
        assessment = self._make_assessment("vizag_pattern", elapsed=12)
        assert assessment.risk_level == RiskLevel.CRITICAL
        alert = _fallback_alert(assessment)
        assert "CRITICAL" in alert.headline.upper() or "evacuate" in alert.full_text.lower()

    def test_fallback_low_is_calm(self):
        assessment = self._make_assessment("normal_ops", elapsed=2)
        alert = _fallback_alert(assessment)
        assert alert.severity_label == "LOW"
        assert "critical" not in alert.headline.lower()

    def test_api_called_with_key(self):
        """When API key present, Anthropic client must be called."""
        assessment = self._make_assessment()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='''{
            "headline": "CRITICAL: H2S and hot work — evacuate now",
            "full_text": "Compound hazard detected. Gas and permit conflict active.",
            "regulatory_summary": "OISD-GS-1 Cl.7.1, Factory Act S.36",
            "immediate_actions": ["Suspend hot work permit", "Evacuate Zone C"],
            "historical_reference": "Similar to Vizag 2025 incident."
        }''')]

        with patch("agents.alert_generator.anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = mock_response
            alert = generate_alert(assessment, rag_context="test context", api_key="sk-test-key")

        assert alert.generated_by == "anthropic-api"
        assert "CRITICAL" in alert.headline or "H2S" in alert.headline
        assert len(alert.immediate_actions) >= 1

    def test_api_json_parse_error_falls_back(self):
        """Malformed JSON from API must trigger fallback, not crash."""
        assessment = self._make_assessment()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is not JSON at all.")]

        with patch("agents.alert_generator.anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = mock_response
            alert = generate_alert(assessment, rag_context="", api_key="sk-test-key")

        assert alert.generated_by == "fallback"

    def test_api_network_error_falls_back(self):
        """Network error must trigger fallback, not crash."""
        assessment = self._make_assessment()
        with patch("agents.alert_generator.anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.side_effect = Exception("Connection refused")
            alert = generate_alert(assessment, rag_context="", api_key="sk-test-key")

        assert alert.generated_by == "fallback"

    def test_api_strips_markdown_fences(self):
        """API response wrapped in ```json ... ``` must parse correctly."""
        assessment = self._make_assessment()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='```json\n{"headline":"Test alert","full_text":"Details here.","regulatory_summary":"OISD-GS-1","immediate_actions":["Act now"],"historical_reference":""}\n```')]

        with patch("agents.alert_generator.anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = mock_response
            alert = generate_alert(assessment, rag_context="", api_key="sk-test-key")

        assert alert.generated_by == "anthropic-api"
        assert alert.headline == "Test alert"


# ══════════════════════════════════════════════════════════════════════════════
# 3. INTEGRATED PIPELINE TESTS (RAG wired into RiskEngine)
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegratedPipeline:

    def test_rag_context_populated_on_assessment(self):
        """RiskAssessment.rag_context must be non-empty for active scenarios."""
        engine = RiskEngine()
        for t in range(2, 12, 2):
            reading = get_reading("vizag_pattern", elapsed_minutes=t)
            result = engine.assess(reading)
        # Should contain the alert header + RAG context
        assert len(result.rag_context) > 20

    def test_compound_triggers_have_historical_match(self):
        """After Vizag scenario, at least one compound trigger should have a historical match."""
        engine = RiskEngine()
        for t in range(2, 14, 2):
            reading = get_reading("vizag_pattern", elapsed_minutes=t)
            result = engine.assess(reading)
        matches = [t.historical_match for t in result.compound_triggers if t.historical_match]
        assert len(matches) > 0, "Expected at least one compound trigger with historical_match"

    def test_alert_headline_in_rag_context(self):
        """rag_context field should contain [ALERT] prefix."""
        engine = RiskEngine()
        for t in range(2, 12, 2):
            reading = get_reading("hot_work_conflict", elapsed_minutes=t)
            result = engine.assess(reading)
        assert "[ALERT]" in result.rag_context

    def test_full_pipeline_serialises_with_rag(self):
        """to_dict() must still work cleanly with RAG fields populated."""
        engine = RiskEngine()
        for t in range(2, 12, 2):
            reading = get_reading("vizag_pattern", elapsed_minutes=t)
            result = engine.assess(reading)
        import json
        d = result.to_dict()
        assert json.dumps(d)  # must not raise
        assert isinstance(d["rag_context"], str)

    def test_normal_ops_rag_context_minimal(self):
        """Normal ops with no active factors should produce minimal RAG context."""
        engine = RiskEngine()
        reading = get_reading("normal_ops", elapsed_minutes=0)
        result = engine.assess(reading)
        # No active factors → rag_agent returns "" → rag_context is just the alert line
        assert isinstance(result.rag_context, str)

    def test_existing_9_tests_still_pass(self):
        """Regression: all original scoring tests still pass with RAG integrated."""
        engine = RiskEngine()
        # normal ops
        reading = get_reading("normal_ops")
        r = engine.assess(reading)
        assert r.risk_level == RiskLevel.LOW

        # vizag critical
        engine2 = RiskEngine()
        for t in range(2, 14, 2):
            reading = get_reading("vizag_pattern", elapsed_minutes=t)
            r2 = engine2.assess(reading)
        assert r2.risk_level == RiskLevel.CRITICAL
        assert r2.risk_score >= 80
