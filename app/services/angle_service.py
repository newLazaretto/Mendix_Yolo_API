from typing import Dict, Any, List, Tuple
import math
import numpy as np
import cv2
from ultralytics import YOLO
from app.services.image_utils import base64_to_rgb_ndarray, bgr_to_base64_png
from app.core.config import settings

# Carrega o modelo uma vez (singleton de módulo)
_angle_model = None

def _get_angle_model() -> YOLO:
    global _angle_model
    if _angle_model is None:
        _angle_model = YOLO(settings.ANGLE_MODEL_PATH)
    return _angle_model

def _rgb_to_bgr(img_rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

def _compute_angle_deg(head: np.ndarray, tail: np.ndarray) -> float:
    """
    Calcula ângulo absoluto em graus do vetor head->tail.
    head/tail: [x, y] em pixels.
    """
    dx = float(tail[0] - head[0])
    dy = float(tail[1] - head[1])
    angle_rad = math.atan2(dy, dx)  # -pi..pi (0° = eixo +x)
    angle_deg = abs(math.degrees(angle_rad))
    return angle_deg

def _quadrant(dx: float, dy: float) -> str:
    if dx >= 0 and dy < 0:   return "Q1"
    if dx < 0 and dy < 0:    return "Q2"
    if dx < 0 and dy >= 0:   return "Q3"
    return "Q4"

def _annotate(img_bgr: np.ndarray, pairs: List[Tuple[np.ndarray, np.ndarray, float]]) -> np.ndarray:
    """
    Desenha linha head->tail e rótulo do ângulo.
    pairs: lista de (head, tail, angle_deg)
    """
    out = img_bgr.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    for (head, tail, angle_deg) in pairs:
        h = (int(head[0]), int(head[1]))
        t = (int(tail[0]), int(tail[1]))
        # linha e pontos
        cv2.circle(out, h, 5, (0, 255, 255), -1)
        cv2.circle(out, t, 5, (0, 255, 0), -1)
        cv2.line(out, h, t, (0, 200, 0), 2)
        # label
        tx = int((h[0] + t[0]) / 2)
        ty = int((h[1] + t[1]) / 2)
        label = f"{angle_deg:.2f}G"
        cv2.putText(out, label, (tx, ty), font, 0.9, (0, 255, 255), 2, cv2.LINE_AA)
    return out

def analyze_angles(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Payload esperado:
      {
        "image_id": "abc123",         # OU
        "image_base64": "data:image/..;base64,...",
        "return_overlay": true/false  # opcional (sobrepõe settings.RETURN_OVERLAY_BASE64)
      }

    Retorno:
      {
        "detections": [
          {
            "index": 0,
            "angle_deg": 12.34,
            "head": [x, y],
            "tail": [x, y],
            "length_px": 123.4,
            "radians": 0.21,
            "direction": "Q1|Q2|Q3|Q4"
          }, ...
        ],
        "count": n,
        "overlay_base64": "data:image/png;base64,..."  # se solicitado
      }
    """
    image_id = payload.get("image_id")
    image_b64 = payload.get("image_base64")
    want_overlay = payload.get("return_overlay", settings.RETURN_OVERLAY_BASE64)

    if not image_id and not image_b64:
        raise ValueError("Forneça 'image_id' ou 'image_base64'.")

    # 1) Obtenção e decodificação da imagem (RGB)
    if image_id:
        b64 = fetch_image_base64_by_id(str(image_id))
        if not b64:
            raise ValueError(f"Imagem não encontrada para image_id='{image_id}'.")
        img_rgb = base64_to_rgb_ndarray(b64)
    else:
        img_rgb = base64_to_rgb_ndarray(str(image_b64))

    # 2) Modelo + inferência
    model = _get_angle_model()
    # O modelo foi treinado em BGR no seu exemplo, mas ultralytics aceita np.ndarray BGR ou RGB.
    # Para manter compatibilidade com seu script original, convertemos para BGR aqui:
    img_bgr = _rgb_to_bgr(img_rgb)
    results = model(img_bgr)
    if not results or results[0].keypoints is None:
        return {"detections": [], "count": 0, "overlay_base64": None if want_overlay else None}

    kpts = results[0].keypoints.data
    if hasattr(kpts, "cpu"):
        kpts = kpts.cpu().numpy()
    else:
        kpts = np.asarray(kpts)

    # 3) Interpretação: esperamos 2 keypoints por instância (head, tail)
    detections = []
    overlay_pairs = []
    for idx, inst in enumerate(kpts):
        # Suporta também (N, num_kpts, 2) ou (num_kpts, 2). Vamos normalizar:
        points = inst
        if points.ndim == 1:  # ex.: (6,) -> reshape (3,2)
            if points.size % 2 != 0:
                continue
            points = points.reshape(-1, 2)
        # se houver confiança z adicional, pegue apenas x,y
        if points.shape[1] >= 2:
            head = points[0][:2]
            tail = points[1][:2]
        else:
            continue

        dx = float(tail[0] - head[0])
        dy = float(tail[1] - head[1])
        angle_rad = math.atan2(dy, dx)
        angle_deg = abs(math.degrees(angle_rad))
        length = float(np.hypot(dx, dy))
        dir_quadrant = _quadrant(dx, dy)

        detections.append({
            "index": int(idx),
            "angle_deg": float(angle_deg),
            "head": [float(head[0]), float(head[1])],
            "tail": [float(tail[0]), float(tail[1])],
            "length_px": length,
            "radians": float(angle_rad),
            "direction": dir_quadrant
        })
        overlay_pairs.append((head, tail, angle_deg))

    # 4) Overlay (opcional)
    overlay_b64 = None
    if want_overlay and len(overlay_pairs) > 0:
        # Se quiser usar a renderização do ultralytics:
        #   img_vis = results[0].plot()  # retorna BGR com todas as anotações do modelo
        # Aqui usamos nossa anotação (limpa, só head->tail + ângulo):
        img_annot = _annotate(img_bgr, overlay_pairs)
        overlay_b64 = bgr_to_base64_png(img_annot)

    return {"detections": detections, "count": len(detections), "overlay_base64": overlay_b64}
