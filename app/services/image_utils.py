# app/services/image_utils.py
import base64, re, cv2, numpy as np

_DATA_URL_RE = re.compile(r'^data:.*;base64,', re.IGNORECASE)

def base64_to_rgb_ndarray(b64: str) -> np.ndarray:
    # remove prefixo data URL se houver
    raw = _DATA_URL_RE.sub('', b64.strip())
    buf = base64.b64decode(raw)
    arr = np.frombuffer(buf, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Falha ao decodificar base64 para imagem.")
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def bgr_to_base64_png(img_bgr: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img_bgr)
    if not ok:
        raise ValueError("Falha ao codificar PNG.")
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("utf-8")


