from typing import Dict, Any
import numpy as np
from app.schemas.command import CommandType
from app.services.angle_service import analyze_angles
from app.services.image_utils import base64_to_rgb_ndarray
from app.services.temperature import build_temperature_matrix_linear, stats_from_bbox
from app.services.roi_detect import ROIBoxDetector

# Aqui você pluga seus serviços reais (ex.: extrator de temperaturas, banco, etc.)
# Por enquanto, deixo mocks para explicar a estrutura.

def handle_ping(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"message": "pong", "echo": payload}

def handle_system_status(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "ok", "uptime_seconds": 1234}

def handle_temperature_stats(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Payload esperado (um dos campos de imagem é obrigatório):
      {
        "image_id": "abc123",              # ID no Postgres (opção A)
        "image_base64": "<...>",           # Raw base64 ou data URI (opção B)
        "t_min": 98.0,
        "t_max": 550.0,
        "use_default_if_none": true        # opcional (fallback se não detectar ROI)
      }
    """
    image_id = payload.get("image_id")
    image_b64 = payload.get("image_base64")

    if not image_id and not image_b64:
        raise ValueError("Forneça 'image_id' ou 'image_base64' no payload.")

    # 1) Busca/decodifica a imagem
    if image_id:
        b64 = fetch_image_base64_by_id(str(image_id))
        if not b64:
            raise ValueError(f"Imagem não encontrada para image_id='{image_id}'.")
        img_rgb = base64_to_rgb_ndarray(b64)
    else:
        img_rgb = base64_to_rgb_ndarray(image_b64)

    # 2) Parâmetros térmicos
    t_min = float(payload.get("t_min", 98.0))
    t_max = float(payload.get("t_max", 550.0))
    if not np.isfinite(t_min) or not np.isfinite(t_max) or t_max <= t_min:
        raise ValueError("Parâmetros de temperatura inválidos (t_min/t_max).")

    # 3) Matriz de temperatura
    matriz = build_temperature_matrix_linear(img_rgb, t_min, t_max)

    # 4) ROI por detecção
    detector = ROIBoxDetector()
    bbox = detector.detect_bbox(img_rgb)

    # 5) Fallback opcional para ROI central
    use_default = bool(payload.get("use_default_if_none", True))
    if bbox is None:
        if not use_default:
            raise ValueError("Nenhuma ROI 'extraction_roi' detectada.")
        H, W = matriz.shape
        bbox = (int(W*0.35), int(H*0.35), int(W*0.65), int(H*0.65))
        fallback_used = True
    else:
        fallback_used = False

    # 6) Estatísticas
    stats = stats_from_bbox(matriz, bbox)

    return {
        "source": "image_id" if image_id else "image_base64",
        "image_id": image_id,
        "t_min_used": t_min,
        "t_max_used": t_max,
        "roi_bbox": [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
        "fallback_used": fallback_used,
        "stats": stats
    }

def dispatch_command(cmd_type: CommandType, payload: Dict[str, Any]) -> Dict[str, Any]:
    if cmd_type == CommandType.PING:
        return handle_ping(payload)
    if cmd_type == CommandType.GET_SYSTEM_STATUS:
        return handle_system_status(payload)
    if cmd_type == CommandType.GET_TEMPERATURE_STATS:
        return handle_temperature_stats(payload)
    if cmd_type == CommandType.GET_ANGLES:
        return analyze_angles(payload)
    raise ValueError(f"Unsupported command: {cmd_type}")