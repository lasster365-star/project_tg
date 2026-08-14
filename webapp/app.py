"""
FastAPI-приложение: API + статика Mini App (twa/).
Запуск:  python -m webapp.app
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.requests import Request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from shared.config import config  # noqa: E402
from shared.db import init_db  # noqa: E402
from webapp.routers.api import router as api_router  # noqa: E402


logging.basicConfig(
    level=logging.INFO if not config.debug else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("site")


TWA_DIR = PROJECT_ROOT / "twa"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Telegram Shop Mini App",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    @app.on_event("startup")
    async def _startup() -> None:
        await init_db()
        log.info("DB initialized")

    # API
    app.include_router(api_router)

    # Mini App статика — корень /, StaticFiles ниже не пересекается
    app.mount("/", StaticFiles(directory=str(TWA_DIR), html=True), name="twa")

    @app.get("/api/health", include_in_schema=False)
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/manifest.webmanifest", include_in_schema=False)
    async def manifest() -> FileResponse:
        return FileResponse(TWA_DIR / "manifest.webmanifest")

    @app.get("/telegram-web-app.js", include_in_schema=False)
    async def telegram_js() -> FileResponse:
        # Telegram автоматически подгружает этот скрипт в Mini App.
        return FileResponse(TWA_DIR / "telegram-web-app.js", media_type="application/javascript")

    @app.exception_handler(Exception)
    async def _json_error(request: Request, exc: Exception):
        # Чтобы клиент получал JSON, а не HTML 500
        return JSONResponse(
            status_code=500, content={"error": "internal", "detail": str(exc)}
        )
    return app


app = create_app()


async def main() -> None:
    log.info("Starting API on %s:%s", config.api_host, config.api_port)
    cfg = uvicorn.Config(
        "webapp.app:app",
        host=config.api_host,
        port=config.api_port,
        log_level="info",
        access_log=False,
        proxy_headers=True,
    )
    server = uvicorn.Server(cfg)

    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def _stop(*_a):
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass

    runner = asyncio.create_task(server.serve())
    await stop_event.wait()
    server.should_exit = True
    await runner


if __name__ == "__main__":
    asyncio.run(main())
