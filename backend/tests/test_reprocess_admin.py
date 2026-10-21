import asyncio

from app.processing import ReprocessResult
from app.routers import admin


def test_reprocess_history_returns_rebuild_counts(monkeypatch) -> None:
    async def fake_reprocess(session: object) -> ReprocessResult:
        return ReprocessResult(
            raw_events_processed=12,
            applications_rebuilt=5,
            history_records_rebuilt=12,
            overrides_applied=2,
        )

    monkeypatch.setattr(admin, "run_reprocess", fake_reprocess)

    result = asyncio.run(admin.reprocess_history(object()))

    assert result.model_dump() == {
        "raw_events_processed": 12,
        "applications_rebuilt": 5,
        "history_records_rebuilt": 12,
        "overrides_applied": 2,
        "errors": [],
    }
