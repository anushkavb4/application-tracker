from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


TriggerType = Literal["intent_click", "ats_nav", "form_submit"]


class EventIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    client_event_id: str = Field(min_length=1, max_length=128)
    url: HttpUrl
    page_title: str = Field(min_length=1, max_length=2000)
    referrer: HttpUrl | None = None
    trigger_type: TriggerType
    tab_id: int | None = Field(default=None, ge=0)
    nav_chain_id: UUID | None = None
    captured_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class EventBatchIn(BaseModel):
    events: list[EventIn] = Field(min_length=1, max_length=100)


class EventBatchOut(BaseModel):
    accepted: int
    duplicates: int
    applications_created: int
    applications_updated: int


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dedup_key: str
    company_name: str | None
    role: str | None
    ats: str | None
    external_id: str | None
    url: str
    status: str
    status_source: str
    confidence: int
    first_seen_at: datetime
    last_seen_at: datetime
    applied_at: datetime | None
    notes: str | None


class ApplicationListOut(BaseModel):
    items: list[ApplicationOut]
    total: int
    page: int
    page_size: int


class StatsSummaryOut(BaseModel):
    total: int
    unattributed_count: int
    status_counts: dict[str, int]
    applied_count: int
    response_count: int
    response_rate: float
    applications_over_time: list[dict[str, Any]]
