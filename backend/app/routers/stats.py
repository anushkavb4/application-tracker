from datetime import datetime
from typing import cast

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application_filters import unattributed_condition
from app.db import get_db
from app.deps import require_api_key
from app.models import Application
from app.schemas import StatsSummaryOut

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(require_api_key)])


@router.get("/summary", response_model=StatsSummaryOut)
async def summary(session: AsyncSession = Depends(get_db)) -> StatsSummaryOut:
    total = int(await session.scalar(select(func.count(Application.id))) or 0)
    unattributed_count = int(
        await session.scalar(
            select(func.count(Application.id)).where(unattributed_condition())
        )
        or 0
    )
    grouped = await session.execute(
        select(Application.status, func.count(Application.id)).group_by(Application.status)
    )
    status_counts = {status: count for status, count in grouped.all()}
    applied_count = sum(
        count for status, count in status_counts.items() if status in {"applied", "screening", "interview", "offer"}
    )
    response_count = sum(
        count for status, count in status_counts.items() if status in {"screening", "interview", "offer"}
    )

    over_time = await session.execute(
        select(
            func.date_trunc("day", Application.first_seen_at).label("day"),
            func.count(Application.id).label("count"),
        )
        .group_by("day")
        .order_by("day")
    )
    applications_over_time = [
        {"date": cast(datetime, day).date().isoformat(), "count": count}
        for day, count in over_time.all()
    ]

    return StatsSummaryOut(
        total=total,
        unattributed_count=unattributed_count,
        status_counts=status_counts,
        applied_count=applied_count,
        response_count=response_count,
        response_rate=(response_count / applied_count if applied_count else 0.0),
        applications_over_time=applications_over_time,
    )
