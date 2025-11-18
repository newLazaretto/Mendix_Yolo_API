# app/api/v1/endpoints/ingest.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from app.api.deps import api_key_auth
from app.core.config import settings
from app.schemas.pipeline import InboundRequest, MixedResponse
from app.services.ingest_service import process_inbound_mixed
import logging, traceback

router = APIRouter()


@router.post("/process-images", response_model=MixedResponse, status_code=status.HTTP_200_OK)
async def process_images_mixed(req: InboundRequest, _=Depends(api_key_auth)):
    try:
        payload, _processed = await process_inbound_mixed(req)
        return payload
    except Exception as e:
        logging.exception("Erro no processamento (mixed)")
        if settings.DEBUG:
            raise HTTPException(status_code=500, detail=f"{e.__class__.__name__}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="internal_error")