from datetime import datetime
from pathlib import Path

from app.tasks.celery_app import celery_app
from app.db.sync_session import get_sync_db
from app.db.models import Job
from app.services.pdf_converter import convert_pdf_to_docx
from app.core.config import settings


@celery_app.task(bind=True, name="tasks.convert_pdf", max_retries=2)
def convert_pdf_task(self, job_id: str, pdf_path_str: str):
    db = get_sync_db()
    try:
        job: Job | None = db.get(Job, job_id)
        if not job:
            return

        job.status = "processing"
        job.updated_at = datetime.utcnow()
        db.commit()

        pdf_path = Path(pdf_path_str)
        result = convert_pdf_to_docx(pdf_path, settings.OUTPUT_DIR)

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
        Path(pdf_path_str).unlink(missing_ok=True)
        db.close()
