# app/api/v1/endpoints/commands.py
import logging, traceback
from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from app.api.deps import api_key_auth
from app.core.config import settings
from app.schemas.command import CommandRequest, CommandResponse
from app.services.command_service import dispatch_command

logger = logging.getLogger("commands")
router = APIRouter()

@router.post("/", response_model=CommandResponse, status_code=status.HTTP_200_OK)
async def execute_command(req: CommandRequest, _=Depends(api_key_auth)):
    try:
        data = dispatch_command(req.type, req.payload)
        return CommandResponse(success=True, data=data, correlation_id=req.correlation_id)
    except ValueError as e:
        # Erros de input → 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unhandled error processing command %s", req.type)
        if settings.DEBUG:
            tb = traceback.format_exc()
            return CommandResponse(
                success=False, error=f"{e.__class__.__name__}: {e}\n{tb}",
                correlation_id=req.correlation_id
            )
        return CommandResponse(success=False, error="internal_error", correlation_id=req.correlation_id)
