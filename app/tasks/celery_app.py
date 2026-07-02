from celery import Celery
from app.core.config import settings

# Local/dev mode: set CELERY_TASK_ALWAYS_EAGER=true to run tasks inline in the API
# process instead of dispatching to a Redis-backed worker. Lets the whole backend run
# with only Python + SQLite — no Redis broker and no separate `celery worker`. In eager
# mode we also point Celery at an in-memory broker/backend so it never imports or
# connects to Redis.
_eager = settings.CELERY_TASK_ALWAYS_EAGER
_broker = "memory://" if _eager else settings.REDIS_URL
_backend = "cache+memory://" if _eager else settings.REDIS_URL

celery_app = Celery(
    "pdf_converter",
    broker=_broker,
    backend=_backend,
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
    task_always_eager=_eager,
    task_eager_propagates=_eager,
)
