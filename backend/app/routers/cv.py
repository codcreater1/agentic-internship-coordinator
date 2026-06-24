from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel, EmailStr

from app.models.cv import CVAnalysisResponse
from app.services.pdf_service import PDFService
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/cv", tags=["cv"])


class CVTextRequest(BaseModel):
    name: str
    email: EmailStr
    cv_text: str


@router.post("/analyze", response_model=CVAnalysisResponse)
async def analyze_cv(
    name: str = Form(...),
    email: str = Form(...),
    file: UploadFile = File(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    cv_text = await PDFService.extract_text_from_pdf(file)

    if not cv_text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    result = ApplicationService.evaluate(cv_text)

    return CVAnalysisResponse(
        name=name,
        email=email,
        filename=file.filename,
        extracted_text_preview=cv_text[:500],
        candidate_score=result["candidate_score"],
        recommended_role=result["recommended_role"],
        status=result["status"],
        report=result["report"],
        email_subject=result["email_subject"],
        email_body=result["email_body"],
    )


@router.post("/analyze-text", response_model=CVAnalysisResponse)
async def analyze_cv_text(request: CVTextRequest):
    result = ApplicationService.evaluate(request.cv_text)

    return CVAnalysisResponse(
        name=request.name,
        email=request.email,
        filename="text-input",
        extracted_text_preview=request.cv_text[:500],
        candidate_score=result["candidate_score"],
        recommended_role=result["recommended_role"],
        status=result["status"],
        report=result["report"],
        email_subject=result["email_subject"],
        email_body=result["email_body"],
    )