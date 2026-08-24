from dotenv import load_dotenv

# Load .env so LLM_API_KEY reaches the OpenAI-compatible SDK (which reads
# os.environ directly — pydantic-settings does not populate it).
load_dotenv()

import logging
from contextlib import asynccontextmanager
from app.core.logging_config import setup_logging
setup_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import applications, cv, pdf, reports
from app.services import application_repository as repo
from app.services import report_repository, report_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the tables exist. (We intentionally do NOT purge task dirs here —
    # contracts and completion certificates back persistent records and must
    # survive.)
    repo.init_db()
    report_repository.init_db()

    # The originality index lives in memory. Rebuilding it from the accepted
    # submissions on disk is what stops a restart from amnestying a report
    # copied from one accepted last week.
    indexed = report_service.load_corpus()
    logger.info("Report originality index loaded with %d accepted report(s)", indexed)

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


app.include_router(applications.router)
app.include_router(cv.router)
app.include_router(pdf.router)
app.include_router(reports.router)
