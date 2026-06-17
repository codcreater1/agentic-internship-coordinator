from fastapi import APIRouter

from app.models.application import Application, ApplicationResponse
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/", response_model=ApplicationResponse)
def create_application(application: Application):
    result = ApplicationService.evaluate(application.cv_text)

    return ApplicationResponse(
        name=application.name,
        email=application.email,
        candidate_score=result["candidate_score"],
        recommended_role=result["recommended_role"],
        status=result["status"],
        report=result["report"],
        email_subject=result["email_subject"],
        email_body=result["email_body"],
    )
