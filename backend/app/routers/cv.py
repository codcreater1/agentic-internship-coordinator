from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel, EmailStr

from app.models.application import ApplicationResponse
from app.models.cv import CVAnalysisResponse
from app.services import application_repository as repo
from app.services.application_service import ApplicationService
from app.services.contract_service import ContractService
from app.services.cv_pdf_service import CVPDFService
from app.services.storage_service import storage_service

router = APIRouter(prefix="/cv", tags=["cv"])


class CVTextRequest(BaseModel):
    name: str
    email: EmailStr
    cv_text: str


def create_unsigned_contract(name: str, email: str, result: dict) -> str:
    """Generate the internship agreement PDF (unsigned). The coordinator signs
    it later in the dashboard via /applications/{index}/sign."""
    contract_task_id, task_dir = storage_service.create_task()

    ContractService.create_contract_pdf(
        name=name,
        email=email,
        recommended_role=result["recommended_role"],
        candidate_score=result["candidate_score"],
        output_path=task_dir / "original.pdf",
    )

    return contract_task_id


def _persist_application(name, email, result, contract_task_id):
    """Store the analysed candidate so it shows up in the dashboard."""
    contract_pdf_path = None
    if contract_task_id:
        try:
            contract_pdf_path = str(storage_service.original_path(contract_task_id))
        except Exception:
            pass

    repo.add(
        ApplicationResponse(
            name=name,
            email=email,
            candidate_score=result["candidate_score"],
            recommended_role=result["recommended_role"],
            status=result["status"],
            report=result["report"],
            email_subject=result["email_subject"],
            email_body=result["email_body"],
            contract_pdf_path=contract_pdf_path,
            signed_contract_path=None,
            contract_task_id=contract_task_id,
            signed_contract_download_url=None,
        )
    )


_AWAITING_SIGNATURE_NOTE = (
    "\n\nYour internship agreement has been generated and is awaiting "
    "coordinator signature. We will share the signed copy with you shortly."
)


@router.post("/analyze", response_model=CVAnalysisResponse)
async def analyze_cv(
    name: str = Form(...),
    email: str = Form(...),
    file: UploadFile = File(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    cv_text = await CVPDFService.extract_text_from_pdf(file)

    if not cv_text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    result = ApplicationService.evaluate(cv_text, candidate_name=name)
    resolved_name = result.get("extracted_name") or name

    contract_task_id = None
    if result["status"] == "interview":
        contract_task_id = create_unsigned_contract(name=resolved_name, email=email, result=result)
        result["email_body"] += _AWAITING_SIGNATURE_NOTE

    _persist_application(resolved_name, email, result, contract_task_id)

    return CVAnalysisResponse(
        name=resolved_name,
        email=email,
        filename=file.filename,
        extracted_text_preview=cv_text[:500],
        candidate_score=result["candidate_score"],
        recommended_role=result["recommended_role"],
        status=result["status"],
        report=result["report"],
        email_subject=result["email_subject"],
        email_body=result["email_body"],
        contract_task_id=contract_task_id,
        signed_contract_download_url=None,
    )


@router.post("/analyze-text", response_model=CVAnalysisResponse)
async def analyze_cv_text(request: CVTextRequest):
    result = ApplicationService.evaluate(request.cv_text, candidate_name=request.name)
    resolved_name = result.get("extracted_name") or request.name

    contract_task_id = None
    if result["status"] == "interview":
        contract_task_id = create_unsigned_contract(
            name=resolved_name, email=request.email, result=result
        )
        result["email_body"] += _AWAITING_SIGNATURE_NOTE

    _persist_application(resolved_name, request.email, result, contract_task_id)

    return CVAnalysisResponse(
        name=resolved_name,
        email=request.email,
        filename="text-input",
        extracted_text_preview=request.cv_text[:500],
        candidate_score=result["candidate_score"],
        recommended_role=result["recommended_role"],
        status=result["status"],
        report=result["report"],
        email_subject=result["email_subject"],
        email_body=result["email_body"],
        contract_task_id=contract_task_id,
        signed_contract_download_url=None,
    )
