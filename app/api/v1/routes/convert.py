import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.db.models import Job
from app.tasks.pdf_tasks import convert_pdf_task, convert_docx_to_pdf_task
from app.services.image_converter import convert_image_to_pdf

router = APIRouter(prefix="/convert", tags=["Convert"])

_IMAGE_CONTENT_TYPES = ("image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff")
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")
_DOCX_CONTENT_TYPES = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/octet-stream",
)


@router.post(
    "/to-docx",
    summary="Submit a PDF for Word conversion (async)",
    description=(
        "Saves the PDF, creates a job record, and queues conversion in the background. "
        "Returns a job_id immediately — poll GET /api/v1/jobs/{job_id} for status."
    ),
)
async def submit_convert_job(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    _validate_pdf(file)

    pdf_path = await _save_upload(file, ".pdf")

    job = Job(original_filename=file.filename or pdf_path.name)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    convert_pdf_task.delay(job.id, str(pdf_path))

    return {"job_id": job.id, "status": "pending"}


@router.post(
    "/word-to-pdf",
    summary="Submit a Word document for PDF conversion (async)",
    description=(
        "Saves the .docx, creates a job record, and queues LibreOffice conversion in the "
        "background. Returns a job_id immediately — poll GET /api/v1/jobs/{job_id} for status."
    ),
)
async def submit_word_to_pdf_job(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    _validate_docx(file)

    docx_path = await _save_upload(file, ".docx")

    job = Job(original_filename=file.filename or docx_path.name)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    convert_docx_to_pdf_task.delay(job.id, str(docx_path))

    return {"job_id": job.id, "status": "pending"}


@router.post(
    "/image-to-pdf",
    summary="Convert an image to PDF (synchronous)",
    description="Uploads an image (JPEG/PNG/WebP/BMP/TIFF) and returns the converted PDF immediately.",
)
async def image_to_pdf(file: UploadFile = File(...)):
    _validate_image(file)

    ext = Path(file.filename or "").suffix.lower() or ".img"
    image_path = await _save_upload(file, ext)
    try:
        result = convert_image_to_pdf(image_path, settings.OUTPUT_DIR)
        return result
    finally:
        image_path.unlink(missing_ok=True)


@router.get(
    "/download/{filename}",
    summary="Download a converted .docx file",
)
async def download_file(filename: str):
    file_path = settings.OUTPUT_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found or already deleted")

    media_type = (
        "application/pdf" if filename.lower().endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(path=str(file_path), filename=filename, media_type=media_type)


def _validate_pdf(file: UploadFile) -> None:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if file.filename and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")


def _validate_docx(file: UploadFile) -> None:
    if file.content_type not in _DOCX_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only Word (.docx) files are accepted")
    if file.filename and not file.filename.lower().endswith((".docx", ".doc")):
        raise HTTPException(status_code=400, detail="Only Word (.docx) files are accepted")


def _validate_image(file: UploadFile) -> None:
    if file.content_type not in _IMAGE_CONTENT_TYPES + ("application/octet-stream",):
        raise HTTPException(status_code=400, detail="Only image files are accepted")
    if file.filename and not file.filename.lower().endswith(_IMAGE_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only image files are accepted")


async def _save_upload(file: UploadFile, extension: str) -> Path:
    unique_name = f"{uuid.uuid4().hex}{extension}"
    dest = settings.UPLOAD_DIR / unique_name

    async with aiofiles.open(dest, "wb") as out:
        total = 0
        chunk_size = 1024 * 64
        while chunk := await file.read(chunk_size):
            total += len(chunk)
            if total > settings.max_file_size_bytes:
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB",
                )
            await out.write(chunk)

    return dest
