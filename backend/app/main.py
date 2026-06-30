from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import applications, cv, pdf

app = FastAPI(title="Agentic Internship Coordinator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(pdf.router)