# mock_source_sink.py
from fastapi import FastAPI, Body, Query
from pydantic import BaseModel, AwareDatetime
from typing import List, Dict, Any, Optional
import uvicorn, json, os, threading

app = FastAPI(title="Mock Source+Sink")

# Carrega imagens mock de um JSON externo (veja etapa 3)
MOCK_JSON = os.environ.get("MOCK_IMAGES_JSON", "mock_images.json")
LAST_SINK_PAYLOAD: List[Dict[str, Any]] = []

class SourceImage(BaseModel):
    Side: str
    Port: int
    Section: int
    IsThermal: bool
    Name: str
    Base64String: str

class SourceResponse(BaseModel):
    Side: str
    Date: AwareDatetime
    Images: List[SourceImage]

@app.get("/source", response_model=SourceResponse)
def source(Date: AwareDatetime = Query(...), Side: str = Query(...)):
    """Devolve a lista de imagens com base64 que você configurou no mock_images.json"""
    if not os.path.exists(MOCK_JSON):
        # fallback: PNG 1x1 transparente
        tiny_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAOb+J8YAAAAASUVORK5CYII="
        images = [
            {"Side": Side, "Port": 1, "Section": 1, "IsThermal": True, "Name": "IMG1", "Base64String": f"data:image/png;base64,{tiny_png}"},
            {"Side": Side, "Port": 2, "Section": 2, "IsThermal": True, "Name": "IMG2", "Base64String": f"data:image/png;base64,{tiny_png}"},
        ]
    else:
        with open(MOCK_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        images = data.get("Images", [])
        # garante Side consistente
        for im in images:
            im.setdefault("Side", Side)
    return {"Side": Side, "Date": Date, "Images": images}

@app.post("/rest/postthermaldata/v1/Data")
def sink(items: List[Dict[str, Any]] = Body(...)):
    """Recebe sua lista final (o que sua API envia ao sink) e guarda para consulta."""
    global LAST_SINK_PAYLOAD
    LAST_SINK_PAYLOAD = items
    return {"ok": True, "count": len(items)}

@app.get("/sink/last")
def sink_last():
    """Consulta o último payload recebido pelo sink (para verificação)."""
    return LAST_SINK_PAYLOAD

if __name__ == "__main__":
    uvicorn.run("mock_source_sink:app", host="0.0.0.0", port=9000, reload=True)
