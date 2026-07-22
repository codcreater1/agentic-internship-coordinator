from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.agents.cv_agent import analyze_cv
from app.agents.matching_agent import match_candidate
from app.agents.report_agent import generate_report


class CandidateState(TypedDict):
    cv_text: str
    extracted_name: str
    analysis: str
    candidate_score: int
    strengths: list[str]
    weaknesses: list[str]
    recommendation: str
    rationale: str
    report: str
    internship_country: str
    internship_eu_eligible: str
    # Placement details the internship agreement cannot be issued without.
    company_name: str
    supervisor_name: str
    supervisor_contact: str
    # False when the LLM was unreachable and the keyword fallback produced
    # the score — see ApplicationService.
    ai_available: bool


builder = StateGraph(CandidateState)

builder.add_node("cv_analysis", analyze_cv)
builder.add_node("matching", match_candidate)
builder.add_node("report", generate_report)

builder.set_entry_point("cv_analysis")

builder.add_edge("cv_analysis", "matching")
builder.add_edge("matching", "report")
builder.add_edge("report", END)

graph = builder.compile()