"""
agents/alert_generator.py
Anthropic API-powered safety alert generation.
Takes a RiskAssessment + RAG context → structured natural-language alert.

Usage:
    from agents.alert_generator import generate_alert, AlertOutput
    alert = generate_alert(assessment, rag_context)
    print(alert.headline)
    print(alert.full_text)
    print(alert.regulatory_summary)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
from dataclasses import dataclass
from typing import Optional
import anthropic

from agents.interfaces import RiskAssessment, RiskLevel


# ── Output contract ───────────────────────────────────────────────────────────

@dataclass
class AlertOutput:
    headline: str               # ≤ 12 words, shown in UI banner
    severity_label: str         # "LOW" / "WARNING" / "HIGH" / "CRITICAL"
    full_text: str              # 2–4 sentence human-readable alert
    regulatory_summary: str     # comma-separated violated clauses
    immediate_actions: list     # list of strings, top 3 max
    historical_reference: str   # matching incident if any
    generated_by: str           # "anthropic-api" or "fallback"


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(assessment: RiskAssessment, rag_context: str) -> str:
    active_factors = [f.description for f in assessment.risk_factors if f.active]
    compounds = [t.description for t in assessment.compound_triggers]
    actions = [a.action for a in assessment.recommended_actions[:3]]
    violations = assessment.regulatory_violations

    prompt = f"""You are a safety officer AI at an industrial coke oven plant.
A compound risk detection system has flagged a serious condition.
Generate a structured safety alert for the control room team.

RISK DATA:
- Risk Score: {assessment.risk_score}/100
- Risk Level: {assessment.risk_level.value}
- Elapsed Minutes: {assessment.elapsed_minutes}
- Active Risk Factors: {chr(10).join(f'  * {f}' for f in active_factors)}
- Compound Triggers Detected: {chr(10).join(f'  * {c[:120]}' for c in compounds) if compounds else '  * None'}
- Regulatory Violations: {', '.join(violations) if violations else 'None'}
- Top Recommended Actions: {chr(10).join(f'  {i+1}. {a}' for i,a in enumerate(actions))}

{rag_context}

Respond ONLY with a JSON object. No markdown, no explanation, no preamble. Schema:
{{
  "headline": "<≤12 words, urgent tone, mention key hazard>",
  "full_text": "<2-4 sentences: what is happening, why it is dangerous, what the compound condition means>",
  "regulatory_summary": "<comma-separated violated clauses e.g. OISD-GS-1 Cl.7.1, Factory Act S.36>",
  "immediate_actions": ["<action 1>", "<action 2>", "<action 3>"],
  "historical_reference": "<one sentence referencing most relevant past incident, or empty string>"
}}"""
    return prompt


# ── Fallback (no API key / API error) ────────────────────────────────────────

def _fallback_alert(assessment: RiskAssessment) -> AlertOutput:
    """Rule-based alert used when Anthropic API is unavailable."""
    level = assessment.risk_level.value
    score = assessment.risk_score
    active = [f.description for f in assessment.risk_factors if f.active]
    actions = [a.action for a in assessment.recommended_actions[:3]]

    headlines = {
        "CRITICAL": f"CRITICAL: Compound hazard — evacuate Zone C immediately",
        "HIGH":     f"HIGH RISK: Multiple safety factors active — take action now",
        "WARNING":  f"WARNING: Elevated gas detected — monitor and prepare",
        "LOW":      f"Status normal — no immediate action required",
    }

    full_texts = {
        "CRITICAL": (
            f"Risk score {score}/100. A compound hazard condition has been detected: "
            f"{active[0] if active else 'multiple factors active'}. "
            f"This combination has been linked to fatal incidents at Indian steel plants. "
            f"Evacuation of affected zones and immediate suspension of hot work permits is required."
        ),
        "HIGH": (
            f"Risk score {score}/100. Multiple risk factors are active simultaneously. "
            f"Gas levels are rising and permit conditions create an elevated ignition risk. "
            f"Immediate action is required before this escalates to CRITICAL."
        ),
        "WARNING": (
            f"Risk score {score}/100. Gas levels are above normal thresholds. "
            f"Situation is being monitored. Ensure all permits are reviewed for zone compatibility."
        ),
        "LOW": (
            f"Risk score {score}/100. All sensors nominal, no permit conflicts detected. "
            f"System is monitoring continuously."
        ),
    }

    return AlertOutput(
        headline=headlines.get(level, f"Risk Level: {level}"),
        severity_label=level,
        full_text=full_texts.get(level, ""),
        regulatory_summary=", ".join(assessment.regulatory_violations) or "None",
        immediate_actions=actions,
        historical_reference="",
        generated_by="fallback",
    )


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_alert(
    assessment: RiskAssessment,
    rag_context: str = "",
    api_key: Optional[str] = None,
) -> AlertOutput:
    """
    Generate a safety alert using the Anthropic API.
    Falls back gracefully to rule-based alert if:
    - ANTHROPIC_API_KEY is not set
    - API call fails for any reason

    Args:
        assessment:  RiskAssessment from risk_engine.assess()
        rag_context: Context string from rag_agent.build_rag_context()
        api_key:     Optional override; else reads ANTHROPIC_API_KEY env var

    Returns:
        AlertOutput dataclass
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return _fallback_alert(assessment)

    try:
        client = anthropic.Anthropic(api_key=key)
        prompt = _build_prompt(assessment, rag_context)

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()

        # Strip accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)

        return AlertOutput(
            headline=data.get("headline", "Safety alert generated"),
            severity_label=assessment.risk_level.value,
            full_text=data.get("full_text", ""),
            regulatory_summary=data.get("regulatory_summary", ""),
            immediate_actions=data.get("immediate_actions", []),
            historical_reference=data.get("historical_reference", ""),
            generated_by="anthropic-api",
        )

    except json.JSONDecodeError as e:
        # API responded but JSON malformed — still use fallback
        print(f"[alert_generator] JSON parse error: {e} — using fallback")
        return _fallback_alert(assessment)

    except Exception as e:
        print(f"[alert_generator] API error: {type(e).__name__}: {e} — using fallback")
        return _fallback_alert(assessment)
