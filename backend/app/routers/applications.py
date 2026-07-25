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
from app.services.application_service import (
    CONTRACT_CRITICAL_FIELDS,
    ApplicationService,
)
from app.services.contract_service import SIGNATURE_DATE_POS, ContractService
from app.services.pdf_service import pdf_service
from app.services.storage_service import storage_service
from app.services.token_service import create_download_token

router = APIRouter(prefix="/applications", tags=["applications"])


def process_application(application: Application) -> ApplicationResponse:
    result = ApplicationService.evaluate(application.cv_text, candidate_name=application.name)
    resolved_name = result.get("extracted_name") or application.name
    missing_fields = result.get("missing_fields", [])

    contract_pdf_path = None
    contract_task_id = None

    # Only an application that reached `interview` gets an agreement, and the
    # evaluation can only return `interview` once every mandatory placement
    # field is present. The second half of that condition is asserted here too:
    # the contract is the one artefact that must never be produced from an
    # incomplete application, so it does not rely on the status alone.
    if result["status"] == "interview" and not missing_fields:
        contract_task_id, task_dir = storage_service.create_task()

        original_contract_path = task_dir / "original.pdf"

        ContractService.create_contract_pdf(
            name=resolved_name,
            email=application.email,
            recommended_role=result["recommended_role"],
            candidate_score=result["candidate_score"],
            company_name=result["company_name"],
            supervisor_name=result["supervisor_name"],
            supervisor_contact=result["supervisor_contact"],
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
        company_name=result["company_name"],
        supervisor_name=result["supervisor_name"],
        supervisor_contact=result["supervisor_contact"],
        missing_fields=missing_fields,
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


def _require_by_id(application_id: str) -> ApplicationResponse:
    """Resolve an application by its stable id.

    Everything that acts on a specific candidate addresses them this way. The
    list position is not a safe handle: applications arrive continuously from
    n8n and the list is ordered newest-first, so an index captured when the
    dashboard loaded points at a different candidate as soon as one more
    application lands. Signing or emailing the wrong person's agreement is
    exactly the failure that must not be possible.
    """
    application = repo.get_by_id(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


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


@router.post("/by-id/{application_id}/approve", response_model=ApplicationResponse)
def approve_application(application_id: str):
    """Coordinator override: manually move a candidate to `interview` and issue
    the contract, for a borderline case the AI left at `pending` (or
    `request_clarification`). The coordinator's judgement outranks the score.

    The mandatory-field gate still holds: a contract must name a host
    organisation and workplace supervisor, so if those are missing the override
    is refused with the specific gaps — approving cannot fabricate them.
    """
    application = _require_by_id(application_id)

    if application.contract_task_id:
        raise HTTPException(status_code=409, detail="Application already has a contract")

    missing = [f for f in CONTRACT_CRITICAL_FIELDS if not getattr(application, f, "")]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                "Cannot issue a contract — the application is missing: "
                + ", ".join(f.replace("_", " ") for f in missing)
            ),
        )

    task_id, task_dir = storage_service.create_task()
    ContractService.create_contract_pdf(
        name=application.name,
        email=application.email,
        recommended_role=application.recommended_role,
        candidate_score=application.candidate_score,
        company_name=application.company_name,
        supervisor_name=application.supervisor_name,
        supervisor_contact=application.supervisor_contact,
        output_path=task_dir / "original.pdf",
    )

    application.status = "interview"
    application.missing_fields = []
    application.contract_task_id = task_id
    application.contract_pdf_path = str(storage_service.original_path(task_id))
    return repo.update(application)


@router.get("/by-id/{application_id}/contract-preview")
def preview_contract(application_id: str):
    application = _require_by_id(application_id)

    if not application.contract_pdf_path or not Path(application.contract_pdf_path).is_file():
        raise HTTPException(status_code=404, detail="Contract not available")

    return FileResponse(
        path=application.contract_pdf_path,
        media_type="application/pdf",
        filename="contract.pdf",
        content_disposition_type="inline",
    )


@router.post("/by-id/{application_id}/sign", response_model=ApplicationResponse)
def sign_application(application_id: str, request: SignApplicationRequest):
    application = _require_by_id(application_id)

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

    # Stamp the date the coordinator actually signs, not the date the contract
    # was generated (which can be days earlier).
    signed_on = datetime.now(timezone.utc).date().isoformat()

    pdf_service.embed_signature(
        source_pdf=source_pdf,
        output_pdf=signed_path,
        image_bytes=signature_bytes,
        page_index=0,
        x=request.x,
        y=request.y,
        w=request.w,
        h=request.h,
        text_stamps=[(signed_on, *SIGNATURE_DATE_POS)],
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


@router.post("/by-id/{application_id}/send-contract", response_model=ApplicationResponse)
def send_contract(application_id: str, request: SendContractRequest):
    """Email the signed contract to a coordinator-chosen recipient, via n8n."""
    application = _require_by_id(application_id)

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
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except email_service.EmailSendError as exc:
        # 424 (not 502): a CDN in front of the API rewrites upstream 5xx into its
        # own error page, which would hide the reason from the coordinator.
        raise HTTPException(status_code=424, detail=str(exc)) from exc

    application.contract_sent_to = request.to
    application.contract_sent_at = datetime.now(timezone.utc).isoformat()

    return repo.update(application)