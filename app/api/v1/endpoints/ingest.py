# app/api/v1/endpoints/ingest.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from app.api.deps import api_key_auth
from app.core.config import settings
from app.schemas.pipeline import InboundRequest, AggregatedPayload
from app.services.ingest_service import process_inbound_and_forward
import logging, traceback

router = APIRouter()

@router.post("/process-images", response_model=List[AggregatedPayload], status_code=status.HTTP_200_OK)
async def process_images(req: InboundRequest, _=Depends(api_key_auth)):
    try:
        payload_list, _processed = await process_inbound_and_forward(req)
        return payload_list
    except Exception as e:
        logging.exception("Erro no processamento")
        if settings.DEBUG:
            raise HTTPException(status_code=500, detail=f"{e.__class__.__name__}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="internal_error")
