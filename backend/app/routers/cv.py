from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel, EmailStr

from app.models.cv import CVAnalysisResponse
from app.services.application_service import ApplicationService
from app.services.contract_service import ContractService
from app.services.cv_pdf_service import CVPDFService
from app.services.pdf_service import pdf_service
from app.services.signature_image_service import SignatureImageService
from app.services.storage_service import storage_service
from app.services.token_service import create_download_token

router = APIRouter(prefix="/cv", tags=["cv"])


class CVTextRequest(BaseModel):
    name: str
    email: EmailStr
    cv_text: str


def create_signed_contract(name: str, email: str, result: dict):
    contract_task_id, task_dir = storage_service.create_task()

    original_contract_path = task_dir / "original.pdf"
    signed_path = task_dir / "signed.pdf"

    ContractService.create_contract_pdf(
        name=name,
        email=email,
        recommended_role=result["recommended_role"],
        candidate_score=result["candidate_score"],
        output_path=original_contract_path,
    )

    signature_bytes = SignatureImageService.create_company_signature()

    pdf_service.embed_signature(
        source_pdf=original_contract_path,
        output_pdf=signed_path,
        image_bytes=signature_bytes,
        page_index=0,
        x=70,
        y=600,
        w=220,
        h=70,
    )

    token = create_download_token(contract_task_id)
    download_url = f"/pdf/download/{contract_task_id}?token={token}"

    return contract_task_id, download_url


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

    result = ApplicationService.evaluate(cv_text)

    contract_task_id = None
    signed_contract_download_url = None

    if result["status"] == "interview":
        contract_task_id, signed_contract_download_url = create_signed_contract(
            name=name,
            email=email,
            result=result,
        )

        result["email_body"] += (
            "\n\nYour internship agreement has been generated and signed digitally.\n"
            f"Download link: {signed_contract_download_url}"
        )

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
        contract_task_id=contract_task_id,
        signed_contract_download_url=signed_contract_download_url,
    )


@router.post("/analyze-text", response_model=CVAnalysisResponse)
async def analyze_cv_text(request: CVTextRequest):
    result = ApplicationService.evaluate(request.cv_text)

    contract_task_id = None
    signed_contract_download_url = None

    if result["status"] == "interview":
        contract_task_id, signed_contract_download_url = create_signed_contract(
            name=request.name,
            email=request.email,
            result=result,
        )

        result["email_body"] += (
            "\n\nYour internship agreement has been generated and signed digitally.\n"
            f"Download link: {signed_contract_download_url}"
        )

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
        contract_task_id=contract_task_id,
        signed_contract_download_url=signed_contract_download_url,
    )