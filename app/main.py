# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.router import router as api_router

setup_logging()
app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

app.include_router(api_router, prefix="/api")

@app.get("/", include_in_schema=False)
async def root():
    return {"docs": "/docs", "redoc": "/redoc"}

if __name__ == "__main__":
    import os, sys, pathlib, uvicorn
    # garante que o diretório raiz (que contém 'app/') está no sys.path
    ROOT = pathlib.Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    use_reload = os.getenv("APP_RELOAD", "1") == "1"

    if use_reload:
        # precisa de string "app.main:app" para o reloader funcionar
        uvicorn.run("app.main:app", host=host, port=port, reload=True)
    else:
        # sem reload, pode passar o objeto diretamente
        uvicorn.run(app, host=host, port=port)
