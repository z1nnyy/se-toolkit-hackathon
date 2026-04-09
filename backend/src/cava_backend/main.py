from __future__ import annotations

import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from cava_backend.database import init_database
from cava_backend.routers import auth, menu
from cava_backend.services.seeder import backfill_menu_translations, seed_demo_menu
from cava_backend.services.user_seeder import ensure_default_super_admin
from cava_backend.settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_database()
    await ensure_default_super_admin()
    if settings.seed_demo_data:
        await seed_demo_menu()
    await backfill_menu_translations()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    description="API for the Cava cafe Telegram bot and admin panel.",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    traceback_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback_lines[-3:],
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(menu.router, prefix="/menu", tags=["menu"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])

assets_dir = Path(__file__).resolve().parents[2] / "assets"
app.mount("/menu-assets", StaticFiles(directory=assets_dir), name="menu-assets")
frontend_dist_dir = Path(__file__).resolve().parents[3] / "frontend" / "dist"


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "cava-backend"}


if frontend_dist_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dist_dir, html=True), name="frontend")
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": "cava-backend",
            "status": "ok",
            "docs": "/docs",
            "menu_items": "/menu/items",
            "frontend_hint": "Run the Vite admin panel on http://localhost:5173",
        }
