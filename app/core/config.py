from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]

ASSETS_DIR = APP_DIR / "assets"


class Settings(BaseSettings):
    APP_NAME: str = "Mendix Command API"
    API_V1_PREFIX: str = "/api/v1"
    API_KEY: str = "123"

    EXTERNAL_SOURCE_URL: str = "http://localhost:9000/source"   # GET

    SINK_BASE_URL: str = "http://localhost:9000/"               # <--- BASE
    SINK_POST_THERMAL_PATH: str = "rest/postthermaldata/v1/Data"  # <--- SERVIÇO

    TEMP_AGGREGATION: str = "mean"

    MAX_TEMPERATURE_VECTOR_LEN: int = 15000
    SINK_BATCH_SIZE: int = 26


    SIDE_MAP: Dict[str, str] = {"LEFT": "LEFT", "RIGHT": "RIGHT"}
    DEFAULT_EQUIPMENT: str = "Forno"
    SINK_TEMPERATURE_FIELD_NAME: str = "Temperature"

    ROI_CLASS_NAME: str = "extraction_roi"
    INFER_SIZE_W: int = 224
    INFER_SIZE_H: int = 224

    TEMP_MIN_DEFAULT: float = 98.0
    TEMP_MAX_DEFAULT: float = 550.0

    PROCESS_NON_THERMAL: bool = False

    ROI_MODEL_PATH: str = str(ASSETS_DIR / "vivix_model.pt")
    ANGLE_MODEL_PATH: str = str(ASSETS_DIR / "angle_model.pt")

    RETURN_OVERLAY_BASE64: bool = True
    DEBUG: bool = True

    CORS_ALLOW_ORIGINS: List[str] = ["http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
