from datetime import datetime
from pathlib import Path

from app.tasks.celery_app import celery_app
from app.db.sync_session import get_sync_db
from app.db.models import Job
from app.services.pdf_converter import convert_pdf_to_docx
from app.services.docx_converter import convert_docx_to_pdf
from app.core.config import settings


def _run_conversion_job(self, job_id: str, src_path_str: str, convert_fn):
    db = get_sync_db()
    try:
        job: Job | None = db.get(Job, job_id)
        if not job:
            return

        job.status = "processing"
        job.updated_at = datetime.utcnow()
        db.commit()

        result = convert_fn(Path(src_path_str), settings.OUTPUT_DIR)

        job.status = "done"
        job.result_filename = result.filename
        job.download_url = result.download_url
        job.total_pages = result.total_pages
        job.file_size_bytes = result.file_size_bytes
        job.updated_at = datetime.utcnow()
        db.commit()

    except Exception as exc:
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error = str(exc)
            job.updated_at = datetime.utcnow()
            db.commit()
        raise self.retry(exc=exc, countdown=5)

    finally:
        Path(src_path_str).unlink(missing_ok=True)
        db.close()


@celery_app.task(bind=True, name="tasks.convert_pdf", max_retries=2)
def convert_pdf_task(self, job_id: str, pdf_path_str: str):
    _run_conversion_job(self, job_id, pdf_path_str, convert_pdf_to_docx)


@celery_app.task(bind=True, name="tasks.convert_docx_to_pdf", max_retries=2)
def convert_docx_to_pdf_task(self, job_id: str, docx_path_str: str):
    _run_conversion_job(self, job_id, docx_path_str, convert_docx_to_pdf)
