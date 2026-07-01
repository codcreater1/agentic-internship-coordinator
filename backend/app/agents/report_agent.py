"""Report agent — composes a readable evaluation report from graph state.

Deterministic (no model call): it formats the structured evaluation produced by
``cv_agent`` into a human-readable summary used in the UI and emails.
"""


def generate_report(state):
    score = state.get("candidate_score", 0)
    role = state.get("recommendation", "N/A")
    analysis = state.get("analysis", "").strip()
    rationale = state.get("rationale", "").strip()
    strengths = state.get("strengths", []) or []
    weaknesses = state.get("weaknesses", []) or []

    lines = [
        f"Candidate score: {score}/100.",
        f"Recommended role: {role}.",
    ]

    if analysis:
        lines.append("")
        lines.append(analysis)

    if strengths:
        lines.append("")
        lines.append("Strengths:")
        lines.extend(f"  - {item}" for item in strengths)

    if weaknesses:
        lines.append("")
        lines.append("Areas for improvement:")
        lines.extend(f"  - {item}" for item in weaknesses)

    if rationale:
        lines.append("")
        lines.append(f"Role fit: {rationale}")

    return {"report": "\n".join(lines)}
