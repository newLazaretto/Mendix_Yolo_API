from typing import Dict, Any, List, Tuple, Optional
import math
import numpy as np
import cv2
from ultralytics import YOLO
from app.core.config import settings

_angle_model: Optional[YOLO] = None

def _get_angle_model() -> YOLO:
    global _angle_model
    if _angle_model is None:
        _angle_model = YOLO(settings.ANGLE_MODEL_PATH)
    return _angle_model

def _rgb_to_bgr(img_rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

def _angle_deg_from_points(head_xy: np.ndarray, tail_xy: np.ndarray) -> float:
    dx = float(tail_xy[0] - head_xy[0])
    dy = float(tail_xy[1] - head_xy[1])
    ang = math.degrees(math.atan2(dy, dx))
    return abs(ang)

def _percent_from_angle(angle_deg: float) -> float:
    """
    90° -> 0%
    0° ou 180° -> 100%
    mapeamento robusto: 100 * cos^2(theta)
    """
    rad = math.radians(angle_deg)
    pct = 100.0 * (math.cos(rad) ** 2)
    if pct < 0: pct = 0.0
    if pct > 100: pct = 100.0
    return float(pct)

def valves_from_image_rgb(img_rgb: np.ndarray) -> List[float]:
    """
    Retorna até 3 valores de válvula (0..100). Ordena por confiança desc.
    Se houver <3 detecções, completa com None.
    """
    model = _get_angle_model()
    img_bgr = _rgb_to_bgr(img_rgb)
    res = model(img_bgr)
    if not res or res[0].keypoints is None:
        return []

    r0 = res[0]
    kpts = r0.keypoints
    conf = None
    if hasattr(r0, "boxes") and r0.boxes is not None and r0.boxes.conf is not None:
        conf = r0.boxes.conf.detach().cpu().numpy()
    data = kpts.data
    if hasattr(data, "cpu"):
        data = data.cpu().numpy()
    data = np.asarray(data)

    vals: List[Tuple[float, float]] = [] 
    for i, inst in enumerate(data):
        pts = inst
        if pts.ndim == 1:
            if pts.size % 2 != 0:
                continue
            pts = pts.reshape(-1, 2)
        if pts.shape[0] < 2 or pts.shape[1] < 2:
            continue
        head = pts[0][:2]
        tail = pts[1][:2]
        ang = _angle_deg_from_points(head, tail)
        pct = _percent_from_angle(ang)
        c = float(conf[i]) if conf is not None and i < len(conf) else 1.0
        vals.append((c, pct))

    if not vals:
        return []

    vals.sort(key=lambda x: x[0], reverse=True)
    out = [v for _, v in vals[:3]]
    return out
