import numpy as np, cv2
from ultralytics import YOLO
from app.core.config import settings

class ROIBoxDetector:
    def __init__(self, model_path: str | None = None, class_name: str | None = None, size_w: int | None = None, size_h: int | None = None):
        self.model = YOLO(model_path or settings.ROI_MODEL_PATH)
        self.class_name = class_name or settings.ROI_CLASS_NAME
        self.tw = int(size_w or settings.INFER_SIZE_W)
        self.th = int(size_h or settings.INFER_SIZE_H)

    def detect_bbox(self, img_rgb):
        H, W = img_rgb.shape[:2]
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        resized = cv2.resize(img_bgr, (self.tw, self.th), interpolation=cv2.INTER_AREA)

        r0 = self.model(resized)[0]
        if r0.masks is None:
            return None

        names = r0.names
        xs, ys = [], []
        for i, poly in enumerate(r0.masks.xy):
            cls_id = int(r0.boxes.cls[i].item())
            if names.get(cls_id) == self.class_name:
                p = np.round(poly).astype(np.int32)
                xs.append(p[:, 0]); ys.append(p[:, 1])

        if not xs:
            return None

        sx, sy = W / float(self.tw), H / float(self.th)
        xs = np.concatenate(xs) * sx
        ys = np.concatenate(ys) * sy

        x_lo = int(np.clip(np.floor(xs.min()), 0, W - 1))
        x_hi = int(np.clip(np.ceil(xs.max()), 0, W))
        y_lo = int(np.clip(np.floor(ys.min()), 0, H - 1))
        y_hi = int(np.clip(np.ceil(ys.max()), 0, H))

        if x_hi <= x_lo or y_hi <= y_lo:
            return None
        return (x_lo, y_lo, x_hi, y_hi)
