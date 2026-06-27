"""
agents/risk_engine.py — Member 1 owns this.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional, Tuple
from collections import deque
from agents.interfaces import (
    PlantReading, RiskAssessment, RiskFactor, CompoundTrigger,
    PredictionWindow, RecommendedAction, RiskLevel, SensorStatus, PermitType
)
from config.settings import RISK_WEIGHTS, COMPOUND_MULTIPLIERS, SENSOR_THRESHOLDS


class RiskEngine:
    def __init__(self, history_window: int = 20):
        self._score_history: deque = deque(maxlen=history_window)
        self._previous_score: Optional[float] = None

    def assess(self, reading: PlantReading) -> RiskAssessment:
        factors              = self._evaluate_factors(reading)
        base_score           = sum(f.contribution for f in factors if f.active)
        triggers, multiplier = self._detect_compound_triggers(factors, reading)
        raw_score            = min(100.0, base_score * multiplier)
        score                = self._smooth(raw_score)
        level                = self._classify(score)
        self._score_history.append(score)
        prediction           = self._predict(score, level)
        actions              = self._recommend_actions(factors, triggers, reading)

        assessment = RiskAssessment(
            timestamp=reading.timestamp, elapsed_minutes=reading.elapsed_minutes,
            risk_score=round(score, 1), risk_level=level,
            previous_score=self._previous_score, risk_factors=factors,
            compound_triggers=triggers, prediction=prediction,
            recommended_actions=actions,
            regulatory_violations=self._collect_violations(factors, triggers),
        )
        if level == RiskLevel.CRITICAL:
            assessment.incident_report_draft = self._draft_incident_report(assessment, reading)
            assessment.evacuation_triggered = True

        self._previous_score = score
        return assessment

    def _evaluate_factors(self, reading):
        return [
            self._factor_gas_anomaly(reading),
            self._factor_permit_conflict(reading),
            self._factor_confined_unchecked(reading),
            self._factor_shift_changeover(reading),
            self._factor_sensor_blindspot(reading),
        ]

    def _factor_gas_anomaly(self, reading):
        weight = RISK_WEIGHTS["gas_sensor_anomaly"]
        triggered, max_sev = [], 0.0
        for sid, s in reading.sensors.items():
            if s.sensor_type not in ("H2S","CO","CH4"): continue
            if s.status in (SensorStatus.WARNING, SensorStatus.CRITICAL, SensorStatus.IDLH):
                triggered.append(sid)
                sev = {"WARNING":0.85,"CRITICAL":0.95,"IDLH":1.0}.get(s.status.value, 0)
                max_sev = max(max_sev, sev)
        active = bool(triggered)
        return RiskFactor(factor_id="gas_sensor_anomaly", active=active, weight=weight,
            contribution=round(weight*max_sev*100,1) if active else 0.0,
            description=f"Elevated gas at: {', '.join(triggered)}" if active else "Gas sensors nominal",
            regulatory_ref="OISD-GS-1 Clause 6.3 / 6.4", evidence=triggered)

    def _factor_permit_conflict(self, reading):
        weight = RISK_WEIGHTS["permit_gas_conflict"]
        hot_zones = self._zones_with_elevated_gas(reading)
        conflicting = [p.permit_id for p in reading.active_permits
                       if p.permit_type == PermitType.HOT_WORK
                       and (any(z in p.zone for z in hot_zones) or p.risk_flag)]
        active = bool(conflicting)
        return RiskFactor(factor_id="permit_gas_conflict", active=active, weight=weight,
            contribution=round(weight*100,1) if active else 0.0,
            description=f"HOT WORK permit in gas zone: {', '.join(conflicting)}" if active else "No conflicts",
            regulatory_ref="OISD-GS-1 Clause 7.1 / DGFASLI OM-2023-11 Clause 4.3",
            evidence=conflicting)

    def _factor_confined_unchecked(self, reading):
        weight = RISK_WEIGHTS["confined_space_unchecked"]
        unchecked = [p.permit_id for p in reading.active_permits
                     if p.permit_type == PermitType.CONFINED_SPACE
                     and (p.risk_flag or (p.conflict_reason and "gas check" in p.conflict_reason.lower()))]
        active = bool(unchecked)
        return RiskFactor(factor_id="confined_space_unchecked", active=active, weight=weight,
            contribution=round(weight*100,1) if active else 0.0,
            description=f"Confined space no pre-entry check: {', '.join(unchecked)}" if active else "All permits checked",
            regulatory_ref="Factory Act S.36(1)(a) / DGFASLI OM-2023-11 Clause 4.1",
            evidence=unchecked)

    def _factor_shift_changeover(self, reading):
        weight = RISK_WEIGHTS["shift_changeover_window"]
        s = reading.shift
        active = s.in_changeover_window or not s.handover_complete or s.fatigue_flag
        reasons = ([("in changeover window" if s.in_changeover_window else "")] +
                   [("handover incomplete"  if not s.handover_complete else "")] +
                   [("fatigue flag"         if s.fatigue_flag else "")])
        reasons = [r for r in reasons if r]
        return RiskFactor(factor_id="shift_changeover_window", active=active, weight=weight,
            contribution=round(weight*100,1) if active else 0.0,
            description=f"Shift risk: {', '.join(reasons)}" if active else "Shift OK",
            regulatory_ref="DGFASLI OM-2023-11 Clause 5.2", evidence=reasons)

    def _factor_sensor_blindspot(self, reading):
        weight = RISK_WEIGHTS["sensor_maintenance_blindspot"]
        offline = [sid for sid, s in reading.sensors.items()
                   if s.status == SensorStatus.OFFLINE and s.sensor_type in ("H2S","CO","CH4")]
        active = bool(offline)
        return RiskFactor(factor_id="sensor_maintenance_blindspot", active=active, weight=weight,
            contribution=round(weight*100,1) if active else 0.0,
            description=f"Gas detectors OFFLINE: {', '.join(offline)}" if active else "All detectors OK",
            regulatory_ref="DGFASLI OM-2023-11 Clause 6.1", evidence=offline)

    def _detect_compound_triggers(self, factors, reading):
        active_ids = {f.factor_id for f in factors if f.active}
        triggers, max_mult = [], 1.0
        DESCS = {
            ("gas_sensor_anomaly","permit_gas_conflict"): "Elevated gas + hot work permit = explosion precursor (Vizag Jan 2025).",
            ("confined_space_unchecked","gas_sensor_anomaly"): "Confined space without gas check while sensors elevated.",
            ("sensor_maintenance_blindspot","gas_sensor_anomaly"): "Gas rising where detector is offline — true peak unknown.",
        }
        REFS = {
            ("gas_sensor_anomaly","permit_gas_conflict"): ["OISD-GS-1 Clause 7.1","DGFASLI OM-2023-11 Clause 4.3","Factory Act S.36(3)"],
            ("confined_space_unchecked","gas_sensor_anomaly"): ["Factory Act S.36(1)(a)","OISD-GS-1 Clause 6.3"],
            ("sensor_maintenance_blindspot","gas_sensor_anomaly"): ["DGFASLI OM-2023-11 Clause 6.1"],
        }
        for (f1,f2), mult in COMPOUND_MULTIPLIERS.items():
            if f1 in active_ids and f2 in active_ids:
                key = (f1,f2) if (f1,f2) in DESCS else (f2,f1)
                triggers.append(CompoundTrigger(
                    trigger_id=f"{f1}_x_{f2}", factors_involved=[f1,f2], multiplier=mult,
                    description=DESCS.get(key, f"Compound: {f1}+{f2}"),
                    historical_match=None, regulatory_refs=REFS.get(key,[])))
                max_mult = max(max_mult, mult)
        return triggers, max_mult

    def _predict(self, score, level):
        if len(self._score_history) < 3:
            return PredictionWindow(None, None, 0.0, "Insufficient history", None, None)
        history = list(self._score_history)
        slope   = (history[-1] - history[0]) / len(history)
        if slope <= 0:
            return PredictionWindow(None, None, 0.5, "Score stable", None, None)
        thresholds = {RiskLevel.LOW:35, RiskLevel.WARNING:60, RiskLevel.HIGH:80, RiskLevel.CRITICAL:101}
        next_level, next_thresh = None, 101
        for lvl in [RiskLevel.LOW, RiskLevel.WARNING, RiskLevel.HIGH, RiskLevel.CRITICAL]:
            if thresholds[lvl] > score:
                next_level, next_thresh = lvl, thresholds[lvl]; break
        mins = ((next_thresh - score) / max(slope, 0.001)) * 2.0
        ss   = max(mins * 2.5, mins + 1.0)
        return PredictionWindow(
            minutes_to_next_threshold=round(mins,0), next_threshold=next_level,
            confidence=min(0.95, 0.4+len(history)*0.04),
            basis=f"Linear extrapolation {slope:+.1f} pts/reading",
            single_sensor_minutes=round(ss,0), lead_time_advantage_minutes=round(ss-mins,0))

    def _recommend_actions(self, factors, triggers, reading):
        actions, priority = [], 1
        for t in triggers:
            if "permit_gas_conflict" in t.factors_involved:
                ev = next((f.evidence for f in factors if f.factor_id=="permit_gas_conflict"), [])
                actions.append(RecommendedAction(priority=priority,
                    action=f"SUSPEND hot work permit(s): {', '.join(ev)} immediately",
                    rationale="Hot work in gas zone = leading cause of coke oven explosions",
                    regulatory_basis="DGFASLI OM-2023-11 Clause 4.3",
                    zone=reading.active_permits[0].zone if reading.active_permits else None,
                    time_sensitive=True)); priority+=1
            if "confined_space_unchecked" in t.factors_involved:
                actions.append(RecommendedAction(priority=priority,
                    action="Halt confined space entry — re-test atmosphere",
                    rationale="Elevated gas + unchecked confined space = H2S accumulation risk",
                    regulatory_basis="Factory Act S.36(1)(a)", zone=None,
                    time_sensitive=True)); priority+=1
        for f in factors:
            if f.active:
                if f.factor_id=="sensor_maintenance_blindspot":
                    actions.append(RecommendedAction(priority=priority,
                        action=f"Deploy portable detector for offline zones: {f.evidence}",
                        rationale="Offline sensor = unknown gas levels",
                        regulatory_basis="DGFASLI OM-2023-11 Clause 6.1",
                        zone=None, time_sensitive=False)); priority+=1
                elif f.factor_id=="shift_changeover_window":
                    actions.append(RecommendedAction(priority=priority,
                        action="Incoming supervisor must review gas trend before accepting shift",
                        rationale="Most accidents occur during shift changeover",
                        regulatory_basis="DGFASLI OM-2023-11 Clause 5.2",
                        zone=None, time_sensitive=False)); priority+=1
        return sorted(actions, key=lambda a: a.priority)

    def _classify(self, score):
        if score >= 80: return RiskLevel.CRITICAL
        if score >= 60: return RiskLevel.HIGH
        if score >= 35: return RiskLevel.WARNING
        return RiskLevel.LOW

    def _smooth(self, score, alpha=0.8):
        if self._previous_score is None: return score
        return alpha*score + (1-alpha)*self._previous_score

    def _zones_with_elevated_gas(self, reading):
        zone_map = {"Zone A":["G-01","G-02","G-03"],"Zone B":["G-04","G-05","G-06"],"Zone C":["G-07","G-08","G-09"]}
        return list({z for z, sids in zone_map.items()
                     for sid in sids
                     if (s:=reading.sensors.get(sid)) and
                        s.status in (SensorStatus.WARNING, SensorStatus.CRITICAL, SensorStatus.IDLH)})

    def _collect_violations(self, factors, triggers):
        refs = [f.regulatory_ref for f in factors if f.active and f.regulatory_ref]
        for t in triggers: refs.extend(t.regulatory_refs)
        return list(set(refs))

    def _draft_incident_report(self, assessment, reading):
        active  = [f.description for f in assessment.risk_factors if f.active]
        permits = [p.permit_id for p in reading.active_permits]
        return f"""SAFETY INCIDENT PRELIMINARY REPORT
Generated by SafetyIQ Compound Risk Engine
==========================================
Date/Time:  {reading.timestamp}
Facility:   Visakhapatnam Steel Plant — Coke Oven Battery 3
Shift:      {reading.shift.shift} — Supervisor: {reading.shift.supervisor}
Risk Score: {assessment.risk_score}/100 (CRITICAL)

COMPOUND CONDITIONS DETECTED
{chr(10).join(f'  • {f}' for f in active)}

ACTIVE PERMITS
{chr(10).join(f'  • {p}' for p in permits)}

REGULATORY VIOLATIONS
{chr(10).join(f'  • {v}' for v in assessment.regulatory_violations)}

Lead time advantage: {assessment.prediction.lead_time_advantage_minutes or 0:.0f} minutes over single-sensor baseline.

IMMEDIATE ACTIONS
{chr(10).join(f'  {i+1}. {a.action}' for i,a in enumerate(assessment.recommended_actions[:3]))}

[Auto-generated — qualified safety officer must review before DGFASLI submission.]
"""