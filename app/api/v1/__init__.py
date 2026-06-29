from fastapi import APIRouter
from app.api.v1.routes import convert, extract, jobs

router = APIRouter(prefix="/api/v1")
router.include_router(convert.router)
router.include_router(extract.router)
router.include_router(jobs.router)
