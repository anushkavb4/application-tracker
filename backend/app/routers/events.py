from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_api_key
from app.models import RawEvent
from app.processing import apply_raw_event, load_patterns
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
        patterns = await load_patterns(session)

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

            if await apply_raw_event(session, raw_event, patterns):
                applications_created += 1
            else:
                applications_updated += 1
            accepted += 1

    return EventBatchOut(
        accepted=accepted,
        duplicates=duplicates,
        applications_created=applications_created,
        applications_updated=applications_updated,
    )
