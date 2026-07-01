from dotenv import load_dotenv

# Load .env so LLM_API_KEY reaches the OpenAI-compatible SDK (which reads
# os.environ directly — pydantic-settings does not populate it).
load_dotenv()

from contextlib import asynccontextmanager
from app.core.logging_config import setup_logging
setup_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import applications, cv, pdf
from app.services import application_repository as repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the applications table exists. (We intentionally do NOT purge task
    # dirs here — contracts back persistent applications and must survive.)
    repo.init_db()
    yield


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/health")
def health_check():
    from app.core.health import get_health
    return get_health()


@app.get("/test-agent")
def test_agent():
    return {
        "message": "Agent test endpoint is working"
    }


app.include_router(applications.router)
app.include_router(cv.router)
app.include_router(pdf.router)