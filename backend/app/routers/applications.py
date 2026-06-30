import base64

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.application import (
    Application,
    ApplicationResponse,
    SignApplicationRequest,
)
from app.services.application_service import ApplicationService
from app.services.contract_service import ContractService
from app.services.pdf_service import pdf_service
from app.services.storage_service import storage_service
from app.services.token_service import create_download_token

router = APIRouter(prefix="/applications", tags=["applications"])

APPLICATIONS_DB: list[ApplicationResponse] = []


def process_application(application: Application) -> ApplicationResponse:
    result = ApplicationService.evaluate(application.cv_text)

    contract_pdf_path = None
    contract_task_id = None

    if result["status"] == "interview":
        contract_task_id, task_dir = storage_service.create_task()

        original_contract_path = task_dir / "original.pdf"

        ContractService.create_contract_pdf(
            name=application.name,
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
        name=application.name,
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
    return APPLICATIONS_DB


@router.post("/", response_model=ApplicationResponse)
def create_application(application: Application):
    response = process_application(application)
    APPLICATIONS_DB.insert(0, response)
    return response


@router.post("/from-n8n", response_model=ApplicationResponse)
def create_application_from_n8n(application: Application):
    response = process_application(application)
    APPLICATIONS_DB.insert(0, response)
    return response


@router.get("/{index}", response_model=ApplicationResponse)
def get_application(index: int):
    if index < 0 or index >= len(APPLICATIONS_DB):
        raise HTTPException(status_code=404, detail="Application not found")

    return APPLICATIONS_DB[index]


@router.get("/{index}/contract-preview")
def preview_contract(index: int):
    if index < 0 or index >= len(APPLICATIONS_DB):
        raise HTTPException(status_code=404, detail="Application not found")

    application = APPLICATIONS_DB[index]

    if not application.contract_pdf_path:
        raise HTTPException(status_code=404, detail="Contract not generated")

    return FileResponse(
        path=application.contract_pdf_path,
        media_type="application/pdf",
        filename="contract.pdf",
    )


@router.post("/{index}/sign", response_model=ApplicationResponse)
def sign_application(index: int, request: SignApplicationRequest):
    if index < 0 or index >= len(APPLICATIONS_DB):
        raise HTTPException(status_code=404, detail="Application not found")

    application = APPLICATIONS_DB[index]

    if not application.contract_task_id or not application.contract_pdf_path:
        raise HTTPException(status_code=400, detail="Contract not generated")

    try:
        signature_base64 = request.signature_image_base64

        if "," in signature_base64:
            signature_base64 = signature_base64.split(",", 1)[1]

        signature_bytes = base64.b64decode(signature_base64)

    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature image")

    task_dir = storage_service.task_dir(application.contract_task_id)
    signed_path = task_dir / "signed.pdf"

    pdf_service.embed_signature(
        source_pdf=task_dir / "original.pdf",
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

    APPLICATIONS_DB[index] = application

    return application