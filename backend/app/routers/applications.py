import base64
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.security import require_api_key
from app.models.application import (
    Application,
    ApplicationResponse,
    SendContractRequest,
    SignApplicationRequest,
)
from app.services import application_repository as repo
from app.services import email_service
from app.services.application_service import ApplicationService
from app.services.contract_service import ContractService
from app.services.pdf_service import pdf_service
from app.services.storage_service import storage_service
from app.services.token_service import create_download_token

router = APIRouter(prefix="/applications", tags=["applications"])


def process_application(application: Application) -> ApplicationResponse:
    result = ApplicationService.evaluate(application.cv_text, candidate_name=application.name)
    resolved_name = result.get("extracted_name") or application.name

    contract_pdf_path = None
    contract_task_id = None

    if result["status"] == "interview":
        contract_task_id, task_dir = storage_service.create_task()

        original_contract_path = task_dir / "original.pdf"

        ContractService.create_contract_pdf(
            name=resolved_name,
            email=application.email,
            recommended_role=result["recommended_role"],
            candidate_score=result["candidate_score"],
            output_path=original_contract_path,
        )

        contract_pdf_path = str(original_contract_path)

        result["email_body"] += (
            "\n\nYour internship agreement has been generated. "
            "It is waiting for coordinator signature."
        )

    return ApplicationResponse(
        name=resolved_name,
        email=application.email,
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


@router.get("/", response_model=list[ApplicationResponse])
def list_applications():
    return repo.list_all()


@router.post("/", response_model=ApplicationResponse)
def create_application(application: Application):
    return repo.add(process_application(application))


@router.post(
    "/from-n8n",
    response_model=ApplicationResponse,
    dependencies=[Depends(require_api_key)],
)
def create_application_from_n8n(application: Application):
    return repo.add(process_application(application))


@router.get("/{index}", response_model=ApplicationResponse)
def get_application(index: int):
    application = repo.get_by_index(index)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    return application


@router.delete("/by-id/{application_id}", status_code=204)
def delete_application(application_id: str):
    if not repo.delete(application_id):
        raise HTTPException(status_code=404, detail="Application not found")


@router.get("/{index}/contract-preview")
def preview_contract(index: int):
    application = repo.get_by_index(index)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.contract_pdf_path or not Path(application.contract_pdf_path).is_file():
        raise HTTPException(status_code=404, detail="Contract not available")

    return FileResponse(
        path=application.contract_pdf_path,
        media_type="application/pdf",
        filename="contract.pdf",
        content_disposition_type="inline",
    )


@router.post("/{index}/sign", response_model=ApplicationResponse)
def sign_application(index: int, request: SignApplicationRequest):
    application = repo.get_by_index(index)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.contract_task_id or not application.contract_pdf_path:
        raise HTTPException(status_code=400, detail="Contract not generated")

    try:
        signature_base64 = request.signature_image_base64

        if "," in signature_base64:
            signature_base64 = signature_base64.split(",", 1)[1]

        signature_bytes = base64.b64decode(signature_base64)

    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature image")

    try:
        source_pdf = storage_service.original_path(application.contract_task_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Contract file not available")

    signed_path = source_pdf.parent / "signed.pdf"

    pdf_service.embed_signature(
        source_pdf=source_pdf,
        output_pdf=signed_path,
        image_bytes=signature_bytes,
        page_index=0,
        x=request.x,
        y=request.y,
        w=request.w,
        h=request.h,
    )

    token = create_download_token(application.contract_task_id)
    download_url = f"/pdf/download/{application.contract_task_id}?token={token}"

    application.signed_contract_path = str(signed_path)
    application.signed_contract_download_url = download_url

    application.email_body += (
        "\n\nThe internship agreement has been signed by the coordinator.\n"
        f"Download link: {download_url}"
    )

    return repo.update(application)


@router.post("/{index}/send-contract", response_model=ApplicationResponse)
def send_contract(index: int, request: SendContractRequest):
    """Email the signed contract to a coordinator-chosen recipient, via n8n."""
    application = repo.get_by_index(index)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.signed_contract_path:
        raise HTTPException(
            status_code=400, detail="Contract has not been signed yet"
        )

    try:
        email_service.send_signed_contract(
            to=request.to,
            subject=request.subject,
            body=request.body,
            pdf_path=Path(application.signed_contract_path),
            candidate_name=application.name,
        )
    except email_service.EmailNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except email_service.EmailSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    application.contract_sent_to = request.to
    application.contract_sent_at = datetime.now(timezone.utc).isoformat()

    return repo.update(application)