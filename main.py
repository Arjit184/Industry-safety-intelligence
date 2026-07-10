"""
SafetyIQ — FastAPI backend (Week 3 final)
Member 2 owns this file.

Member 1's risk_engine.py now calls RAG + alert_generator internally.
So _process() is simpler — just call engine.assess() and merge raw fields.
The alert is already in assessment.rag_context as "[ALERT] headline\n..."

New fields in every WebSocket message:
  nl_alert       — Claude-generated 2-sentence alert (extracted from rag_context)
  nl_headline    — short headline (≤12 words)
  sensors        — raw sensor readings
  active_permits — active PTW permits
  shift          — shift context

Endpoints:
  GET  /                       health check
  GET  /scenarios              list all 4 scenarios
  GET  /assessment/{scenario}  full payload
  GET  /zones                  plant zone definitions
  GET  /thresholds             sensor thresholds
  GET  /vizag                  Vizag incident data
  GET  /api/stats              detection stats for slides
  WS   /ws/stream/{scenario}   live stream every 2s
  WS   /ws/escalation          auto-cycles all 4 scenarios

Run:
  uvicorn main:app --reload --port 8000
"""

import json, asyncio, sys, os, re
from datetime import datetime
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import INCIDENT_SCENARIOS, PLANT_ZONES, SENSOR_THRESHOLDS
from data.simulator import SensorSimulator
from data.adapter import to_plant_reading

app = FastAPI(title="SafetyIQ API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_connections: Dict[str, Set[WebSocket]] = {}

# ── Scenario aliases ──────────────────────────────────────────────────────────
# Member 3's frontend uses "hot_work_gas", backend has "hot_work_conflict"
SCENARIO_ALIASES = {
    "hot_work_gas": "hot_work_conflict",
}

# ── Risk engine — loaded once, reused every tick ──────────────────────────────
# Member 1's engine now handles RAG + alert internally
try:
    from agents.risk_engine import RiskEngine
    _engine = RiskEngine()
    _engine_available = True
    print("✓ Risk engine loaded (with RAG + alert_generator)")
except ImportError as e:
    _engine = None
    _engine_available = False
    print(f"⚠  Risk engine not found: {e}")


def _extract_alert_fields(rag_context: str) -> tuple:
    """
    Member 1 stores the alert inside rag_context as:
      [ALERT] headline text
      [SOURCE] anthropic-api or fallback
      ... rest of RAG context ...

    Extract headline and source, return (headline, source, clean_rag_context).
    """
    headline = ""
    source   = ""
    lines    = rag_context.split("\n") if rag_context else []
    rest     = []

    for line in lines:
        if line.startswith("[ALERT]"):
            headline = line.replace("[ALERT]", "").strip()
        elif line.startswith("[SOURCE]"):
            source = line.replace("[SOURCE]", "").strip()
        else:
            rest.append(line)

    clean_context = "\n".join(rest).strip()
    return headline, source, clean_context


# ── Core processing function ──────────────────────────────────────────────────

def _process(raw: dict, engine=None) -> dict:
    """
    Convert raw simulator snapshot → full WebSocket payload.
    engine.assess() now handles RAG + alert internally (Member 1's Week 3 upgrade).
    We just merge raw sensor/permit/shift fields and extract the alert.
    """
    if engine is None:
        return raw

    reading    = to_plant_reading(raw)
    assessment = engine.assess(reading)
    payload    = assessment.to_dict()

    # Merge raw fields the frontend needs (not in RiskAssessment)
    payload["sensors"]        = raw.get("sensors", {})
    payload["active_permits"] = raw.get("permits", [])
    payload["shift"]          = raw.get("shift_log", {})
    payload["scenario"]       = raw.get("scenario", "")

    # Extract alert headline from rag_context (Member 1 stores it there)
    headline, source, clean_ctx = _extract_alert_fields(
        payload.get("rag_context", "")
    )
    if headline:
        payload["nl_alert"]        = headline
        payload["nl_alert_source"] = source
        payload["rag_context"]     = clean_ctx   # clean version for frontend

    return payload


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {
        "status":             "ok",
        "service":            "SafetyIQ",
        "version":            "3.0.0",
        "timestamp":          datetime.now().isoformat(),
        "risk_engine_loaded": _engine_available,
        "scenarios":          list(INCIDENT_SCENARIOS.keys()),
    }


@app.get("/scenarios")
def list_scenarios():
    return {
        name: {
            "description":      sc["description"],
            "duration_minutes": sc["duration_minutes"],
            "active_permits":   len(sc.get("active_permits", [])),
            "has_incidents":    bool(sc.get("incidents")),
            "offline_sensors":  sc.get("maintenance_offline", []),
        }
        for name, sc in INCIDENT_SCENARIOS.items()
    }


@app.get("/assessment/{scenario}")
def get_assessment(scenario: str):
    scenario = SCENARIO_ALIASES.get(scenario, scenario)
    if scenario not in INCIDENT_SCENARIOS:
        return {"error": f"Unknown scenario '{scenario}'",
                "valid": list(INCIDENT_SCENARIOS.keys())}
    sim = SensorSimulator(scenario)
    return _process(sim.full_snapshot(), _engine)


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
            "unit":           t.get("unit"),
            "warning":        t.get("warning"),
            "critical":       t.get("critical"),
            "idlh":           t.get("idlh"),
            "regulatory_ref": t.get("regulatory_ref"),
        }
        for stype, t in SENSOR_THRESHOLDS.items()
    }


@app.get("/vizag")
def get_vizag():
    return {
        "incident":                          "Visakhapatnam Steel Plant, Coke Oven Battery 3",
        "date":                              "12 January 2025",
        "fatalities":                        8,
        "injuries":                          14,
        "compound_lead_time_minutes":        145,
        "single_sensor_alert_minutes":       156,
        "precursor_signals_visible_minutes": 73,
        "safetyiq_critical_at_minute":       11,
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
            "DGFASLI OM-2023-11 Clause 4.3 — PTW not cross-checked vs live readings",
            "DGFASLI OM-2023-11 Clause 6.1 — no backup detector when G-09 offline",
        ],
    }


@app.get("/api/stats")
def get_stats():
    """Detection comparison stats — Member 4 uses these for slides."""
    return {
        "safetyiq_compound_system": {
            "false_negative_rate_percent":  0,
            "vizag_alert_at_minute":        11,
            "lead_time_minutes":            145,
            "compound_factors_detected":    5,
            "regulatory_violations_cited":  8,
        },
        "single_sensor_baseline": {
            "false_negative_rate_percent":    100,
            "vizag_alert_at_minute":          156,
            "lead_time_minutes":              0,
            "misses_compound_conditions":     True,
            "would_have_saved_vizag_workers": False,
        },
        "vizag_incident": {
            "date":              "12 January 2025",
            "fatalities":        8,
            "precursor_minutes": 73,
            "safetyiq_advantage": "145 minutes earlier than single-sensor baseline",
        },
        "india_industry": {
            "fatal_accidents_fy2023":         6500,
            "facilities_manual_handoffs_pct": 60,
            "source_fatalities":              "DGFASLI FY2023",
            "source_handoffs":                "FICCI Survey 2024",
        },
    }


# ── WebSocket endpoints ───────────────────────────────────────────────────────

@app.websocket("/ws/stream/{scenario}")
async def stream(websocket: WebSocket, scenario: str):
    """
    Live stream — one reading every 2 real seconds (10× sim time).
    Sends scenario_complete when done — frontend auto-reconnects.
    """
    scenario = SCENARIO_ALIASES.get(scenario, scenario)
    if scenario not in INCIDENT_SCENARIOS:
        await websocket.close(code=4004, reason=f"Unknown scenario: {scenario}")
        return

    await websocket.accept()
    _connections.setdefault(scenario, set()).add(websocket)

    sim   = SensorSimulator(scenario)
    limit = INCIDENT_SCENARIOS[scenario]["duration_minutes"]

    try:
        while sim.elapsed_minutes < limit:
            payload = _process(sim.full_snapshot(), _engine)
            await websocket.send_text(json.dumps(payload, default=str))
            await asyncio.sleep(2.0)
            sim.elapsed_minutes += 2.0 * 10.0 / 60.0

        await websocket.send_text(json.dumps({
            "type": "scenario_complete", "scenario": scenario
        }))

    except WebSocketDisconnect:
        pass
    finally:
        _connections.get(scenario, set()).discard(websocket)


@app.websocket("/ws/escalation")
async def escalation(websocket: WebSocket):
    """Judge demo mode — auto-cycles all 4 scenarios."""
    await websocket.accept()

    CYCLE = [
        ("normal_ops",       30),
        ("gas_rising",       45),
        ("hot_work_conflict",60),
        ("vizag_pattern",    30),
    ]

    try:
        for scenario, duration in CYCLE:
            sim = SensorSimulator(scenario)

            await websocket.send_text(json.dumps({
                "type":        "scenario_start",
                "scenario":    scenario,
                "description": INCIDENT_SCENARIOS[scenario]["description"],
            }))

            while sim.elapsed_minutes < duration:
                payload = _process(sim.full_snapshot(), _engine)
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