import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.db.models import Job
from app.tasks.pdf_tasks import convert_pdf_task

router = APIRouter(prefix="/convert", tags=["Convert"])


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

    pdf_path = await _save_upload(file)

    job = Job(original_filename=file.filename or pdf_path.name)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    convert_pdf_task.delay(job.id, str(pdf_path))

    return {"job_id": job.id, "status": "pending"}


@router.get(
    "/download/{filename}",
    summary="Download a converted .docx file",
)
async def download_file(filename: str):
    file_path = settings.OUTPUT_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found or already deleted")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def _validate_pdf(file: UploadFile) -> None:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    if file.filename and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")


async def _save_upload(file: UploadFile) -> Path:
    unique_name = f"{uuid.uuid4().hex}.pdf"
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
