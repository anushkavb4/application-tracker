import csv
import io
import json
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_api_key
from app.models import Application
from app.routers.applications import _apply_filters

router = APIRouter(prefix="/api/export", tags=["exports"], dependencies=[Depends(require_api_key)])


def _serialize(application: Application) -> dict[str, object]:
    return {
        "id": str(application.id),
        "dedup_key": application.dedup_key,
        "company_name": application.company_name,
        "role": application.role,
        "ats": application.ats,
        "external_id": application.external_id,
        "url": application.url,
        "status": application.status,
        "status_source": application.status_source,
        "confidence": application.confidence,
        "first_seen_at": application.first_seen_at.isoformat(),
        "last_seen_at": application.last_seen_at.isoformat(),
        "applied_at": application.applied_at.isoformat() if application.applied_at else None,
        "notes": application.notes,
    }


async def _get_applications(
    session: AsyncSession,
    status_filter: str | None,
    ats: str | None,
    company: str | None,
    date_from: date | None,
    date_to: date | None,
) -> list[Application]:
    statement = _apply_filters(
        select(Application), status_filter, ats, company, None, date_from, date_to
    ).order_by(Application.first_seen_at)
    return list(await session.scalars(statement))


@router.get("/applications.json")
async def export_json(
    status_filter: str | None = Query(default=None, alias="status"),
    ats: str | None = None,
    company: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    applications = await _get_applications(session, status_filter, ats, company, date_from, date_to)
    return [_serialize(application) for application in applications]


@router.get("/applications.jsonl", response_class=PlainTextResponse)
async def export_jsonl(
    status_filter: str | None = Query(default=None, alias="status"),
    ats: str | None = None,
    company: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_db),
) -> str:
    applications = await _get_applications(session, status_filter, ats, company, date_from, date_to)
    return "".join(json.dumps(_serialize(application)) + "\n" for application in applications)


@router.get("/applications.csv")
async def export_csv(
    status_filter: str | None = Query(default=None, alias="status"),
    ats: str | None = None,
    company: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    applications = await _get_applications(session, status_filter, ats, company, date_from, date_to)
    rows = [_serialize(application) for application in applications]
    buffer = io.StringIO()
    fieldnames = [
        "id", "dedup_key", "company_name", "role", "ats", "external_id", "url",
        "status", "status_source", "confidence", "first_seen_at", "last_seen_at", "applied_at", "notes",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications.csv"},
    )
