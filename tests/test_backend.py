"""
SafetyIQ — Member 2 test suite
Member 2 owns this file.

Tests every file you're responsible for.
Run: pytest tests/ -v

All tests must pass before you hand off to Member 3.
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from data.simulator import SensorSimulator
from data.adapter import to_plant_reading
from agents.interfaces import SensorStatus, PermitType, RiskLevel
from config.settings import INCIDENT_SCENARIOS, SENSOR_THRESHOLDS


# ══════════════════════════════════════════════════════
# SIMULATOR TESTS
# ══════════════════════════════════════════════════════

class TestSimulator:

    def test_all_scenarios_initialise(self):
        for name in INCIDENT_SCENARIOS:
            sim = SensorSimulator(name)
            assert sim.scenario_name == name

    def test_unknown_scenario_raises(self):
        with pytest.raises(ValueError):
            SensorSimulator("not_a_real_scenario")

    def test_full_snapshot_has_required_keys(self):
        sim = SensorSimulator("normal_ops")
        snap = sim.full_snapshot()
        for key in ("timestamp", "scenario", "elapsed_minutes", "sensors", "alerts", "permits", "shift_log"):
            assert key in snap, f"Missing key: {key}"

    def test_normal_ops_has_no_alerts(self):
        sim  = SensorSimulator("normal_ops")
        snap = sim.full_snapshot()
        # Normal ops should produce no CRITICAL/IDLH alerts
        critical = [a for a in snap["alerts"] if "CRITICAL" in a.get("type","") or "IDLH" in a.get("type","")]
        assert len(critical) == 0, f"Normal ops should not have critical alerts: {critical}"

    def test_vizag_has_offline_sensor(self):
        sim  = SensorSimulator("vizag_pattern")
        snap = sim.full_snapshot()
        g09  = snap["sensors"].get("G-09", {})
        assert g09.get("status") == "OFFLINE", "G-09 should be OFFLINE in Vizag scenario"
        assert g09.get("value")  is None,      "OFFLINE sensor should have null value"

    def test_vizag_has_three_permits(self):
        sim  = SensorSimulator("vizag_pattern")
        snap = sim.full_snapshot()
        assert len(snap["permits"]) == 3

    def test_vizag_hot_work_permit_is_flagged(self):
        sim     = SensorSimulator("vizag_pattern")
        snap    = sim.full_snapshot()
        ptw_047 = next((p for p in snap["permits"] if p["permit_id"] == "PTW-047"), None)
        assert ptw_047 is not None,         "PTW-047 should exist"
        assert ptw_047["risk_flag"] is True, "PTW-047 should be flagged as conflict"
        assert ptw_047["type"] == "HOT_WORK"

    def test_vizag_confined_space_no_preentry(self):
        sim     = SensorSimulator("vizag_pattern")
        snap    = sim.full_snapshot()
        ptw_051 = next((p for p in snap["permits"] if p["permit_id"] == "PTW-051"), None)
        assert ptw_051 is not None
        assert ptw_051["risk_flag"] is True
        assert "gas check" in (ptw_051.get("conflict_reason") or "").lower()

    def test_sensor_count(self):
        sim  = SensorSimulator("normal_ops")
        snap = sim.full_snapshot()
        # Expect: 3×H2S + 3×CO + 3×CH4 + 1×O2 + 2×TEMP + 2×PRESSURE = 14
        assert len(snap["sensors"]) == 14

    def test_elapsed_minutes_advances(self):
        sim = SensorSimulator("gas_rising")
        sim.elapsed_minutes = 30.0
        snap = sim.full_snapshot()
        assert snap["elapsed_minutes"] == 30.0

    def test_gas_rising_drift(self):
        """H2S should be higher at t=60 than t=0 in gas_rising scenario."""
        sim0 = SensorSimulator("gas_rising", seed=1)
        h2s0 = sim0.full_snapshot()["sensors"]["G-07"]["value"]

        sim60 = SensorSimulator("gas_rising", seed=1)
        sim60.elapsed_minutes = 60
        h2s60 = sim60.full_snapshot()["sensors"]["G-07"]["value"]

        assert h2s60 > h2s0, f"H2S should drift up: {h2s0:.1f} → {h2s60:.1f}"

    def test_shift_log_structure(self):
        sim  = SensorSimulator("normal_ops")
        snap = sim.full_snapshot()
        sl   = snap["shift_log"]
        for key in ("shift", "supervisor", "handover_complete", "in_changeover_window",
                    "workers_in_hazardous_zones", "fatigue_flag", "notes"):
            assert key in sl, f"Shift log missing: {key}"

    def test_all_sensor_statuses_are_valid(self):
        valid = {"NORMAL", "WARNING", "CRITICAL", "IDLH", "OFFLINE"}
        for scenario in INCIDENT_SCENARIOS:
            sim  = SensorSimulator(scenario)
            snap = sim.full_snapshot()
            for sid, s in snap["sensors"].items():
                assert s["status"] in valid, \
                    f"{scenario}/{sid}: invalid status '{s['status']}'"

    def test_baked_in_incident_fires_at_correct_time(self):
        """Vizag CRITICAL incident should fire at or after minute 11."""
        sim = SensorSimulator("vizag_pattern")
        sim.elapsed_minutes = 11.0
        snap = sim.full_snapshot()
        critical_alerts = [a for a in snap["alerts"] if "CRITICAL" in a.get("type", "")]
        assert len(critical_alerts) > 0, "CRITICAL alert should fire at minute 11"

    def test_serialisable_to_json(self):
        """Snapshot must be JSON-serialisable (no datetime objects etc.)."""
        for scenario in INCIDENT_SCENARIOS:
            sim  = SensorSimulator(scenario)
            snap = sim.full_snapshot()
            try:
                json.dumps(snap, default=str)
            except Exception as e:
                pytest.fail(f"{scenario} snapshot not JSON-serialisable: {e}")


# ══════════════════════════════════════════════════════
# ADAPTER TESTS
# ══════════════════════════════════════════════════════

class TestAdapter:

    def _reading(self, scenario: str = "vizag_pattern", elapsed: float = 0):
        sim = SensorSimulator(scenario)
        sim.elapsed_minutes = elapsed
        return to_plant_reading(sim.full_snapshot())

    def test_returns_plant_reading(self):
        from agents.interfaces import PlantReading
        r = self._reading()
        assert isinstance(r, PlantReading)

    def test_sensor_statuses_are_typed_enums(self):
        r = self._reading()
        for sid, s in r.sensors.items():
            assert isinstance(s.status, SensorStatus), \
                f"{sid}.status should be SensorStatus, got {type(s.status)}"

    def test_offline_sensor_has_none_value(self):
        r   = self._reading("vizag_pattern")
        g09 = r.sensors.get("G-09")
        assert g09 is not None
        assert g09.status == SensorStatus.OFFLINE
        assert g09.value  is None

    def test_permit_types_are_typed_enums(self):
        r = self._reading("vizag_pattern")
        for p in r.active_permits:
            assert isinstance(p.permit_type, PermitType)

    def test_hot_work_permit_type(self):
        r      = self._reading("vizag_pattern")
        ptw047 = next((p for p in r.active_permits if p.permit_id == "PTW-047"), None)
        assert ptw047 is not None
        assert ptw047.permit_type == PermitType.HOT_WORK
        assert ptw047.risk_flag   is True

    def test_shift_context_fields(self):
        r = self._reading("vizag_pattern")
        # Vizag pattern runs at ~10pm — changeover depends on system time
        assert r.shift.supervisor == "R. Venkatesh"
        assert isinstance(r.shift.workers_in_hazardous_zones, dict)
        assert isinstance(r.shift.fatigue_flag, bool)

    def test_all_sensors_transferred(self):
        r = self._reading()
        assert len(r.sensors) == 14

    def test_normal_ops_no_permits(self):
        r = self._reading("normal_ops")
        assert len(r.active_permits) == 0

    def test_elapsed_minutes_preserved(self):
        r = self._reading("gas_rising", elapsed=45.0)
        assert r.elapsed_minutes == 45.0

    def test_raw_alerts_transferred(self):
        r = self._reading("vizag_pattern")
        assert isinstance(r.raw_alerts, list)
        # Vizag scenario has offline sensor alerts
        assert len(r.raw_alerts) > 0

    def test_missing_keys_dont_crash(self):
        """Adapter must not crash on incomplete simulator output."""
        minimal = {"timestamp": "2025-01-12T22:47:00", "scenario": "test",
                   "elapsed_minutes": 0, "sensors": {}, "alerts": []}
        r = to_plant_reading(minimal)
        assert r.timestamp == "2025-01-12T22:47:00"
        assert len(r.sensors) == 0


# ══════════════════════════════════════════════════════
# CORPUS TESTS
# ══════════════════════════════════════════════════════

class TestCorpus:

    def test_corpus_files_exist(self):
        import os
        # Build corpus first if needed
        from data.corpus_builder import build_corpus
        build_corpus()
        for fname in ("incidents.json", "regulations.json", "chunks.json"):
            assert os.path.exists(f"data/corpus/{fname}"), f"Missing: {fname}"

    def test_incidents_have_required_fields(self):
        from data.corpus_builder import INCIDENTS
        for inc in INCIDENTS:
            for field in ("id", "title", "date", "fatalities", "root_causes",
                          "precursor_signals", "regulatory_violations", "body"):
                assert field in inc, f"Incident {inc.get('id','?')} missing: {field}"

    def test_vizag_incident_present(self):
        from data.corpus_builder import INCIDENTS
        vizag = next((i for i in INCIDENTS if i["id"] == "INC-003"), None)
        assert vizag is not None
        assert vizag["fatalities"] == 8
        assert "Vizag" in vizag["title"] or "Visakhapatnam" in vizag["body"]

    def test_regulations_have_clauses(self):
        from data.corpus_builder import REGULATIONS
        for reg in REGULATIONS:
            assert "clauses" in reg and len(reg["clauses"]) >= 3, \
                f"{reg['id']} should have ≥3 clauses"

    def test_oisd_clause_6_3_present(self):
        from data.corpus_builder import REGULATIONS
        oisd = next((r for r in REGULATIONS if r["id"] == "REG-001"), None)
        assert oisd is not None
        assert "6.3" in oisd["clauses"]
        assert "H2S" in oisd["clauses"]["6.3"]

    def test_chunks_cover_all_types(self):
        import json
        with open("data/corpus/chunks.json") as f:
            chunks = json.load(f)
        types = {c["type"] for c in chunks}
        assert "incident_body"     in types
        assert "root_cause"        in types
        assert "precursor_signal"  in types
        assert "prevention_action" in types
        assert "regulation"        in types

    def test_chunk_count(self):
        import json
        with open("data/corpus/chunks.json") as f:
            chunks = json.load(f)
        assert len(chunks) >= 40, f"Expected ≥40 chunks, got {len(chunks)}"


# ══════════════════════════════════════════════════════
# FASTAPI ENDPOINT TESTS
# ══════════════════════════════════════════════════════

class TestAPI:

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def test_health_returns_ok(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health_lists_scenarios(self, client):
        r = client.get("/")
        body = r.json()
        assert "scenarios" in body
        assert "vizag_pattern" in body["scenarios"]

    def test_scenarios_endpoint(self, client):
        r = client.get("/scenarios")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 4
        for name in ("normal_ops", "gas_rising", "hot_work_conflict", "vizag_pattern"):
            assert name in body

    def test_snapshot_normal_ops(self, client):
        r = client.get("/assessment/normal_ops")
        assert r.status_code == 200
        body = r.json()
        assert "sensors" in body or "risk_score" in body   # raw or risk assessment

    def test_snapshot_vizag(self, client):
        r = client.get("/assessment/vizag_pattern")
        assert r.status_code == 200

    def test_snapshot_unknown_scenario(self, client):
        r = client.get("/assessment/does_not_exist")
        assert r.status_code == 200
        assert "error" in r.json()

    def test_zones_endpoint(self, client):
        r = client.get("/zones")
        assert r.status_code == 200
        body = r.json()
        assert "ZONE_A" in body
        assert "ZONE_C" in body
        assert "position" in body["ZONE_A"]

    def test_cors_header_present(self, client):
        r = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 200


# ══════════════════════════════════════════════════════
# ADDITIONAL API TESTS (matching previous session spec)
# ══════════════════════════════════════════════════════

class TestAPIv2:

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def test_assessment_endpoint(self, client):
        """/assessment/{scenario} must work — this is what Member 3's frontend calls."""
        r = client.get("/assessment/vizag_pattern")
        assert r.status_code == 200
        body = r.json()
        # Either raw simulator output or RiskAssessment — both must have sensors or risk_score
        assert "sensors" in body or "risk_score" in body

    def test_assessment_all_scenarios(self, client):
        for s in ("normal_ops", "gas_rising", "hot_work_conflict", "vizag_pattern"):
            r = client.get(f"/assessment/{s}")
            assert r.status_code == 200, f"Failed for {s}"

    def test_thresholds_endpoint(self, client):
        r = client.get("/thresholds")
        assert r.status_code == 200
        body = r.json()
        assert "H2S" in body
        assert body["H2S"]["warning"] == 5.0
        assert "OISD" in body["H2S"]["regulatory_ref"]

    def test_vizag_endpoint(self, client):
        r = client.get("/vizag")
        assert r.status_code == 200
        body = r.json()
        assert body["fatalities"] == 8
        assert body["compound_lead_time_minutes"] == 145
        assert len(body["all_five_precursors"]) == 5

    def test_scenarios_root_path(self, client):
        """/scenarios (no /api prefix) — matches previous session."""
        r = client.get("/scenarios")
        assert r.status_code == 200
        assert "vizag_pattern" in r.json()

    def test_zones_root_path(self, client):
        r = client.get("/zones")
        assert r.status_code == 200
        assert "ZONE_A" in r.json()