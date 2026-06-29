from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "pdf_converter",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.pdf_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # one task per worker at a time — PDF conversion is CPU-bound
    task_acks_late=True,           # only ack after task completes, so crashes don't lose jobs
)
