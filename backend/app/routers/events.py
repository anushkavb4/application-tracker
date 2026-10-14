from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_api_key
from app.models import Application, ApplicationEvent, RawEvent, UrlPattern
from app.parsing.engine import parse_job
from app.parsing.resolver import is_forward, resolve
from app.schemas import EventBatchIn, EventBatchOut

router = APIRouter(prefix="/api/events", tags=["events"], dependencies=[Depends(require_api_key)])


@router.post("/batch", response_model=EventBatchOut)
async def ingest_events(
    batch: EventBatchIn,
    session: AsyncSession = Depends(get_db),
) -> EventBatchOut:
    ordered_events = sorted(batch.events, key=lambda event: event.captured_at)
    client_ids = {event.client_event_id for event in ordered_events}

    accepted = 0
    duplicates = 0
    applications_created = 0
    applications_updated = 0

    async with session.begin():
        existing_rows = await session.scalars(
            select(RawEvent).where(RawEvent.client_event_id.in_(client_ids))
        )
        existing_ids = {event.client_event_id for event in existing_rows}
        seen_ids: set[str] = set()
        patterns = list(
            await session.scalars(
                select(UrlPattern).where(UrlPattern.enabled.is_(True)).order_by(UrlPattern.priority)
            )
        )

        for event in ordered_events:
            if event.client_event_id in existing_ids or event.client_event_id in seen_ids:
                duplicates += 1
                continue
            seen_ids.add(event.client_event_id)

            raw_event = RawEvent(
                client_event_id=event.client_event_id,
                url=str(event.url),
                page_title=event.page_title,
                referrer=str(event.referrer) if event.referrer else None,
                trigger_type=event.trigger_type,
                tab_id=event.tab_id,
                nav_chain_id=event.nav_chain_id,
                captured_at=event.captured_at,
                payload=event.payload,
            )
            session.add(raw_event)
            await session.flush()

            parsed = parse_job(str(event.url), event.page_title, patterns)
            resolution = resolve(parsed, event.trigger_type)
            application = await session.scalar(
                select(Application).where(Application.dedup_key == resolution.dedup_key)
            )

            if application is None:
                application = Application(
                    dedup_key=resolution.dedup_key,
                    company_name=parsed.company,
                    role=parsed.role,
                    ats=parsed.ats,
                    external_id=parsed.external_id,
                    url=str(event.url),
                    status=resolution.status,
                    status_source=resolution.status_source,
                    confidence=resolution.confidence,
                    first_seen_at=event.captured_at,
                    last_seen_at=event.captured_at,
                    applied_at=(event.captured_at if resolution.status == "applied" else None),
                )
                session.add(application)
                await session.flush()
                applications_created += 1
            else:
                application.last_seen_at = max(application.last_seen_at, event.captured_at)
                application.confidence = max(application.confidence, resolution.confidence)
                if is_forward(application.status, resolution.status):
                    if application.status != resolution.status:
                        application.status = resolution.status
                        if resolution.status == "applied" and application.applied_at is None:
                            application.applied_at = event.captured_at
                    applications_updated += 1
                if not application.company_name and parsed.company:
                    application.company_name = parsed.company
                if not application.role and parsed.role:
                    application.role = parsed.role
                if not application.ats and parsed.ats:
                    application.ats = parsed.ats
                if not application.external_id and parsed.external_id:
                    application.external_id = parsed.external_id

            session.add(
                ApplicationEvent(
                    application_id=application.id,
                    raw_event_id=raw_event.id,
                    status=resolution.status,
                    confidence=resolution.confidence,
                    source=resolution.status_source,
                    occurred_at=event.captured_at,
                )
            )
            accepted += 1

    return EventBatchOut(
        accepted=accepted,
        duplicates=duplicates,
        applications_created=applications_created,
        applications_updated=applications_updated,
    )
