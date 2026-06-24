# main.py — SafetyIQ FastAPI Backend
# REST + WebSocket — sends full RiskAssessment to frontend
# Run: uvicorn main:app --reload

import asyncio, json, sys, os
from datetime import datetime, timezone
from dataclasses import asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import ZONES, SENSOR_THRESHOLDS, VIZAG_INCIDENT
from data.simulator import SCENARIOS, build_snapshot
from data.adapter import snapshot_to_typed
from agents.risk_engine import assess_risk

app = FastAPI(
    title="SafetyIQ — Industrial Safety Intelligence",
    description="Compound risk detection for zero-harm plant operations",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def full_assessment(scenario: str) -> dict:
    """Build raw snapshot → typed → risk assessment → serializable dict."""
    raw = build_snapshot(scenario)
    typed = snapshot_to_typed(raw)
    assessment = assess_risk(typed)
    return {
        "scenario": scenario,
        "scenario_label": raw["scenario_label"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "compound_risk_score": assessment.compound_risk_score,
        "alert_level": assessment.alert_level,
        "predicted_breach_minutes": assessment.predicted_breach_minutes,
        "risk_factors": [
            {
                "name": f.name, "score": f.score, "weight": f.weight,
                "contribution": f.contribution, "detail": f.detail
            }
            for f in assessment.risk_factors
        ],
        "recommended_actions": assessment.recommended_actions,
        "sensors": raw["sensors"],
        "permits": raw["permits"],
        "summary": raw["summary"],
        "shift_changeover_active": raw["shift_changeover_active"],
        "entry_check_logged": raw["entry_check_logged"],
    }


# ─── REST ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "online", "project": "SafetyIQ", "version": "1.0.0"}

@app.get("/scenarios")
def list_scenarios():
    return {
        k: {
            "label": v["label"],
            "compound_risk_score": v["compound_risk_score"],
            "predicted_breach_minutes": v["predicted_breach_minutes"]
        }
        for k, v in SCENARIOS.items()
    }

@app.get("/assessment/{scenario}")
def get_assessment(scenario: str):
    if scenario not in SCENARIOS:
        return JSONResponse(status_code=404, content={"error": f"Unknown scenario: {scenario}"})
    return full_assessment(scenario)

@app.get("/zones")
def get_zones():
    return ZONES

@app.get("/thresholds")
def get_thresholds():
    return SENSOR_THRESHOLDS

@app.get("/vizag")
def get_vizag():
    return VIZAG_INCIDENT


# ─── WebSocket — live streaming ──────────────────────────────────────────────

@app.websocket("/ws/stream/{scenario}")
async def stream(websocket: WebSocket, scenario: str):
    """
    Frontend connects: new WebSocket('ws://localhost:8000/ws/stream/vizag_pattern')
    Sends a full RiskAssessment every 2 seconds.
    """
    await websocket.accept()
    if scenario not in SCENARIOS:
        await websocket.send_json({"error": f"Unknown scenario: {scenario}"})
        await websocket.close()
        return
    try:
        while True:
            await websocket.send_text(json.dumps(full_assessment(scenario)))
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/escalation")
async def escalation_demo(websocket: WebSocket):
    """
    Judge demo endpoint — cycles through all 4 scenarios automatically.
    Shows the escalation from Normal → Vizag Pattern in real time.
    """
    await websocket.accept()
    scenarios = list(SCENARIOS.keys())
    idx = 0
    try:
        while True:
            scenario = scenarios[idx % len(scenarios)]
            data = full_assessment(scenario)
            data["_demo_step"] = idx + 1
            data["_next_scenario"] = scenarios[(idx + 1) % len(scenarios)]
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(3.0)
            idx += 1
    except WebSocketDisconnect:
        pass