import base64, re, numpy as np, cv2

DATA_URI_RE = re.compile(r"^data:image/[^;]+;base64,")

def base64_to_rgb_ndarray(b64: str):
    if not b64:
        raise ValueError("Base64 vazio.")
    b64_clean = DATA_URI_RE.sub("", b64.strip())
    try:
        img_bytes = base64.b64decode(b64_clean, validate=True)
    except Exception as e:
        raise ValueError(f"Base64 inválido: {e}")
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Falha ao decodificar (cv2.imdecode=None).")
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

def bgr_to_base64_png(img_bgr: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img_bgr)
    if not ok:
        raise ValueError("Falha ao codificar PNG.")
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("utf-8")


