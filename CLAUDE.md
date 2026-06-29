# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

**Full stack (recommended):**
```bash
cp .env.example .env
docker compose up --build
```

**Local development (API only, requires Postgres + Redis running):**
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Celery worker (separate terminal):**
```bash
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
```

**Scale workers:**
```bash
docker compose up --scale worker=3
```

**Flower (Celery monitoring dashboard) — available at `localhost:5555` when using docker compose.**

## Database migrations

```bash
# Apply migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback one step
alembic downgrade -1
```

The `lifespan` hook in `app/main.py` calls `create_all` so tests and local runs work without running migrations first. In production, always use Alembic.

## Tests

```bash
pytest                          # all tests
pytest tests/test_extract.py    # single file
pytest -k "test_health"         # single test by name
```

Tests use `httpx.AsyncClient` with `ASGITransport` — no live server or database is needed for the existing tests.

## Architecture

### Request flow

**Synchronous extraction** (`POST /api/v1/extract/text-and-images`, `POST /api/v1/extract/text-only`):
1. File uploaded → saved to `uploads/` with a UUID name
2. `pdf_extractor.py` processes it synchronously with PyMuPDF (`fitz`)
3. File deleted from `uploads/` in a `finally` block
4. Response returned immediately — no job record, no DB

**Async conversion** (`POST /api/v1/convert/to-docx`):
1. File uploaded → saved to `uploads/`
2. A `Job` row is created in Postgres with `status=pending`
3. `convert_pdf_task.delay(job_id, pdf_path)` queues the task in Redis
4. API returns `{"job_id": ..., "status": "pending"}` immediately
5. Celery worker picks up the task, updates status to `processing`, runs `pdf2docx`, then writes `done`/`failed`
6. Client polls `GET /api/v1/jobs/{job_id}` until `status == "done"`, then downloads from `GET /api/v1/convert/download/{filename}`

### Dual session pattern

The API uses **async SQLAlchemy** (`app/db/session.py`, `asyncpg` driver) for FastAPI routes. Celery tasks are synchronous and use a separate **sync SQLAlchemy** session (`app/db/sync_session.py`, `psycopg2` driver). Both point to the same database. Do not use the async session inside Celery tasks.

### Key configuration (`app/core/config.py`)

All settings come from environment variables (`.env` file). Important ones:
- `DATABASE_URL` — async driver (`postgresql+asyncpg://...`)
- `DATABASE_SYNC_URL` — sync driver (`postgresql+psycopg2://...`)
- `REDIS_URL` — used as both broker and backend for Celery
- `UPLOAD_DIR` / `OUTPUT_DIR` — default to `uploads/` and `outputs/` at project root; auto-created on startup
- `MAX_FILE_SIZE_MB` — enforced during streaming upload (default 50)
- `ALLOWED_ORIGINS` — comma-separated list for CORS

### Job status lifecycle

`pending` → `processing` → `done` | `failed`

The task retries up to 2 times (`max_retries=2`) with a 5-second countdown on failure. The uploaded PDF is deleted from `uploads/` in the task's `finally` block regardless of outcome.

### PDF libraries

- **PyMuPDF (`fitz`)** — used for both text/image extraction and page-count in conversion
- **pdf2docx** — used only for the PDF→Word conversion; wraps LibreOffice-based conversion
