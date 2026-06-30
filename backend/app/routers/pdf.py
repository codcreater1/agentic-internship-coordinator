"""PDF signing API — three endpoints."""

from __future__ import annotations

import logging

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File,
    Form, HTTPException, UploadFile, status,
)
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.exceptions import AppError, SignedPdfNotReadyError, TaskNotFoundError
from app.core.models import PageGeometry, SignResponse, UploadResponse
from app.services.file_service import FileService, file_service
from app.services.pdf_service import PdfService, pdf_service
from app.services.storage_service import StorageService, storage_service
from app.services.token_service import (
    create_download_token,
    verify_download_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdf", tags=["pdf"])


def get_file_service() -> FileService:
    return file_service


def get_pdf_service() -> PdfService:
    return pdf_service


def get_storage_service() -> StorageService:
    return storage_service


def _raise_http(err: AppError) -> None:
    raise HTTPException(status_code=err.http_status, detail=err.detail)


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    file: UploadFile = File(...),
    fs: FileService = Depends(get_file_service),
    ps: PdfService = Depends(get_pdf_service),
    ss: StorageService = Depends(get_storage_service),
) -> UploadResponse:
    task_id, task_dir = ss.create_task()
    pdf_path = task_dir / "original.pdf"
    succeeded = False

    try:
        size = await fs.stream_pdf_to_disk(file, pdf_path)

        try:
            pages = ps.describe_pages(pdf_path)
        except AppError as err:
            _raise_http(err)

        succeeded = True

    except AppError as err:
        _raise_http(err)

    finally:
        if not succeeded:
            ss.remove_task(task_id)

    return UploadResponse(
        task_id=task_id,
        page_count=len(pages),
        pages=[
            PageGeometry(
                index=p.index,
                width=p.width,
                height=p.height,
            )
            for p in pages
        ],
        upload_size_bytes=size,
    )


@router.post("/sign", response_model=SignResponse)
async def sign_pdf(
    task_id: str = Form(...),
    image: UploadFile = File(...),
    page: int = Form(..., ge=0),
    x: float = Form(...),
    y: float = Form(...),
    w: float = Form(..., gt=0),
    h: float = Form(..., gt=0),
    fs: FileService = Depends(get_file_service),
    ps: PdfService = Depends(get_pdf_service),
    ss: StorageService = Depends(get_storage_service),
) -> SignResponse:

    try:
        source = ss.original_path(task_id)
    except TaskNotFoundError as err:
        _raise_http(err)

    output = source.parent / "signed.pdf"

    try:
        image_bytes = await fs.read_signature_image(image)
    except AppError as err:
        _raise_http(err)

    try:
        ps.embed_signature(
            source,
            output,
            image_bytes=image_bytes,
            page_index=page,
            x=x,
            y=y,
            w=w,
            h=h,
        )

    except AppError as err:
        _raise_http(err)

    except Exception:
        logger.exception(
            "Unexpected error while signing task %s",
            task_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to sign PDF.",
        )

    token = create_download_token(task_id)

    download_url = (
        f"{settings.api_prefix}/pdf/download/{task_id}"
        f"?token={token}"
    )

    return SignResponse(
        task_id=task_id,
        page=page,
        download_url=download_url,
    )


@router.get("/download/{task_id}", response_class=FileResponse)
async def download_signed(
    task_id: str,
    token: str,
    background: BackgroundTasks,
    ss: StorageService = Depends(get_storage_service),
) -> FileResponse:

    try:
        token_task_id = verify_download_token(token)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Invalid or expired download token",
        )

    if token_task_id != task_id:
        raise HTTPException(
            status_code=403,
            detail="Token does not match task",
        )

    try:
        path = ss.signed_path(task_id)
    except TaskNotFoundError as err:
        _raise_http(err)

    if not path.is_file():
        _raise_http(SignedPdfNotReadyError())

    background.add_task(
        ss.remove_task,
        task_id,
    )

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename="signed.pdf",
        headers={
            "Cache-Control": "no-store",
        },
    )
