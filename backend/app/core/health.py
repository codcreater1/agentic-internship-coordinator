from app.core import llm


def get_health() -> dict:
    return {
        "status": "healthy",
        "service": "Agentic Internship Coordinator",
        "ai_enabled": llm.is_enabled(),
    }
