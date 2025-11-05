# app/services/temperature.py
from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import cv2

# (opcional) tenta ler path do settings se existir
try:
    from app.core.config import settings
except Exception:
    settings = None  # sem dependência dura

# ==== CONFIG PADRÃO ====
DEFAULT_CLASS_NAME = "extraction_roi"
DEFAULT_INFER_SIZE = (224, 224)  # (width, height)
# Caminho do modelo: prioridade settings -> caminhos relativos comuns -> string simples
_DEF_MODEL_CANDIDATES = []

if settings and getattr(settings, "ROI_MODEL_PATH", None):
    _DEF_MODEL_CANDIDATES.append(Path(str(settings.ROI_MODEL_PATH)))

# tenta app/assets/vivix_model.pt
_THIS = Path(__file__).resolve()
_APP_DIR = _THIS.parents[1] if len(_THIS.parents) >= 2 else _THIS.parent
_DEF_MODEL_CANDIDATES.append(_APP_DIR / "assets" / "vivix_model.pt")
# tenta app/api/assets/vivix_model.pt (caso você tenha mantido lá)
_DEF_MODEL_CANDIDATES.append(_APP_DIR / "api" / "assets" / "vivix_model.pt")
# fallback string crua (vai depender do cwd)
_DEF_MODEL_CANDIDATES.append(Path("assets/vivix_model.pt"))

def _resolve_default_model_path() -> str:
    for cand in _DEF_MODEL_CANDIDATES:
        try:
            if Path(cand).exists():
                return str(Path(cand))
        except Exception:
            pass
    # último recurso: retorna o último candidato como string mesmo
    return str(_DEF_MODEL_CANDIDATES[-1])

# ==== MODELO (cache) ====
_ROI_MODEL_CACHE: dict[str, "YOLO"] = {}

def _get_yolo(model_path: str):
    from ultralytics import YOLO
    mp = str(Path(model_path))
    mdl = _ROI_MODEL_CACHE.get(mp)
    if mdl is None:
        mdl = YOLO(mp)
        _ROI_MODEL_CACHE[mp] = mdl
    return mdl

# ==== TEMPERATURA (como já tinha) ====
def build_temperature_matrix_linear(img_rgb: np.ndarray, t_min: float, t_max: float) -> np.ndarray:
    g = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    norm = cv2.normalize(g, None, 0.0, 1.0, cv2.NORM_MINMAX)
    return t_min + norm * (t_max - t_min)

def stats_from_bbox(matriz: np.ndarray, bbox: tuple[int, int, int, int]) -> dict:
    """
    bbox no formato (x_lo, y_lo, x_hi, y_hi) com x_hi/y_hi EXCLUSIVOS.
    """
    x_lo, y_lo, x_hi, y_hi = bbox
    roi = matriz[y_lo:y_hi, x_lo:x_hi]
    if roi.size == 0:
        raise ValueError("ROI vazia")
    return {
        "min": float(np.min(roi)),
        "max": float(np.max(roi)),
        "mean": float(np.mean(roi)),
        "std": float(np.std(roi)),
        "width": int(x_hi - x_lo),
        "height": int(y_hi - y_lo),
    }

# ==== ROI automática via YOLO ====
def detect_roi_bbox(
    img_rgb: np.ndarray,
    *,
    model_path: str | None = None,
    class_name: str = DEFAULT_CLASS_NAME,
    infer_size: tuple[int, int] = DEFAULT_INFER_SIZE,
) -> tuple[int, int, int, int] | None:
    """
    Retorna bbox da ROI no formato (x_lo, y_lo, x_hi, y_hi) com limites superiores EXCLUSIVOS,
    já no tamanho original da imagem. Se nada for detectado, retorna None.
    """
    H, W = img_rgb.shape[:2]
    tw, th = int(infer_size[0]), int(infer_size[1])

    model_path = model_path or _resolve_default_model_path()
    model = _get_yolo(model_path)

    # YOLO aceita RGB, mas para compat com seu pipeline convertemos para BGR
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    resized = cv2.resize(img_bgr, (tw, th), interpolation=cv2.INTER_AREA)

    results = model(resized)
    r0 = results[0]
    if r0.masks is None:
        return None

    names = r0.names  # dict id->name
    xs, ys = [], []
    for i, poly in enumerate(r0.masks.xy):
        cls_id = int(r0.boxes.cls[i].item())
        cls_name = names.get(cls_id, str(cls_id))
        if cls_name == class_name:
            p = np.round(poly).astype(np.int32)
            xs.append(p[:, 0])
            ys.append(p[:, 1])

    if not xs:
        return None

    # Reescala para o tamanho original
    sx, sy = W / float(tw), H / float(th)
    xs = np.concatenate(xs) * sx
    ys = np.concatenate(ys) * sy

    # Convensão EXCLUSIVA no limite superior (compatível com slicing)
    x_lo = int(np.clip(np.floor(xs.min()), 0, max(W - 1, 0)))
    y_lo = int(np.clip(np.floor(ys.min()), 0, max(H - 1, 0)))
    x_hi = int(np.clip(np.ceil(xs.max()), 1, W))
    y_hi = int(np.clip(np.ceil(ys.max()), 1, H))

    if x_hi <= x_lo or y_hi <= y_lo:
        return None
    return (x_lo, y_lo, x_hi, y_hi)

def _default_center_bbox(shape_hw: tuple[int, int]) -> tuple[int, int, int, int]:
    """
    ROI central (~30%–65% como no seu script). Retorna (x_lo, y_lo, x_hi, y_hi) EXCLUSIVOS.
    """
    H, W = shape_hw
    x_lo, x_hi = int(W * 0.35), int(W * 0.65)
    y_lo, y_hi = int(H * 0.35), int(H * 0.65)
    # clamp e garante ordem
    x_lo = max(0, min(x_lo, W - 1))
    y_lo = max(0, min(y_lo, H - 1))
    x_hi = max(1, min(x_hi, W))
    y_hi = max(1, min(y_hi, H))
    if x_hi <= x_lo + 1:  # largura mínima 1 px
        x_hi = min(W, x_lo + 1)
    if y_hi <= y_lo + 1:
        y_hi = min(H, y_lo + 1)
    return (x_lo, y_lo, x_hi, y_hi)

# ==== Funções "prontas" para API / serviços ====
def to_temperature_vector(img_rgb: np.ndarray, t_min: float, t_max: float, max_len: int | None = None) -> list[float]:
    """
    Vetor da imagem inteira (sem ROI). Mantida para compatibilidade.
    """
    matriz = build_temperature_matrix_linear(img_rgb, t_min, t_max)
    vec = matriz.ravel().astype(float)
    if max_len and vec.size > max_len:
        stride = int(np.ceil(vec.size / max_len))
        vec = vec[::stride]
    return vec.tolist()

def to_temperature_vector_roi(
    img_rgb: np.ndarray,
    t_min: float,
    t_max: float,
    *,
    model_path: str | None = None,
    class_name: str = DEFAULT_CLASS_NAME,
    infer_size: tuple[int, int] = DEFAULT_INFER_SIZE,
    use_default_if_none: bool = True,
    max_len: int | None = None,
) -> dict:
    """
    Constrói matriz de temperatura e retorna VETOR apenas da ROI detectada.
    Saída:
      {
        "vector": [ ...temperaturas... ],
        "bbox": [x_lo, y_lo, x_hi, y_hi],  # EXCLUSIVO no topo/direita
        "stats": {min, max, mean, std, width, height},
        "fallback_used": bool
      }
    """
    matriz = build_temperature_matrix_linear(img_rgb, t_min, t_max)
    bbox = detect_roi_bbox(
        img_rgb,
        model_path=model_path,
        class_name=class_name,
        infer_size=infer_size,
    )
    fallback_used = False
    if bbox is None:
        if not use_default_if_none:
            raise ValueError("Nenhuma ROI detectada e fallback desabilitado.")
        bbox = _default_center_bbox(matriz.shape)
        fallback_used = True

    x_lo, y_lo, x_hi, y_hi = bbox
    roi = matriz[y_lo:y_hi, x_lo:x_hi]
    if roi.size == 0:
        raise ValueError("ROI vazia após clamp.")

    vec = roi.ravel().astype(float)
    if max_len and vec.size > max_len:
        stride = int(np.ceil(vec.size / max_len))
        vec = vec[::stride]

    return {
        "vector": vec.tolist(),
        "bbox": [int(x_lo), int(y_lo), int(x_hi), int(y_hi)],
        "stats": stats_from_bbox(matriz, bbox),
        "fallback_used": fallback_used,
    }
