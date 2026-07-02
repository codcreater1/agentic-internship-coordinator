import sys
from app.core import llm
from app.core.config import settings


def get_health() -> dict:
    return {
        "status": "healthy",
        "service": "Agentic Internship Coordinator",
        "version": settings.app_version,
        "ai_enabled": llm.is_enabled(),
        "python": sys.version.split()[0],
    }
