from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_api_key
from app.models import UrlPattern
from app.parsing.engine import PatternSpec, parse_job
from app.schemas import (
    PatternCreateIn,
    PatternOut,
    PatternPatchIn,
    PatternTestIn,
    PatternTestOut,
)

router = APIRouter(
    prefix="/api/admin/patterns",
    tags=["parser patterns"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=list[PatternOut])
async def list_patterns(session: AsyncSession = Depends(get_db)) -> list[UrlPattern]:
    return list(
        await session.scalars(
            select(UrlPattern).order_by(
                UrlPattern.priority, UrlPattern.created_at, UrlPattern.id
            )
        )
    )


@router.post("", response_model=PatternOut, status_code=status.HTTP_201_CREATED)
async def create_pattern(
    pattern: PatternCreateIn,
    session: AsyncSession = Depends(get_db),
) -> UrlPattern:
    record = UrlPattern(**pattern.model_dump())
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


@router.patch("/{pattern_id}", response_model=PatternOut)
async def update_pattern(
    pattern_id: UUID,
    patch: PatternPatchIn,
    session: AsyncSession = Depends(get_db),
) -> UrlPattern:
    record = await session.get(UrlPattern, pattern_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pattern not found")

    changes = patch.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No changes provided",
        )
    if any(
        value is None
        for name, value in changes.items()
        if name in {"ats", "kind", "url_regex", "priority", "enabled"}
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Pattern fields cannot be null",
        )

    for field, value in changes.items():
        setattr(record, field, value)
    await session.commit()
    await session.refresh(record)
    return record


@router.delete("/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pattern(
    pattern_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Response:
    record = await session.get(UrlPattern, pattern_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pattern not found")
    await session.delete(record)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test", response_model=PatternTestOut)
async def dry_run_pattern(candidate: PatternTestIn) -> PatternTestOut:
    pattern = PatternSpec(
        ats=candidate.pattern.ats,
        kind=candidate.pattern.kind,
        url_regex=candidate.pattern.url_regex,
        title_regex=candidate.pattern.title_regex,
        priority=candidate.pattern.priority,
        enabled=True,
    )
    parsed = parse_job(str(candidate.url), candidate.page_title, [pattern])
    return PatternTestOut(
        matched=parsed.ats is not None,
        ats=parsed.ats,
        company=parsed.company,
        role=parsed.role,
        external_id=parsed.external_id,
        sources=parsed.sources,
    )
