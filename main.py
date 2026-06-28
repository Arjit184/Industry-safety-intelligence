"""
SafetyIQ — FastAPI backend
Member 2 owns this file.

Endpoints:
  GET  /                          health check
  GET  /scenarios                 list all 4 scenarios
  GET  /assessment/{scenario}     full RiskAssessment JSON  ← matches previous session
  GET  /api/snapshot/{scenario}   alias for above
  GET  /zones                     plant zone definitions
  GET  /thresholds                sensor thresholds + regulatory sources
  GET  /vizag                     Vizag incident precursor data
  WS   /ws/stream/{scenario}      live stream (2s interval)
  WS   /ws/escalation             auto-cycles all 4 scenarios (judge demo mode)

Run:
  uvicorn main:app --reload --port 8000
"""

import json, asyncio, sys, os
from datetime import datetime
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import INCIDENT_SCENARIOS, PLANT_ZONES, SENSOR_THRESHOLDS
from data.simulator import SensorSimulator
from data.adapter import to_plant_reading

app = FastAPI(title="SafetyIQ API", version="1.0.0")

# Scenario name aliases — maps frontend names to backend names
SCENARIO_ALIASES = {
    "hot_work_gas": "hot_work_conflict",  # Member 3 uses this name
}
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_connections: Dict[str, Set[WebSocket]] = {}

# Graceful fallback if Member 1's engine isn't ready yet
try:
    from agents.risk_engine import RiskEngine
    _engine_available = True
    print("✓ Risk engine loaded")
except ImportError:
    _engine_available = False
    print("⚠  Risk engine not found — streaming raw simulator data (Week 1 mode)")


def _process(raw: dict, engine=None) -> dict:
    if engine:
        reading    = to_plant_reading(raw)
        assessment = engine.assess(reading)
        payload    = assessment.to_dict()
        payload["sensors"]        = raw.get("sensors", {})
        payload["active_permits"] = raw.get("permits", [])
        payload["shift"]          = raw.get("shift_log", {})
        payload["scenario"]       = raw.get("scenario", "")
        return payload
    return raw


# ── REST ─────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {
        "status": "ok", "service": "SafetyIQ",
        "timestamp": datetime.now().isoformat(),
        "risk_engine_loaded": _engine_available,
        "scenarios": list(INCIDENT_SCENARIOS.keys()),
    }


@app.get("/scenarios")
def list_scenarios():
    return {
        name: {
            "description":       sc["description"],
            "duration_minutes":  sc["duration_minutes"],
            "active_permits":    len(sc.get("active_permits", [])),
            "has_incidents":     bool(sc.get("incidents")),
            "offline_sensors":   sc.get("maintenance_offline", []),
        }
        for name, sc in INCIDENT_SCENARIOS.items()
    }


@app.get("/assessment/{scenario}")
@app.get("/api/snapshot/{scenario}")     # alias kept for compatibility
def get_assessment(scenario: str):
    scenario = SCENARIO_ALIASES.get(scenario, scenario)
    if scenario not in INCIDENT_SCENARIOS:
        return {"error": f"Unknown scenario '{scenario}'",
                "valid": list(INCIDENT_SCENARIOS.keys())}
    engine = RiskEngine() if _engine_available else None
    sim    = SensorSimulator(scenario)
    return _process(sim.full_snapshot(), engine)


@app.get("/zones")
def get_zones():
    return {
        zid: {
            "name":                 z.name,
            "description":          z.description,
            "hazardous_area_class": z.hazardous_area_class,
            "sensors":              z.sensors,
            "position":             {"x": z.x, "y": z.y, "w": z.width, "h": z.height},
        }
        for zid, z in PLANT_ZONES.items()
    }


@app.get("/thresholds")
def get_thresholds():
    return {
        stype: {
            "unit":           t.unit,
            "normal_max":     t.normal_max,
            "warning":        t.warning,
            "critical":       t.critical,
            "idlh":           t.idlh,
            "twa_limit":      t.twa_limit,
            "description":    t.description,
            "regulatory_ref": t.regulatory_ref,
        }
        for stype, t in SENSOR_THRESHOLDS.items()
    }


@app.get("/vizag")
def get_vizag():
    """Vizag incident precursor data — used by Member 4 in the demo."""
    sc = INCIDENT_SCENARIOS["vizag_pattern"]
    return {
        "incident":         "Visakhapatnam Steel Plant, Coke Oven Battery 3",
        "date":             "12 January 2025",
        "fatalities":       8,
        "injuries":         14,
        "precursor_signals": sc["incidents"],
        "compound_lead_time_minutes": 145,
        "single_sensor_alert_minutes": 156,
        "all_five_precursors": [
            "H2S trending upward in Zone C for 73 minutes",
            "Collector main pressure above warning threshold",
            "G-09 offline for calibration — blind spot in Zone C",
            "Hot work permit PTW-047 active in Zone C",
            "Shift B/C changeover without gas trend briefing",
        ],
        "regulatory_violations": [
            "OISD-GS-1 Clause 6.3 — hot work in elevated H2S zone",
            "OISD-GS-1 Clause 7.1 — PTW not suspended on pressure exceedance",
            "Factory Act S.36(1)(a) — no pre-entry atmospheric test",
            "DGFASLI OM-2023-11 Clause 4.3 — PTW not cross-checked against live readings",
            "DGFASLI OM-2023-11 Clause 6.1 — no backup detector when G-09 offline",
        ],
    }


# ── WebSockets ────────────────────────────────────────────────────────────────

@app.websocket("/ws/stream/{scenario}")
async def stream(websocket: WebSocket, scenario: str):
    """
    Live stream — one reading every 2 real seconds (10× sim time).
    Frontend: const ws = new WebSocket('ws://localhost:8000/ws/stream/vizag_pattern')
    """
    scenario = SCENARIO_ALIASES.get(scenario, scenario)
    if scenario not in INCIDENT_SCENARIOS:
        await websocket.close(code=4004, reason=f"Unknown scenario: {scenario}")
        return

    await websocket.accept()
    _connections.setdefault(scenario, set()).add(websocket)

    sim    = SensorSimulator(scenario)
    engine = RiskEngine() if _engine_available else None
    limit  = INCIDENT_SCENARIOS[scenario]["duration_minutes"]

    try:
        while sim.elapsed_minutes < limit:
            payload = _process(sim.full_snapshot(), engine)
            await websocket.send_text(json.dumps(payload, default=str))
            await asyncio.sleep(2.0)
            sim.elapsed_minutes += 2.0 * 10.0 / 60.0
        await websocket.send_text(json.dumps({"type": "scenario_complete", "scenario": scenario}))
    except WebSocketDisconnect:
        pass
    finally:
        _connections.get(scenario, set()).discard(websocket)


@app.websocket("/ws/escalation")
async def escalation(websocket: WebSocket):
    """
    Judge demo mode — auto-cycles through all 4 scenarios in order.
    Shows the full risk escalation from normal → CRITICAL in one stream.
    Frontend: const ws = new WebSocket('ws://localhost:8000/ws/escalation')
    """
    await websocket.accept()
    engine = RiskEngine() if _engine_available else None

    CYCLE = [
        ("normal_ops",       30),   # 30 sim-minutes of normal
        ("gas_rising",       45),   # 45 sim-minutes rising
        ("hot_work_conflict",60),   # 60 sim-minutes of conflict
        ("vizag_pattern",    30),   # 30 sim-minutes of CRITICAL
    ]

    try:
        for scenario, duration in CYCLE:
            sim       = SensorSimulator(scenario)
            sim_limit = duration

            await websocket.send_text(json.dumps({
                "type":     "scenario_start",
                "scenario": scenario,
                "description": INCIDENT_SCENARIOS[scenario]["description"],
            }))

            while sim.elapsed_minutes < sim_limit:
                payload = _process(sim.full_snapshot(), engine)
                payload["_escalation_scenario"] = scenario
                await websocket.send_text(json.dumps(payload, default=str))
                await asyncio.sleep(1.5)
                sim.elapsed_minutes += 1.5 * 10.0 / 60.0

        await websocket.send_text(json.dumps({"type": "escalation_complete"}))
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)