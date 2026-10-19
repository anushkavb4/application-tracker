from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, ApplicationEvent, ManualOverride, RawEvent, UrlPattern
from app.parsing.engine import PatternRow, parse_job
from app.parsing.resolver import is_forward, resolve
from app.seed_patterns import SEED_PATTERNS

REPROCESS_CHUNK_SIZE = 200


async def load_patterns(session: AsyncSession) -> list[UrlPattern]:
    return list(
        await session.scalars(
            select(UrlPattern).where(UrlPattern.enabled.is_(True)).order_by(UrlPattern.priority)
        )
    )


async def apply_raw_event(
    session: AsyncSession, raw_event: RawEvent, patterns: Sequence[PatternRow]
) -> bool:
    """Fold one stored raw event into its application. Returns True if a new row was created."""
    parsed = parse_job(raw_event.url, raw_event.page_title, patterns)
    resolution = resolve(parsed, raw_event.trigger_type)
    application = await session.scalar(
        select(Application).where(Application.dedup_key == resolution.dedup_key)
    )
    created = application is None

    if application is None:
        application = Application(
            dedup_key=resolution.dedup_key,
            company_name=parsed.company,
            role=parsed.role,
            ats=parsed.ats,
            external_id=parsed.external_id,
            url=raw_event.url,
            status=resolution.status,
            status_source=resolution.status_source,
            confidence=resolution.confidence,
            first_seen_at=raw_event.captured_at,
            last_seen_at=raw_event.captured_at,
            applied_at=(raw_event.captured_at if resolution.status == "applied" else None),
        )
        session.add(application)
        await session.flush()
    else:
        application.last_seen_at = max(application.last_seen_at, raw_event.captured_at)
        application.confidence = max(application.confidence, resolution.confidence)
        if application.status_source != "manual" and is_forward(application.status, resolution.status):
            if application.status != resolution.status:
                application.status = resolution.status
                if resolution.status == "applied" and application.applied_at is None:
                    application.applied_at = raw_event.captured_at
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
            occurred_at=raw_event.captured_at,
        )
    )
    return created


@dataclass(frozen=True)
class ReprocessResult:
    raw_events_processed: int
    applications_rebuilt: int
    history_records_rebuilt: int
    overrides_applied: int


async def reprocess(session: AsyncSession) -> ReprocessResult:
    """Rebuild every derived table from `raw_events` under the current patterns.

    Raw events and manual overrides are never modified; overrides are replayed onto the
    rebuilt applications, matched by dedup key. Application UUIDs change.
    """
    async with session.begin():
        await session.execute(delete(ApplicationEvent))
        await session.execute(delete(Application))
        patterns = await load_patterns(session)

        processed = 0
        offset = 0
        while True:
            chunk = list(
                await session.scalars(
                    select(RawEvent)
                    .order_by(RawEvent.captured_at, RawEvent.id)
                    .offset(offset)
                    .limit(REPROCESS_CHUNK_SIZE)
                )
            )
            if not chunk:
                break
            for raw_event in chunk:
                await apply_raw_event(session, raw_event, patterns)
            processed += len(chunk)
            offset += REPROCESS_CHUNK_SIZE
            await session.flush()

        overrides_applied = 0
        for override in await session.scalars(select(ManualOverride)):
            application = await session.scalar(
                select(Application).where(Application.dedup_key == override.dedup_key)
            )
            if application is None:
                continue
            if override.status:
                application.status = override.status
                application.status_source = "manual"
            if override.company_name:
                application.company_name = override.company_name
            if override.role:
                application.role = override.role
            if override.notes:
                application.notes = override.notes
            overrides_applied += 1

        await session.flush()
        applications = await session.scalar(select(func.count(Application.id)))
        history = await session.scalar(select(func.count(ApplicationEvent.id)))

    return ReprocessResult(
        raw_events_processed=processed,
        applications_rebuilt=int(applications or 0),
        history_records_rebuilt=int(history or 0),
        overrides_applied=overrides_applied,
    )


async def seed_patterns_if_empty(session: AsyncSession) -> int:
    """Insert the starter patterns on first boot only, so deleted patterns stay deleted."""
    async with session.begin():
        if await session.scalar(select(func.count(UrlPattern.id))):
            return 0
        session.add_all(
            UrlPattern(
                ats=spec.ats,
                kind=spec.kind,
                url_regex=spec.url_regex,
                title_regex=spec.title_regex,
                priority=spec.priority,
                enabled=spec.enabled,
            )
            for spec in SEED_PATTERNS
        )
    return len(SEED_PATTERNS)
