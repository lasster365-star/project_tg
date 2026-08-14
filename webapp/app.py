"""
FastAPI-приложение: API + статика Mini App (twa/).
Запуск:  python -m webapp.app
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from shared.config import config  # noqa: E402
from shared.db import init_db  # noqa: E402
from webapp.routers.api import (  # noqa: E402
    admin as admin_router,
    public as public_router,
    router as api_router,
)
from webapp.routers.debug import router as debug_router  # noqa: E402


logging.basicConfig(
    level=logging.INFO if not config.debug else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("webapp")


TWA_DIR = PROJECT_ROOT / "twa"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    log.info("Starting up: DB init…")
    await init_db()
    log.info("DB initialized")
    try:
        yield
    finally:
        log.info("Shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Telegram Shop Mini App",
        version="1.3.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=_lifespan,
    )

    @app.exception_handler(Exception)
    async def _json_error(request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )
        return JSONResponse(
            status_code=500, content={"error": "internal", "detail": str(exc)}
        )

    app.include_router(api_router)
    app.include_router(public_router)
    app.include_router(admin_router)
    app.include_router(debug_router)

    @app.get("/manifest.webmanifest", include_in_schema=False)
    async def manifest() -> FileResponse:
        return FileResponse(TWA_DIR / "manifest.webmanifest")

    @app.get("/telegram-web-app.js", include_in_schema=False)
    async def telegram_js() -> FileResponse:
        return FileResponse(
            TWA_DIR / "telegram-web-app.js",
            media_type="application/javascript",
        )

    @app.get("/admin", include_in_schema=False)
    async def admin_page() -> FileResponse:
        return FileResponse(TWA_DIR / "admin.html")

    app.mount("/", StaticFiles(directory=str(TWA_DIR), html=True), name="twa")

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
