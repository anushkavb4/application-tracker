"""Rebuild applications from raw events: `python -m app.reprocess`."""

import asyncio

from app.db import SessionLocal, engine
from app.processing import reprocess


async def main() -> None:
    async with SessionLocal() as session:
        result = await reprocess(session)
    await engine.dispose()
    print(
        f"Processed {result.raw_events_processed} raw events: "
        f"{result.applications_rebuilt} applications, "
        f"{result.history_records_rebuilt} history records, "
        f"{result.overrides_applied} manual overrides replayed."
    )


if __name__ == "__main__":
    asyncio.run(main())
