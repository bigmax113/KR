from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    setup_logging(logging.INFO)
    app = FastAPI(title=settings.APP_NAME)

    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    # For this MVP we don't rely on cookies/auth; keeping allow_credentials=False
    # makes CORS behavior simpler (esp. when the tester page is served locally).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Optional: serve a simple UI from the same origin to avoid CORS altogether.
    # If /static/index.html exists, we serve it at GET /.
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    static_dir = os.path.abspath(static_dir)
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/", include_in_schema=False)
        def root():
            if os.path.isfile(index_path):
                return FileResponse(index_path)
            return {"service": settings.APP_NAME, "status": "ok"}

    app.include_router(router)
    return app


app = create_app()
