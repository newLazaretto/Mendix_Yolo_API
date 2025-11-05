from fastapi import APIRouter
from .endpoints import health, commands, ingest

router = APIRouter()
router.include_router(health.router)  # GET /api/v1/health
router.include_router(commands.router, prefix="/commands", tags=["commands"])  # /api/v1/commands
router.include_router(ingest.router, tags=["ingest"])
