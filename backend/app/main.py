from fastapi import FastAPI
from sqlalchemy import text

from app.config import settings
from app.db import engine

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/health/db", tags=["health"])
async def database_health() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
