from datetime import date, datetime, time, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application_filters import unattributed_condition
from app.db import get_db
from app.deps import require_api_key
from app.models import Application, ApplicationEvent, ManualOverride
from app.schemas import ApplicationListOut, ApplicationOut, ApplicationPatchIn

router = APIRouter(prefix="/api/applications", tags=["applications"], dependencies=[Depends(require_api_key)])

_SORT_COLUMNS = {
    "first_seen_at": Application.first_seen_at,
    "last_seen_at": Application.last_seen_at,
    "status": Application.status,
    "company": Application.company_name,
    "role": Application.role,
    "confidence": Application.confidence,
}
_MANUAL_FIELDS = ("company_name", "role", "status", "notes")


def _manual_field_names(override: ManualOverride | None) -> list[str]:
    if override is None:
        return []
    return [field for field in _MANUAL_FIELDS if getattr(override, field) is not None]


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
    rows = list(await session.scalars(
        filtered.order_by(sort_expression, Application.id).offset((page - 1) * page_size).limit(page_size)
    ))
    overrides: list[ManualOverride] = (
        list(
            await session.scalars(
                select(ManualOverride).where(
                    ManualOverride.dedup_key.in_([application.dedup_key for application in rows])
                )
            )
        )
        if rows
        else []
    )
    fields_by_key = {override.dedup_key: _manual_field_names(override) for override in overrides}

    return ApplicationListOut(
        items=[
            ApplicationOut.model_validate(application).model_copy(
                update={"manual_fields": fields_by_key.get(application.dedup_key, [])}
            )
            for application in rows
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.patch("/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: UUID,
    patch: ApplicationPatchIn,
    session: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    application = await session.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    changes = {
        field: value
        for field, value in patch.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if not changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No changes provided")

    override = await session.scalar(
        select(ManualOverride).where(ManualOverride.dedup_key == application.dedup_key)
    )
    if override is None:
        override = ManualOverride(dedup_key=application.dedup_key)
        session.add(override)

    previous_status = application.status
    for field, value in changes.items():
        setattr(application, field, value)
        setattr(override, field, value)

    if "company_name" in changes:
        application.company_id = None
    if "status" in changes:
        application.status_source = "manual"
        if application.status == "applied" and application.applied_at is None:
            application.applied_at = datetime.now(timezone.utc)
        if application.status != previous_status:
            session.add(
                ApplicationEvent(
                    application_id=application.id,
                    status=application.status,
                    confidence=application.confidence,
                    source="manual",
                    occurred_at=datetime.now(timezone.utc),
                )
            )

    await session.commit()
    return ApplicationOut.model_validate(application).model_copy(
        update={"manual_fields": _manual_field_names(override)}
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
