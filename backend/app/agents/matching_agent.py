"""Matching agent — surfaces the recommended role chosen during CV analysis.

The role decision is made by the evaluation in ``cv_agent`` (so it shares the
same model context as the scoring). This node simply carries it forward in the
graph state, defaulting if it is somehow missing.
"""

from app.agents.cv_agent import DEFAULT_ROLE


def match_candidate(state):
    return {
        "recommendation": state.get("recommendation") or DEFAULT_ROLE,
    }
