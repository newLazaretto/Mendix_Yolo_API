# app/services/ingest_service.py
from typing import Tuple, List, Dict, Any
from datetime import timezone
from app.core.config import settings
from app.schemas.pipeline import (
    InboundRequest, SourceCollection,
    TemperatureRecord, ValveRecord, MixedResponse
)
from app.services.external_client import fetch_from_source, post_to_sink_records
from app.services.image_utils import base64_to_rgb_ndarray
from app.services.temperature import to_temperature_vector
from app.services.angle_service import valves_from_image_rgb

def _iso_z(dt):
    # garante UTC e sufixo 'Z'
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def _should_process(is_thermal: bool) -> bool:
    return is_thermal or settings.PROCESS_NON_THERMAL

def _normalize_side(side: str) -> str:
    if not side:
        return side
    mapped = settings.SIDE_MAP.get(side.upper())
    return mapped if mapped else side

async def process_inbound_mixed(
    req: InboundRequest,
) -> Tuple[MixedResponse, int]:
    collections: List[SourceCollection] = await fetch_from_source(req)

    flat_temps: List[TemperatureRecord] = []
    flat_valves: List[ValveRecord] = []
    sink_records: List[Dict[str, Any]] = []
    processed_total = 0

    for col in collections:
        ts = _iso_z(col.Date)
        for im in col.Images:
            try:
                img_rgb = base64_to_rgb_ndarray(im.Base64String)
            except Exception as e:
                print(f"[PIPE] FAIL decode {im.Name}: {e}")
                continue

            side = _normalize_side(im.Side)
            port = int(im.Port)
            section = im.Section

            if _should_process(im.IsThermal):
                try:
                    temps = to_temperature_vector(
                        img_rgb,
                        settings.TEMP_MIN_DEFAULT,
                        settings.TEMP_MAX_DEFAULT,
                        settings.MAX_TEMPERATURE_VECTOR_LEN,
                    )
                except Exception as e:
                    print(f"[PIPE] FAIL temp {im.Name}: {e}")
                    temps = []

                if temps:
                    for t in temps:
                        rec = TemperatureRecord(
                            Timestamp=ts,
                            Side=side,
                            Port=port,
                            Section=section,
                            Temperature=float(t),
                        )
                        flat_temps.append(rec)
                        sink_records.append(rec.model_dump())
                    processed_total += 1
                else:
                    print(f"[PIPE] SKIP temp {im.Name}: empty temps")
            else:
                try:
                    vals = valves_from_image_rgb(img_rgb) 
                except Exception as e:
                    print(f"[PIPE] FAIL valve {im.Name}: {e}")
                    vals = []

                v1 = float(vals[0]) if len(vals) > 0 else None
                v2 = float(vals[1]) if len(vals) > 1 else None
                v3 = float(vals[2]) if len(vals) > 2 else None

                flat_valves.append(
                    ValveRecord(
                        Timestamp=ts,
                        Side=side,
                        Port=port,
                        Section=section,
                        Valve_1=v1, Valve_2=v2, Valve_3=v3,
                    )
                )

    if sink_records:
        await post_to_sink_records(sink_records)

    return MixedResponse(temperatures=flat_temps, valves=flat_valves), processed_total