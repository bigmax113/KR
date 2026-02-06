from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

def create_app() -> FastAPI:
    app = FastAPI(title="ai-recipes-backend")

    # CORS: для теста разрешаем всё.
    # Потом ограничишь до конкретных доменов (например, твой фронт на Render).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app

app = create_app()
