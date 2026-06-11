from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings
from app.db.session import ensure_database_schema

FRONTEND_DIR = Path(__file__).parent / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.include_router(router, prefix="/api")
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

    @app.on_event("startup")
    async def startup() -> None:
        if not settings.booking_persistence_enabled and settings.session_checkpoint_backend != "postgres":
            return
        try:
            await ensure_database_schema()
        except Exception:
            return

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(
            FRONTEND_DIR / "index.html",
            headers={"Cache-Control": "no-store"},
        )

    return app


app = create_app()
