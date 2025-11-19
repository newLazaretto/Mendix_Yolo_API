from fastapi import APIRouter
from .endpoints import health, ingest

router = APIRouter()
router.include_router(health.router)  # GET /api/v1/health
router.include_router(ingest.router, tags=["ingest"])
