from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "/{job_id}",
    summary="Poll job status",
    description=(
        "Mobile app calls this every 2–3 seconds after submitting a conversion job. "
        "When status is 'done', download_url is ready to use."
    ),
)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job: Job | None = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "original_filename": job.original_filename,
        "download_url": job.download_url,
        "total_pages": job.total_pages,
        "file_size_bytes": job.file_size_bytes,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
