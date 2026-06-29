import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, Query
import aiofiles

from app.core.config import settings
from app.schemas.conversion import ExtractionResult, ErrorResponse
from app.services.pdf_extractor import extract_pdf_content

router = APIRouter(prefix="/extract", tags=["Extract"])


@router.post(
    "/text-and-images",
    response_model=ExtractionResult,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}},
    summary="Extract text and images from a PDF",
    description=(
        "Returns all text (copy-pastable, per page) and all embedded images "
        "as base64-encoded data URIs. Ideal for mobile clients that need raw content."
    ),
)
async def extract_content(
    file: UploadFile = File(...),
    include_images: bool = Query(True, description="Set false to skip image extraction (faster)"),
):
    _validate_pdf(file)

    pdf_path = await _save_upload(file)
    try:
        result = extract_pdf_content(pdf_path)
        if not include_images:
            result.images = []
            for page in result.pages:
                page.image_count = 0
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}")
    finally:
        pdf_path.unlink(missing_ok=True)

    return result


@router.post(
    "/text-only",
    summary="Extract plain text from a PDF",
    description="Lightweight endpoint — returns only the full copy-pastable text, no images.",
)
async def extract_text_only(file: UploadFile = File(...)):
    _validate_pdf(file)

    pdf_path = await _save_upload(file)
    try:
        result = extract_pdf_content(pdf_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}")
    finally:
        pdf_path.unlink(missing_ok=True)

    return {
        "filename": result.filename,
        "total_pages": result.total_pages,
        "full_text": result.full_text,
        "pages": [{"page_number": p.page_number, "text": p.text} for p in result.pages],
    }


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
