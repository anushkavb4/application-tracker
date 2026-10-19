import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal, engine
from app.processing import seed_patterns_if_empty
from app.routers.applications import router as applications_router
from app.routers.events import router as events_router
from app.routers.exports import router as exports_router
from app.routers.stats import router as stats_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with SessionLocal() as session:
        seeded = await seed_patterns_if_empty(session)
    if seeded:
        logger.info("Seeded %d starter URL patterns", seeded)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(events_router)
app.include_router(applications_router)
app.include_router(stats_router)
app.include_router(exports_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/health/db", tags=["health"])
async def database_health() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
