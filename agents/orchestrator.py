"""
SafetyIQ — orchestrator
Generates natural language safety alerts using the Anthropic Claude API.
Only called when risk_level is WARNING or above — not every tick.

Public interface (Member 2 calls this from main.py):
    from agents.orchestrator import generate_alert
    alert = generate_alert(assessment_dict, rag_context)

Returns a short alert string. Returns "" on LOW risk or any error.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Singleton client ─────────────────────────────────────────────────────────
_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            import anthropic
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                return None
            _client = anthropic.Anthropic(api_key=key)
        except Exception:
            return None
    return _client


# ── Public function ───────────────────────────────────────────────────────────

def generate_alert(assessment_dict: dict, rag_context: str = "") -> str:
    """
    Generate a 2-sentence safety alert using Claude.

    Args:
        assessment_dict : the RiskAssessment serialised to dict (from to_dict())
        rag_context     : matching historical incidents from query_rag()

    Returns:
        2-sentence alert string for the plant supervisor.
        Empty string for LOW risk or on any error.
    """
    level = assessment_dict.get("risk_level", "LOW")

    # Only generate alerts for elevated risk
    if level == "LOW":
        return ""

    client = _get_client()
    if client is None:
        return _fallback_alert(assessment_dict)

    try:
        active_factors = [
            f["description"]
            for f in assessment_dict.get("risk_factors", [])
            if f.get("active")
        ]

        compound = assessment_dict.get("compound_triggers", [])
        compound_desc = compound[0]["description"] if compound else ""

        prompt = f"""You are SafetyIQ, an industrial safety AI monitoring Visakhapatnam Steel Plant, Coke Oven Battery 3.

Current status:
- Risk score: {assessment_dict.get('risk_score', 0)}/100
- Risk level: {level}
- Active conditions: {'; '.join(active_factors[:3])}
- Compound trigger: {compound_desc}
- Historical match: {rag_context[:200] if rag_context else 'None'}

Write exactly 2 sentences for the plant supervisor:
Sentence 1: State the most dangerous compound condition specifically (name the sensors and permits involved).
Sentence 2: State the single most urgent action with the regulatory basis.

Be direct. No preamble. No bullet points."""

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text.strip()

    except Exception:
        return _fallback_alert(assessment_dict)


def _fallback_alert(assessment_dict: dict) -> str:
    """
    Rule-based fallback when Claude API is unavailable.
    Ensures the frontend always gets something meaningful.
    """
    level   = assessment_dict.get("risk_level", "LOW")
    score   = assessment_dict.get("risk_score", 0)
    actions = assessment_dict.get("recommended_actions", [])

    if level == "CRITICAL":
        top = actions[0]["action"] if actions else "Initiate evacuation immediately"
        return (
            f"CRITICAL compound risk detected — score {score}/100 with multiple co-occurring hazards. "
            f"Immediate action required: {top}."
        )
    elif level == "HIGH":
        top = actions[0]["action"] if actions else "Suspend active work permits"
        return (
            f"HIGH risk condition — score {score}/100, compound trigger active. "
            f"{top} per DGFASLI OM-2023-11."
        )
    elif level == "WARNING":
        return (
            f"WARNING — risk score {score}/100, conditions trending toward threshold. "
            f"Increase monitoring frequency and review active permits."
        )
    return ""


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test with a mock CRITICAL assessment
    mock = {
        "risk_score": 93.7,
        "risk_level": "CRITICAL",
        "risk_factors": [
            {"active": True,  "description": "Elevated gas at G-07, G-08"},
            {"active": True,  "description": "HOT WORK permit active in gas zone: PTW-047"},
            {"active": True,  "description": "G-09 offline — CH4 blind spot"},
            {"active": False, "description": "Normal shift"},
        ],
        "compound_triggers": [
            {"description": "Elevated gas + hot work = explosion precursor (Vizag Jan 2025)"}
        ],
        "recommended_actions": [
            {"action": "SUSPEND PTW-047 immediately", "regulatory_basis": "DGFASLI OM-2023-11 Clause 4.3"}
        ],
    }
    rag = "[INC-003 89%] Hot work permit PTW-047 active while H2S elevated — matches Vizag Jan 2025 preconditions"

    print("Orchestrator test\n" + "=" * 50)
    result = generate_alert(mock, rag)
    print(f"Alert:\n{result}")
    print()

    # Test LOW risk returns empty
    mock_low = {"risk_level": "LOW", "risk_score": 5, "risk_factors": [], "compound_triggers": [], "recommended_actions": []}
    assert generate_alert(mock_low, "") == "", "LOW risk should return empty string"
    print("LOW risk test: PASS")
    print("\nOrchestrator: PASS")