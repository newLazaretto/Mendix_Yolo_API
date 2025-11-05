import httpx
import json
from urllib.parse import urljoin
from typing import List, Dict, Any
from app.core.config import settings
from app.schemas.pipeline import InboundRequest, SourceResponse

async def fetch_from_source(req: InboundRequest) -> SourceResponse:
    params = {"Date": req.Date.isoformat(), "Side": req.Side}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(settings.EXTERNAL_SOURCE_URL, params=params)
        r.raise_for_status()
        return SourceResponse.model_validate(r.json())

def build_sink_url() -> str:
    base = settings.SINK_BASE_URL
    if not base.endswith("/"):
        base += "/"
    return urljoin(base, settings.SINK_POST_THERMAL_PATH)

async def post_to_sink_records(records: List[Dict[str, Any]]) -> None:
    url = build_sink_url()
    batch_size = getattr(settings, "SINK_BATCH_SIZE", 1)  # 1 = um item por POST
    async with httpx.AsyncClient(timeout=120, http2=False, headers={"Connection": "close"}) as client:
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            # Pré-serializa JSON de forma estrita (sem NaN/Inf) e compacta
            try:
                payload = json.dumps(batch, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            except ValueError as ve:
                # Se houver NaN/Inf, loga e segue pro próximo item
                print(f"[SINK] JSON serialize error (NaN/Inf?): {ve}")
                continue

            print(f"[SINK] POST {url} items={len(batch)} (i={i}) bytes={len(payload)}")
            resp = await client.post(url, content=payload, headers={"Content-Type": "application/json"})
            print(f"[SINK] status={resp.status_code} body={resp.text[:200]}")
            resp.raise_for_status()
