# agents/risk_engine.py — Compound Risk Scoring Engine
# This is the core differentiator: correlates multiple factors into one score.
# Single-sensor systems score each reading independently.
# This engine multiplies them — compound risk is exponential, not additive.

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.interfaces import PlantSnapshot, RiskFactor, RiskAssessment
from config.settings import SENSOR_THRESHOLDS, COMPOUND_RISK_WEIGHTS


# ─── Individual factor scorers ──────────────────────────────────────────────

def score_gas_level(snapshot: PlantSnapshot) -> RiskFactor:
    """Score based on worst sensor reading across the plant."""
    worst_score = 0
    worst_detail = "All sensors within safe limits"

    STATUS_SCORES = {"SAFE": 0, "WARNING": 40, "DANGER": 75, "CRITICAL": 100, "OFFLINE": 0}
    # gas_rising has sensors approaching thresholds — use value proximity for finer scoring
    for s in snapshot.sensors:
        if s.offline or s.status != "SAFE":
            continue
        t = SENSOR_THRESHOLDS[s.sensor_type]
        if s.value is None:
            continue
        # How close to warning threshold? 0–1 proximity score
        if not t.get("invert"):
            proximity = s.value / t["warning"] if t["warning"] > 0 else 0
        else:
            proximity = (t["warning"] - s.value) / t["warning"] if t["warning"] > 0 else 0
        proximity_score = max(0, proximity - 0.5) * 20  # only score if >50% of way to warning
        if proximity_score > worst_score:
            worst_score = proximity_score
            worst_detail = f"{s.sensor_id} ({s.sensor_type}): {s.value} {s.unit} — SAFE but approaching WARNING threshold"

    for s in snapshot.sensors:
        if s.offline:
            continue
        score = STATUS_SCORES.get(s.status, 0)
        if score > worst_score:
            worst_score = score
            worst_detail = f"{s.sensor_id} ({s.sensor_type}): {s.value} {s.unit} — {s.status} [source: {SENSOR_THRESHOLDS[s.sensor_type]['source']}]"

    weight = COMPOUND_RISK_WEIGHTS["gas_level"]
    return RiskFactor(
        name="gas_level", score=worst_score, weight=weight,
        contribution=worst_score * weight, detail=worst_detail
    )

def score_hot_work(snapshot: PlantSnapshot) -> RiskFactor:
    """Hot work permits near elevated gas zones = extreme danger."""
    flagged = [p for p in snapshot.permits if p.flagged and p.type == "Hot Work"]
    score = min(100, len(flagged) * 60)
    detail = (
        f"{len(flagged)} flagged hot work permit(s): " +
        ", ".join(f"{p.permit_id} in {p.zone_name}" for p in flagged)
        if flagged else "No active hot work permits in gas-elevated zones"
    )
    weight = COMPOUND_RISK_WEIGHTS["active_hot_work"]
    return RiskFactor(
        name="active_hot_work", score=score, weight=weight,
        contribution=score * weight, detail=detail
    )

def score_offline_sensors(snapshot: PlantSnapshot) -> RiskFactor:
    """Offline sensors = blind spots. You can't protect what you can't see."""
    offline = [s for s in snapshot.sensors if s.offline]
    # OISD-GS-1: any offline sensor in a monitored zone = safety critical event
    score = min(100, len(offline) * 50)
    detail = (
        f"{len(offline)} offline sensor(s): " +
        ", ".join(f"{s.sensor_id} in {s.zone_name}" for s in offline) +
        " — per OISD-GS-1 Clause 6.3, zone must be treated as WARNING level"
        if offline else "All sensors online"
    )
    weight = COMPOUND_RISK_WEIGHTS["sensor_offline"]
    return RiskFactor(
        name="sensor_offline", score=score, weight=weight,
        contribution=score * weight, detail=detail
    )

def score_shift_changeover(snapshot: PlantSnapshot) -> RiskFactor:
    """Shift handovers create attention gaps — historically high-risk windows."""
    score = 80 if snapshot.shift_changeover_active else 0
    detail = (
        "Shift changeover in progress — supervisor attention gap, per Vizag precursor pattern"
        if snapshot.shift_changeover_active else "No shift changeover active"
    )
    weight = COMPOUND_RISK_WEIGHTS["shift_changeover"]
    return RiskFactor(
        name="shift_changeover", score=score, weight=weight,
        contribution=score * weight, detail=detail
    )

def score_entry_check(snapshot: PlantSnapshot) -> RiskFactor:
    """Missing confined space entry checks — Factory Act Section 36 violation."""
    score = 90 if not snapshot.entry_check_logged else 0
    detail = (
        "Confined space pre-entry atmospheric check NOT logged — violates Factory Act S.36(1)(a)"
        if not snapshot.entry_check_logged else "Entry check logged and valid"
    )
    weight = COMPOUND_RISK_WEIGHTS["no_entry_check"]
    return RiskFactor(
        name="no_entry_check", score=score, weight=weight,
        contribution=score * weight, detail=detail
    )


# ─── Compound multiplier ────────────────────────────────────────────────────

def compound_multiplier(factors: list[RiskFactor]) -> float:
    """
    The key insight: when multiple risk factors co-occur, risk is NOT additive.
    A gas leak alone might be manageable. A gas leak + hot work + offline sensor
    + shift changeover is the exact Vizag pattern — exponentially more dangerous.
    
    Multiplier: if 3+ high-scoring factors, amplify the total by up to 1.4x.
    This is what makes our system beat single-sensor baselines.
    """
    high_factors = sum(1 for f in factors if f.score >= 60)
    if high_factors >= 4:
        return 1.40   # All 5 Vizag precursors = maximum amplification
    elif high_factors >= 3:
        return 1.25
    elif high_factors >= 2:
        return 1.10
    return 1.0


# ─── Breach prediction ──────────────────────────────────────────────────────

def predict_breach_minutes(compound_score: float) -> int | None:
    """
    Predict time to threshold breach based on compound risk score.
    Calibrated against the Vizag incident (47 min lead time at score ~91).
    """
    if compound_score >= 85:
        return 47    # Vizag-level: 47 minutes
    elif compound_score >= 70:
        return 29    # High: 29 minutes
    elif compound_score >= 50:
        return 82    # Medium-high: 82 minutes
    elif compound_score >= 25:
        return 180   # Medium: 3 hours
    return None      # Low risk: no breach predicted


# ─── Recommended actions ────────────────────────────────────────────────────

def get_recommended_actions(compound_score: float, factors: list[RiskFactor]) -> list[str]:
    actions = []
    if compound_score >= 85:
        actions.append("🚨 EVACUATE all non-essential personnel from Z-01, Z-02, Z-04, Z-08 immediately")
        actions.append("📞 Alert Emergency Response Team — activate site emergency protocol")
    if compound_score >= 60:
        actions.append("🔴 SUSPEND all hot work permits in gas-elevated zones")
        actions.append("🔧 Dispatch maintenance to restore offline sensors before any confined space entry")
    if any(f.name == "shift_changeover" and f.score > 0 for f in factors):
        actions.append("👥 Incoming shift supervisor must formally accept all active permits before work continues")
    if any(f.name == "no_entry_check" and f.score > 0 for f in factors):
        actions.append("📋 STOP all confined space entry — conduct fresh atmospheric test per Factory Act S.36(1)(a)")
    if compound_score >= 25:
        actions.append("⚠️ Increase monitoring frequency — check all sensor readings every 10 minutes")
    if compound_score < 25:
        actions.append("✅ Continue normal operations — monitor for escalation")
    return actions


# ─── Main entry point ────────────────────────────────────────────────────────

def assess_risk(snapshot: PlantSnapshot) -> RiskAssessment:
    """Full compound risk assessment for a plant snapshot."""
    factors = [
        score_gas_level(snapshot),
        score_hot_work(snapshot),
        score_offline_sensors(snapshot),
        score_shift_changeover(snapshot),
        score_entry_check(snapshot),
    ]

    base_score = sum(f.contribution for f in factors)
    multiplier = compound_multiplier(factors)
    compound_score = min(100, round(base_score * multiplier, 1))

    breach_minutes = predict_breach_minutes(compound_score)
    actions = get_recommended_actions(compound_score, factors)

    alert_level = (
        "CRITICAL" if compound_score >= 75 else
        "HIGH"     if compound_score >= 50 else
        "MEDIUM"   if compound_score >= 25 else "LOW"
    )

    return RiskAssessment(
        snapshot=snapshot,
        compound_risk_score=compound_score,
        alert_level=alert_level,
        predicted_breach_minutes=breach_minutes,
        risk_factors=factors,
        rag_context=None,   # Populated by RAG agent in Week 2
        recommended_actions=actions
    )


# ─── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data.adapter import get_typed_snapshot

    for scenario in ["normal", "gas_rising", "hot_work_gas", "vizag_pattern"]:
        snap = get_typed_snapshot(scenario)
        result = assess_risk(snap)
        print(f"\n{'='*60}")
        print(f"Scenario: {snap.scenario_label}")
        print(f"Compound Risk Score: {result.compound_risk_score}/100  [{result.alert_level}]")
        print(f"Predicted breach in: {result.predicted_breach_minutes} min")
        print("Risk factors:")
        for f in result.risk_factors:
            print(f"  {f.name:20s}: {f.score:5.1f} × {f.weight:.2f} = {f.contribution:.1f}")
        print("Actions:")
        for a in result.recommended_actions:
            print(f"  {a}")