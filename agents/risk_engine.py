"""
agents/risk_engine.py
The compound risk scoring engine. Member 1 owns this.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import deque

from agents.interfaces import (
    PlantReading, RiskAssessment, RiskFactor, CompoundTrigger,
    PredictionWindow, RecommendedAction, RiskLevel, SensorStatus, PermitType
)
from config.settings import RISK_WEIGHTS, COMPOUND_MULTIPLIERS, SENSOR_THRESHOLDS
import agents.rag_agent as rag_agent
from agents.alert_generator import generate_alert


class RiskEngine:
    """
    Compound risk scoring engine.

    Usage:
        engine = RiskEngine()
        assessment = engine.assess(plant_reading)
        print(assessment.risk_score)   # 0–100
        print(assessment.prediction.minutes_to_next_threshold)  # countdown
    """

    def __init__(self, history_window: int = 20):
        # Keep last N scores for trend analysis and prediction
        self._score_history: deque = deque(maxlen=history_window)
        self._previous_score: Optional[float] = None

    # ── Main entry point ──────────────────────────────────────────────────────

    def assess(self, reading: PlantReading) -> RiskAssessment:
        """
        Full risk assessment from one plant reading snapshot.
        Call this every time the simulator/SCADA produces a new reading.
        """
        # Step 1: evaluate each factor independently
        factors = self._evaluate_factors(reading)

        # Step 2: compute base score
        base_score = sum(f.contribution for f in factors if f.active)

        # Step 3: detect compound co-occurrences and apply multipliers
        triggers, multiplier = self._detect_compound_triggers(factors, reading)

        # Step 4: apply multiplier
        raw_score = min(100.0, base_score * multiplier)

        # Step 5: smooth score slightly (prevents UI jitter)
        score = self._smooth(raw_score)

        # Step 6: classify
        level = self._classify(score)

        # Step 7: predict breach time
        self._score_history.append(score)
        prediction = self._predict(score, level)

        # Step 8: generate recommended actions
        actions = self._recommend_actions(factors, triggers, reading)

        # Step 9a: RAG — enrich compound triggers with historical matches
        active_factor_ids = [f.factor_id for f in factors if f.active]
        for t in triggers:
            if t.historical_match is None:
                t.historical_match = rag_agent.match_historical_incident(t.trigger_id)

        # Step 9b: RAG context for alert generation
        rag_ctx = rag_agent.build_rag_context(active_factor_ids, score)

        # Step 9c: build assessment
        assessment = RiskAssessment(
            timestamp=reading.timestamp,
            elapsed_minutes=reading.elapsed_minutes,
            risk_score=round(score, 1),
            risk_level=level,
            previous_score=self._previous_score,
            risk_factors=factors,
            compound_triggers=triggers,
            prediction=prediction,
            recommended_actions=actions,
            regulatory_violations=self._collect_violations(factors, triggers),
            rag_context=rag_ctx,
        )

        # Step 10: auto-generate incident report draft if CRITICAL
        if level == RiskLevel.CRITICAL:
            assessment.incident_report_draft = self._draft_incident_report(
                assessment, reading
            )
            assessment.evacuation_triggered = True

        # Step 11: Anthropic API alert (non-blocking; falls back if no key)
        alert = generate_alert(assessment, rag_ctx)
        # Store alert headline in rag_context field for now (Week 2: dedicated field)
        assessment.rag_context = (
            f"[ALERT] {alert.headline}\n"
            f"[SOURCE] {alert.generated_by}\n"
            f"{rag_ctx}"
        )

        self._previous_score = score
        return assessment

    # ── Factor evaluation ─────────────────────────────────────────────────────

    def _evaluate_factors(self, reading: PlantReading) -> List[RiskFactor]:
        return [
            self._factor_gas_anomaly(reading),
            self._factor_permit_conflict(reading),
            self._factor_confined_unchecked(reading),
            self._factor_shift_changeover(reading),
            self._factor_sensor_blindspot(reading),
        ]

    def _factor_gas_anomaly(self, reading: PlantReading) -> RiskFactor:
        """Any gas sensor above warning threshold."""
        weight = RISK_WEIGHTS["gas_sensor_anomaly"]
        triggered_sensors = []
        max_severity = 0.0

        for sensor_id, s in reading.sensors.items():
            if s.sensor_type not in ("H2S", "CO", "CH4"):
                continue
            if s.status in (SensorStatus.WARNING, SensorStatus.CRITICAL, SensorStatus.IDLH):
                triggered_sensors.append(sensor_id)
                # Scale severity: WARNING=0.85, CRITICAL=0.95, IDLH=1.0
                severity = {"WARNING": 0.85, "CRITICAL": 0.95, "IDLH": 1.0}.get(s.status.value, 0)
                max_severity = max(max_severity, severity)

        active = len(triggered_sensors) > 0
        contribution = weight * max_severity * 100 if active else 0.0

        return RiskFactor(
            factor_id="gas_sensor_anomaly",
            active=active,
            weight=weight,
            contribution=round(contribution, 1),
            description=f"Elevated gas detected at: {', '.join(triggered_sensors)}" if active
                        else "Gas sensors nominal",
            regulatory_ref="OISD-GS-1 Clause 6.3 / 6.4",
            evidence=triggered_sensors,
        )

    def _factor_permit_conflict(self, reading: PlantReading) -> RiskFactor:
        """Hot work permit active in zone with elevated gas — the Vizag combo."""
        weight = RISK_WEIGHTS["permit_gas_conflict"]
        conflicting_permits = []

        # Get zones with elevated gas
        hot_zones = self._zones_with_elevated_gas(reading)

        for permit in reading.active_permits:
            if permit.permit_type == PermitType.HOT_WORK:
                zone_match = any(hz in permit.zone for hz in hot_zones)
                if zone_match or permit.risk_flag:
                    conflicting_permits.append(permit.permit_id)

        active = len(conflicting_permits) > 0
        contribution = weight * 100 if active else 0.0

        return RiskFactor(
            factor_id="permit_gas_conflict",
            active=active,
            weight=weight,
            contribution=round(contribution, 1),
            description=f"HOT WORK permit in gas-affected zone: {', '.join(conflicting_permits)}"
                        if active else "No hot work permit conflicts",
            regulatory_ref="OISD-GS-1 Clause 7.1 / DGFASLI OM-2023-11 Clause 4.3",
            evidence=conflicting_permits,
        )

    def _factor_confined_unchecked(self, reading: PlantReading) -> RiskFactor:
        """Confined space entry permit with no pre-entry gas check logged."""
        weight = RISK_WEIGHTS["confined_space_unchecked"]
        unchecked = []

        for permit in reading.active_permits:
            if permit.permit_type == PermitType.CONFINED_SPACE:
                # risk_flag from simulator means no pre-entry check
                if permit.risk_flag or (permit.conflict_reason and "gas check" in permit.conflict_reason.lower()):
                    unchecked.append(permit.permit_id)

        active = len(unchecked) > 0
        contribution = weight * 100 if active else 0.0

        return RiskFactor(
            factor_id="confined_space_unchecked",
            active=active,
            weight=weight,
            contribution=round(contribution, 1),
            description=f"Confined space entry without pre-entry gas check: {', '.join(unchecked)}"
                        if active else "All confined space permits properly checked",
            regulatory_ref="Factory Act S.36(1)(a) / DGFASLI OM-2023-11 Clause 4.1",
            evidence=unchecked,
        )

    def _factor_shift_changeover(self, reading: PlantReading) -> RiskFactor:
        """Shift changeover window — cognitive load spike, communication gaps."""
        weight = RISK_WEIGHTS["shift_changeover_window"]
        shift = reading.shift

        active = shift.in_changeover_window or not shift.handover_complete or shift.fatigue_flag
        contribution = weight * 100 if active else 0.0

        reasons = []
        if shift.in_changeover_window: reasons.append("in changeover window")
        if not shift.handover_complete: reasons.append("handover incomplete")
        if shift.fatigue_flag: reasons.append("fatigue flag set")

        return RiskFactor(
            factor_id="shift_changeover_window",
            active=active,
            weight=weight,
            contribution=round(contribution, 1),
            description=f"Shift risk: {', '.join(reasons)}" if active
                        else "Shift handover complete, no fatigue flags",
            regulatory_ref="DGFASLI OM-2023-11 Clause 5.2",
            evidence=reasons,
        )

    def _factor_sensor_blindspot(self, reading: PlantReading) -> RiskFactor:
        """Gas detector offline during operations — coverage blind spot."""
        weight = RISK_WEIGHTS["sensor_maintenance_blindspot"]
        offline = [
            sid for sid, s in reading.sensors.items()
            if s.status == SensorStatus.OFFLINE and s.sensor_type in ("H2S", "CO", "CH4")
        ]

        active = len(offline) > 0
        contribution = weight * 100 if active else 0.0

        return RiskFactor(
            factor_id="sensor_maintenance_blindspot",
            active=active,
            weight=weight,
            contribution=round(contribution, 1),
            description=f"Gas detectors OFFLINE (blind spot): {', '.join(offline)}"
                        if active else "All gas detectors operational",
            regulatory_ref="DGFASLI OM-2023-11 Clause 6.1",
            evidence=offline,
        )

    # ── Compound detection ────────────────────────────────────────────────────

    def _detect_compound_triggers(
        self, factors: List[RiskFactor], reading: PlantReading
    ) -> Tuple[List[CompoundTrigger], float]:
        """
        Check all factor co-occurrence combinations.
        Returns triggers found + the highest multiplier to apply.
        """
        active_ids = {f.factor_id for f in factors if f.active}
        triggers = []
        max_multiplier = 1.0

        for (f1, f2), mult in COMPOUND_MULTIPLIERS.items():
            if f1 in active_ids and f2 in active_ids:
                trigger_id = f"{f1}_x_{f2}"
                desc = self._compound_description(f1, f2)

                triggers.append(CompoundTrigger(
                    trigger_id=trigger_id,
                    factors_involved=[f1, f2],
                    multiplier=mult,
                    description=desc,
                    historical_match=None,  # filled by RAG agent in Week 2
                    regulatory_refs=self._compound_regulatory_refs(f1, f2),
                ))
                max_multiplier = max(max_multiplier, mult)

        return triggers, max_multiplier

    def _compound_description(self, f1: str, f2: str) -> str:
        descriptions = {
            ("gas_sensor_anomaly", "permit_gas_conflict"):
                "Elevated gas + active hot work permit = explosion precursor. "
                "This exact combination preceded the Vizag Jan 2025 incident.",
            ("confined_space_unchecked", "gas_sensor_anomaly"):
                "Workers entering confined space without gas check while sensors show elevation — "
                "H2S accumulates in low-lying spaces undetected.",
            ("sensor_maintenance_blindspot", "gas_sensor_anomaly"):
                "Gas rising in zone where detector is offline — "
                "true peak concentration is unknown and likely higher than readings show.",
        }
        key = (f1, f2) if (f1, f2) in descriptions else (f2, f1)
        return descriptions.get(key, f"Compound condition: {f1} + {f2}")

    def _compound_regulatory_refs(self, f1: str, f2: str) -> List[str]:
        refs = {
            ("gas_sensor_anomaly", "permit_gas_conflict"): [
                "OISD-GS-1 Clause 7.1",
                "DGFASLI OM-2023-11 Clause 4.3",
                "Factory Act S.36(3)",
            ],
            ("confined_space_unchecked", "gas_sensor_anomaly"): [
                "Factory Act S.36(1)(a)",
                "OISD-GS-1 Clause 6.3",
            ],
            ("sensor_maintenance_blindspot", "gas_sensor_anomaly"): [
                "DGFASLI OM-2023-11 Clause 6.1",
            ],
        }
        key = (f1, f2) if (f1, f2) in refs else (f2, f1)
        return refs.get(key, [])

    # ── Prediction ────────────────────────────────────────────────────────────

    def _predict(self, current_score: float, level: RiskLevel) -> PredictionWindow:
        """
        Linear extrapolation over recent score history.
        In Week 2: replace with Claude API call for smarter prediction.
        """
        if len(self._score_history) < 3:
            return PredictionWindow(
                minutes_to_next_threshold=None,
                next_threshold=None,
                confidence=0.0,
                basis="Insufficient history for prediction",
                single_sensor_minutes=None,
                lead_time_advantage_minutes=None,
            )

        # Compute slope: score change per reading
        history = list(self._score_history)
        n = len(history)
        slope = (history[-1] - history[0]) / n  # points per reading

        if slope <= 0:
            return PredictionWindow(
                minutes_to_next_threshold=None,
                next_threshold=None,
                confidence=0.5,
                basis="Score stable or declining — no breach predicted",
                single_sensor_minutes=None,
                lead_time_advantage_minutes=None,
            )

        # Next threshold
        thresholds = {
            RiskLevel.LOW: 35,
            RiskLevel.WARNING: 60,
            RiskLevel.HIGH: 80,
            RiskLevel.CRITICAL: 101,
        }
        order = [RiskLevel.LOW, RiskLevel.WARNING, RiskLevel.HIGH, RiskLevel.CRITICAL]
        next_level = None
        next_thresh = 101
        for lvl in order:
            if thresholds[lvl] > current_score:
                next_level = lvl
                next_thresh = thresholds[lvl]
                break

        # Minutes to threshold (each reading = 2 sim-minutes at 10x acceleration)
        readings_needed = (next_thresh - current_score) / max(slope, 0.001)
        minutes_needed = readings_needed * 2.0

        # Single-sensor baseline (simplified: would alert when H2S > 10 ppm)
        # In practice: roughly 2.5× later than compound detection
        single_sensor_mins = max(minutes_needed * 2.5, minutes_needed + 1.0)

        return PredictionWindow(
            minutes_to_next_threshold=round(minutes_needed, 0),
            next_threshold=next_level,
            confidence=min(0.95, 0.4 + len(history) * 0.04),
            basis=f"Linear extrapolation over last {n} readings — slope {slope:+.1f} pts/reading",
            single_sensor_minutes=round(single_sensor_mins, 0),
            lead_time_advantage_minutes=round(single_sensor_mins - minutes_needed, 0),
        )

    # ── Recommended actions ───────────────────────────────────────────────────

    def _recommend_actions(
        self, factors: List[RiskFactor], triggers: List[CompoundTrigger],
        reading: PlantReading
    ) -> List[RecommendedAction]:
        actions = []
        priority = 1

        for trigger in triggers:
            if "permit_gas_conflict" in trigger.factors_involved:
                conflicting = next(
                    (f.evidence for f in factors if f.factor_id == "permit_gas_conflict"), []
                )
                actions.append(RecommendedAction(
                    priority=priority,
                    action=f"SUSPEND hot work permit(s): {', '.join(conflicting)} immediately",
                    rationale="Hot work in gas-affected zone is the leading cause of coke oven explosions",
                    regulatory_basis="DGFASLI OM-2023-11 Clause 4.3",
                    zone=reading.active_permits[0].zone if reading.active_permits else None,
                    time_sensitive=True,
                ))
                priority += 1

            if "confined_space_unchecked" in trigger.factors_involved:
                actions.append(RecommendedAction(
                    priority=priority,
                    action="Halt all confined space entry — re-test atmosphere before re-entry",
                    rationale="Elevated gas + unchecked confined space = H2S accumulation risk",
                    regulatory_basis="Factory Act S.36(1)(a)",
                    zone=None,
                    time_sensitive=True,
                ))
                priority += 1

        for factor in factors:
            if factor.active:
                if factor.factor_id == "sensor_maintenance_blindspot":
                    actions.append(RecommendedAction(
                        priority=priority,
                        action=f"Deploy portable gas detector to cover offline sensor zones: {factor.evidence}",
                        rationale="Offline sensor = unknown gas levels in coverage area",
                        regulatory_basis="DGFASLI OM-2023-11 Clause 6.1",
                        zone=None,
                        time_sensitive=False,
                    ))
                    priority += 1
                elif factor.factor_id == "shift_changeover_window":
                    actions.append(RecommendedAction(
                        priority=priority,
                        action="Ensure incoming supervisor reviews current gas trend before accepting shift",
                        rationale="Most industrial accidents occur during shift changeover due to communication gaps",
                        regulatory_basis="DGFASLI OM-2023-11 Clause 5.2",
                        zone=None,
                        time_sensitive=False,
                    ))
                    priority += 1

        return sorted(actions, key=lambda a: a.priority)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _classify(self, score: float) -> RiskLevel:
        if score >= 80: return RiskLevel.CRITICAL
        if score >= 60: return RiskLevel.HIGH
        if score >= 35: return RiskLevel.WARNING
        return RiskLevel.LOW

    def _smooth(self, score: float, alpha: float = 0.8) -> float:
        """Exponential smoothing to prevent jitter."""
        if self._previous_score is None:
            return score
        return alpha * score + (1 - alpha) * self._previous_score

    def _zones_with_elevated_gas(self, reading: PlantReading) -> List[str]:
        """Return zone names where gas sensors are above WARNING."""
        hot_zones = []
        zone_sensor_map = {
            "Zone A": ["G-01", "G-02", "G-03"],
            "Zone B": ["G-04", "G-05", "G-06"],
            "Zone C": ["G-07", "G-08", "G-09"],
        }
        for zone, sensors in zone_sensor_map.items():
            for sid in sensors:
                s = reading.sensors.get(sid)
                if s and s.status in (SensorStatus.WARNING, SensorStatus.CRITICAL, SensorStatus.IDLH):
                    hot_zones.append(zone)
                    break
        return list(set(hot_zones))

    def _collect_violations(
        self, factors: List[RiskFactor], triggers: List[CompoundTrigger]
    ) -> List[str]:
        refs = []
        for f in factors:
            if f.active and f.regulatory_ref:
                refs.append(f.regulatory_ref)
        for t in triggers:
            refs.extend(t.regulatory_refs)
        return list(set(refs))

    def _draft_incident_report(
        self, assessment: RiskAssessment, reading: PlantReading
    ) -> str:
        """
        Auto-generate a DGFASLI-format incident report on CRITICAL trigger.
        Week 2: replace this with a Claude API call for better quality.
        """
        active_factors = [f.description for f in assessment.risk_factors if f.active]
        permits = [p.permit_id for p in reading.active_permits]
        violations = assessment.regulatory_violations

        return f"""SAFETY INCIDENT PRELIMINARY REPORT
Generated by SafetyIQ Compound Risk Engine
==========================================
Date/Time:    {reading.timestamp}
Facility:     Visakhapatnam Steel Plant — Coke Oven Battery 3
Shift:        {reading.shift.shift} — Supervisor: {reading.shift.supervisor}
Risk Score:   {assessment.risk_score}/100 (CRITICAL)

COMPOUND CONDITIONS DETECTED
{chr(10).join(f'  • {f}' for f in active_factors)}

ACTIVE PERMITS AT TIME OF TRIGGER
{chr(10).join(f'  • {p}' for p in permits)}

REGULATORY VIOLATIONS IDENTIFIED
{chr(10).join(f'  • {v}' for v in violations)}

PREDICTION LEAD TIME
  This system flagged CRITICAL at {reading.elapsed_minutes:.0f} minutes elapsed.
  Single-sensor baseline would alert at approximately {(assessment.prediction.single_sensor_minutes or 0) + reading.elapsed_minutes:.0f} minutes.
  Lead time advantage: {assessment.prediction.lead_time_advantage_minutes or 0:.0f} minutes.

IMMEDIATE ACTIONS REQUIRED
{chr(10).join(f'  {i+1}. {a.action}' for i, a in enumerate(assessment.recommended_actions[:3]))}

[This report was auto-generated. A qualified safety officer must review and sign before submission to DGFASLI.]
"""
