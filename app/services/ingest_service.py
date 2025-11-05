# app/services/ingest_service.py
from typing import Tuple, List, Dict, Any
from app.core.config import settings
from app.schemas.pipeline import InboundRequest, StoredImage, AggregatedPayload, SourceResponse
from app.services.external_client import fetch_from_source, post_to_sink_records
from app.services.image_utils import base64_to_rgb_ndarray
from app.services.temperature import to_temperature_vector
from datetime import timezone

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

def _section_string(name: str, section: int) -> str:
    return name if name and name.strip() else f"S{section}"

async def process_inbound_and_forward(req: InboundRequest) -> Tuple[AggregatedPayload, int]:
    # 1) GET na fonte
    src: SourceResponse = await fetch_from_source(req)

    # 2) processa imagens em memória
    stored_images: List[StoredImage] = []
    sink_records: List[Dict[str, Any]] = []
    processed = 0

    field_name = settings.SINK_TEMPERATURE_FIELD_NAME  # ex.: "Temperature"
    equipment = (req.Equipment or settings.DEFAULT_EQUIPMENT).strip()

    for im in src.Images:
        temps: List[float] = []
        try:
            img_rgb = base64_to_rgb_ndarray(im.Base64String)
            if _should_process(im.IsThermal):
                temps = to_temperature_vector(
                    img_rgb,
                    settings.TEMP_MIN_DEFAULT,
                    settings.TEMP_MAX_DEFAULT,
                    settings.MAX_TEMPERATURE_VECTOR_LEN,
                )
                processed += 1
            else:
                temps = []
            print(f"[PIPE] OK {im.Name} thermal={im.IsThermal} len={len(temps)}")  # <<< LOG
        except Exception as e:
            print(f"[PIPE] FAIL {im.Name}: {e}")  # <<< LOG
            temps = []  # falha de processamento -> segue sem vetor

        stored_images.append(
            StoredImage(
                Side=im.Side,
                Port=im.Port,
                Section=im.Section,
                IsThermal=im.IsThermal,
                Name=im.Name,
                temperatures=temps,
                length=len(temps),
            )
        )

        if temps:
            sink_records.append({
                "Timestamp": _iso_z(src.Date),
                "Equipment": equipment,
                "Side": _normalize_side(im.Side),
                "Port": int(im.Port),
                "Section": _section_string(im.Name, im.Section),
                field_name: [float(x) for x in temps],
            })
        else:
            print(f"[PIPE] SKIP {im.Name}: empty temps")

    aggregated = AggregatedPayload(Side=src.Side, Date=src.Date, Images=stored_images)

    # 3) monta e POSTa para o sink (com vetor)
    #equipment = (req.Equipment or settings.DEFAULT_EQUIPMENT).strip()

    #sink_records: List[Dict[str, Any]] = []
    '''
    for im in stored_images:
        if not im.temperatures:
            print(f"[PIPE] SKIP {im.Name}: empty temps")  # <<< LOG
            continue
        sink_records.append({
            "Timestamp": _iso_z(src.Date),                   # string ISO+Z
            "Equipment": equipment,
            "Side": _normalize_side(im.Side),
            "Port": int(im.Port),
            "Section": _section_string(im.Name, im.Section),
            settings.SINK_TEMPERATURE_FIELD_NAME: [float(x) for x in im.temperatures],
        })'''

    print(f"[PIPE] sink_records={len(sink_records)}") 
    if sink_records:
        await post_to_sink_records(sink_records)

    return aggregated, processed
