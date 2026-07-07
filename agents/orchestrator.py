"""
SafetyIQ — orchestrator (Week 3)
Generates natural language safety alerts using Claude API.
Falls back to rule-based alerts if API key not set.
Only called for WARNING / HIGH / CRITICAL — never for LOW.

Usage:
    from agents.orchestrator import generate_alert
    alert = generate_alert(assessment_dict, rag_context)
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            import anthropic
            key = os.getenv("ANTHROPIC_API_KEY")
            if key:
                _client = anthropic.Anthropic(api_key=key)
        except Exception:
            pass
    return _client


def generate_alert(assessment_dict: dict, rag_context: str = "") -> str:
    """
    Generate a 2-sentence safety alert for the plant supervisor.

    Args:
        assessment_dict : RiskAssessment serialised to dict (from to_dict())
        rag_context     : matching historical incidents from query_rag()

    Returns:
        2-sentence alert string.
        Empty string for LOW risk.
        Falls back to rule-based alert if Claude API unavailable.
    """
    level = assessment_dict.get("risk_level", "LOW")
    if level == "LOW":
        return ""

    client = _get_client()

    if client:
        return _claude_alert(client, assessment_dict, rag_context)
    else:
        return _fallback_alert(assessment_dict)


def _claude_alert(client, assessment_dict: dict, rag_context: str) -> str:
    try:
        active_factors = [
            f["description"]
            for f in assessment_dict.get("risk_factors", [])
            if f.get("active")
        ]
        compound = assessment_dict.get("compound_triggers", [])
        compound_desc = compound[0]["description"] if compound else "Multiple co-occurring hazards"

        prompt = f"""You are SafetyIQ, an industrial safety AI at Visakhapatnam Steel Plant Coke Oven Battery 3.

Risk score: {assessment_dict.get('risk_score', 0):.0f}/100
Level: {assessment_dict.get('risk_level')}
Active conditions: {'; '.join(active_factors[:3])}
Compound trigger: {compound_desc}
Historical match: {rag_context[:200] if rag_context else 'None'}

Write exactly 2 sentences for the plant supervisor:
1. State the most dangerous compound condition, naming specific sensors and permits.
2. State the single most urgent action with its regulatory basis.

Be direct. No preamble."""

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text.strip()

    except Exception:
        return _fallback_alert(assessment_dict)


def _fallback_alert(assessment_dict: dict) -> str:
    """Rule-based alert — used when Claude API is unavailable."""
    level   = assessment_dict.get("risk_level", "LOW")
    score   = assessment_dict.get("risk_score", 0)
    actions = assessment_dict.get("recommended_actions", [])
    top     = actions[0]["action"] if actions else "Review all active permits immediately"

    if level == "CRITICAL":
        return (
            f"CRITICAL compound risk at score {score:.0f}/100 — "
            f"multiple co-occurring hazards detected simultaneously. "
            f"Immediate action: {top}."
        )
    elif level == "HIGH":
        return (
            f"HIGH risk at score {score:.0f}/100 — compound trigger active. "
            f"{top} per DGFASLI OM-2023-11."
        )
    else:
        return (
            f"WARNING — risk score {score:.0f}/100, conditions trending toward threshold. "
            f"Increase monitoring and review active permits."
        )


if __name__ == "__main__":
    mock = {
        "risk_score": 93.7,
        "risk_level": "CRITICAL",
        "risk_factors": [
            {"active": True,  "description": "Elevated gas at G-07, G-08"},
            {"active": True,  "description": "HOT WORK permit PTW-047 active in gas zone"},
            {"active": True,  "description": "G-09 offline — CH4 blind spot in Zone C"},
        ],
        "compound_triggers": [
            {"description": "Elevated gas + hot work permit = explosion precursor (Vizag Jan 2025)"}
        ],
        "recommended_actions": [
            {"action": "SUSPEND PTW-047 immediately",
             "regulatory_basis": "DGFASLI OM-2023-11 Clause 4.3"}
        ],
    }
    rag = "[INC-003 89%] Vizag Jan 2025 — H2S + CO + hot work permit + offline sensor"

    print("Orchestrator test\n" + "=" * 50)
    result = generate_alert(mock, rag)
    print(f"Alert:\n{result}")
    print()
    assert generate_alert({"risk_level": "LOW"}, "") == ""
    print("LOW risk returns empty: PASS")
    print("\nOrchestrator: PASS")