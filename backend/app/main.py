from fastapi import FastAPI

from app.agents.workflow import graph
from app.routers.applications import router as applications_router

app = FastAPI(title="Agentic Internship Coordinator")

app.include_router(applications_router)


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "backend",
    }


@app.get("/test-agent")
def test_agent():
    result = graph.invoke(
        {
            "cv_text": "Python developer with FastAPI experience"
        }
    )

    return result