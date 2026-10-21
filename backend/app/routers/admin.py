from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_api_key
from app.processing import reprocess as run_reprocess
from app.schemas import ReprocessOut

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/reprocess", response_model=ReprocessOut)
async def reprocess_history(session: AsyncSession = Depends(get_db)) -> ReprocessOut:
    result = await run_reprocess(session)
    return ReprocessOut(
        raw_events_processed=result.raw_events_processed,
        applications_rebuilt=result.applications_rebuilt,
        history_records_rebuilt=result.history_records_rebuilt,
        overrides_applied=result.overrides_applied,
    )
