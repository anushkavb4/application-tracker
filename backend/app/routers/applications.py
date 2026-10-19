from datetime import date, datetime, time, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application_filters import unattributed_condition
from app.db import get_db
from app.deps import require_api_key
from app.models import Application
from app.schemas import ApplicationListOut, ApplicationOut

router = APIRouter(prefix="/api/applications", tags=["applications"], dependencies=[Depends(require_api_key)])

_SORT_COLUMNS = {
    "first_seen_at": Application.first_seen_at,
    "last_seen_at": Application.last_seen_at,
    "status": Application.status,
    "company": Application.company_name,
    "role": Application.role,
    "confidence": Application.confidence,
}


def _apply_filters(
    statement: Select,
    status_filter: str | None,
    ats: str | None,
    company: str | None,
    query: str | None,
    date_from: date | None,
    date_to: date | None,
    unattributed: bool = False,
) -> Select:
    if status_filter:
        statement = statement.where(Application.status == status_filter)
    if ats:
        statement = statement.where(Application.ats.ilike(f"%{ats}%"))
    if company:
        statement = statement.where(Application.company_name.ilike(f"%{company}%"))
    if query:
        search = f"%{query}%"
        statement = statement.where(
            or_(
                Application.company_name.ilike(search),
                Application.role.ilike(search),
                Application.url.ilike(search),
            )
        )
    if date_from:
        statement = statement.where(
            Application.first_seen_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        )
    if date_to:
        statement = statement.where(
            Application.first_seen_at < datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        )
    if unattributed:
        statement = statement.where(unattributed_condition())
    return statement


@router.get("", response_model=ApplicationListOut)
async def list_applications(
    status_filter: str | None = Query(default=None, alias="status"),
    ats: str | None = None,
    company: str | None = None,
    q: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    unattributed: bool = False,
    sort: str = Query(default="last_seen_at"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> ApplicationListOut:
    if sort not in _SORT_COLUMNS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sort field")

    filtered = _apply_filters(
        select(Application), status_filter, ats, company, q, date_from, date_to, unattributed
    )
    total = await session.scalar(select(func.count()).select_from(filtered.subquery()))
    sort_column = _SORT_COLUMNS[sort]
    sort_expression = asc(sort_column) if order == "asc" else desc(sort_column)
    rows = await session.scalars(
        filtered.order_by(sort_expression, Application.id).offset((page - 1) * page_size).limit(page_size)
    )

    return ApplicationListOut(
        items=list(rows),
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{application_id}", response_model=ApplicationOut)
async def get_application(
    application_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Application:
    application = await session.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application
