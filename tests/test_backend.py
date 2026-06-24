# tests/test_backend.py
# Run: pytest tests/ -v

import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.simulator import build_snapshot, SCENARIOS
from data.adapter import snapshot_to_typed, get_typed_snapshot
from agents.risk_engine import assess_risk
from agents.interfaces import PlantSnapshot, RiskAssessment


# ─── Simulator tests ────────────────────────────────────────────────────────

def test_all_scenarios_produce_snapshots():
    for scenario in SCENARIOS:
        snap = build_snapshot(scenario)
        assert snap["scenario"] == scenario
        assert len(snap["sensors"]) > 0
        assert "compound_risk_score" in snap

def test_vizag_has_five_precursors():
    snap = build_snapshot("vizag_pattern")
    offline = [s for s in snap["sensors"] if s["offline"]]
    flagged = [p for p in snap["permits"] if p["flagged"]]
    assert len(offline) >= 1, "Vizag must have at least 1 offline sensor"
    assert len(flagged) >= 2, "Vizag must have at least 2 flagged permits"
    assert snap["shift_changeover_active"] is True
    assert snap["entry_check_logged"] is False

def test_normal_scenario_all_safe():
    snap = build_snapshot("normal")
    statuses = [s["status"] for s in snap["sensors"] if not s["offline"]]
    assert all(s == "SAFE" for s in statuses)

def test_vizag_score_highest():
    scores = {k: build_snapshot(k)["compound_risk_score"] for k in SCENARIOS}
    assert scores["vizag_pattern"] > scores["hot_work_gas"]
    assert scores["hot_work_gas"] > scores["gas_rising"]
    assert scores["gas_rising"] > scores["normal"]


# ─── Adapter tests ───────────────────────────────────────────────────────────

def test_adapter_produces_typed_snapshot():
    snap = get_typed_snapshot("vizag_pattern")
    assert isinstance(snap, PlantSnapshot)
    assert snap.scenario == "vizag_pattern"
    assert snap.shift_changeover_active is True
    assert snap.entry_check_logged is False

def test_adapter_sensors_typed():
    snap = get_typed_snapshot("vizag_pattern")
    for s in snap.sensors:
        assert s.sensor_id is not None
        assert s.status in ("SAFE", "WARNING", "DANGER", "CRITICAL", "OFFLINE")

def test_adapter_all_scenarios():
    for scenario in SCENARIOS:
        snap = get_typed_snapshot(scenario)
        assert isinstance(snap, PlantSnapshot)


# ─── Risk engine tests ───────────────────────────────────────────────────────

def test_risk_engine_produces_assessment():
    snap = get_typed_snapshot("vizag_pattern")
    result = assess_risk(snap)
    assert isinstance(result, RiskAssessment)
    assert 0 <= result.compound_risk_score <= 100

def test_compound_beats_single_factor():
    """THE KEY TEST: compound score must be higher than any single factor score alone."""
    snap = get_typed_snapshot("vizag_pattern")
    result = assess_risk(snap)
    max_single = max(f.score * f.weight for f in result.risk_factors)
    assert result.compound_risk_score > max_single, \
        "Compound score must exceed any single-factor contribution"

def test_vizag_is_critical():
    snap = get_typed_snapshot("vizag_pattern")
    result = assess_risk(snap)
    assert result.alert_level == "CRITICAL"
    assert result.compound_risk_score >= 75
    assert result.predicted_breach_minutes is not None

def test_normal_is_low():
    snap = get_typed_snapshot("normal")
    result = assess_risk(snap)
    assert result.alert_level == "LOW"
    assert result.predicted_breach_minutes is None

def test_all_scenarios_have_actions():
    for scenario in SCENARIOS:
        snap = get_typed_snapshot(scenario)
        result = assess_risk(snap)
        assert len(result.recommended_actions) > 0

def test_escalation_order():
    scores = {}
    for scenario in SCENARIOS:
        snap = get_typed_snapshot(scenario)
        result = assess_risk(snap)
        scores[scenario] = result.compound_risk_score
    assert scores["vizag_pattern"] > scores["hot_work_gas"] > scores["gas_rising"] > scores["normal"]


# ─── API integration test ───────────────────────────────────────────────────

def test_api_assessment_endpoint():
    from fastapi.testclient import TestClient
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from main import app
    client = TestClient(app)

    r = client.get("/assessment/vizag_pattern")
    assert r.status_code == 200
    data = r.json()
    assert data["alert_level"] == "CRITICAL"
    assert data["compound_risk_score"] >= 75
    assert len(data["risk_factors"]) == 5
    assert len(data["recommended_actions"]) > 0

def test_api_unknown_scenario():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    r = client.get("/assessment/fake_scenario")
    assert r.status_code == 404

def test_api_scenarios_list():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    r = client.get("/scenarios")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 4
    assert "vizag_pattern" in data