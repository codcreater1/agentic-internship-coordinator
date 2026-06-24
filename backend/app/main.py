from fastapi import FastAPI

from app.routers import applications, cv

app = FastAPI(title="Agentic Internship Coordinator")


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Agentic Internship Coordinator"
    }


@app.get("/test-agent")
def test_agent():
    return {
        "message": "Agent test endpoint is working"
    }


app.include_router(applications.router)
app.include_router(cv.router)