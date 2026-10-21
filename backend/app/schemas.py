from datetime import datetime
import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


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
    manual_fields: list[str] = Field(default_factory=list)


ApplicationStatus = Literal[
    "viewed", "applied", "screening", "interview", "offer", "rejected", "withdrawn"
]


class ApplicationPatchIn(BaseModel):
    company_name: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, max_length=512)
    status: ApplicationStatus | None = None
    notes: str | None = Field(default=None, max_length=10000)


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


class ReprocessOut(BaseModel):
    raw_events_processed: int
    applications_rebuilt: int
    history_records_rebuilt: int
    overrides_applied: int
    errors: list[str] = Field(default_factory=list)


class PatternFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ats: str = Field(min_length=1, max_length=128)
    kind: str = Field(default="job_posting", min_length=1, max_length=32)
    url_regex: str = Field(min_length=1)
    title_regex: str | None = None
    priority: int = 100
    enabled: bool = True

    @field_validator("url_regex")
    @classmethod
    def validate_url_regex(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as error:
            raise ValueError(f"Invalid URL regex: {error}") from error
        return value

    @field_validator("title_regex")
    @classmethod
    def validate_title_regex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            re.compile(value)
        except re.error as error:
            raise ValueError(f"Invalid title regex: {error}") from error
        return value


class PatternCreateIn(PatternFields):
    pass


class PatternPatchIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ats: str | None = Field(default=None, min_length=1, max_length=128)
    kind: str | None = Field(default=None, min_length=1, max_length=32)
    url_regex: str | None = Field(default=None, min_length=1)
    title_regex: str | None = None
    priority: int | None = None
    enabled: bool | None = None

    @field_validator("url_regex")
    @classmethod
    def validate_url_regex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            re.compile(value)
        except re.error as error:
            raise ValueError(f"Invalid URL regex: {error}") from error
        return value

    @field_validator("title_regex")
    @classmethod
    def validate_title_regex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            re.compile(value)
        except re.error as error:
            raise ValueError(f"Invalid title regex: {error}") from error
        return value


class PatternOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ats: str
    kind: str
    url_regex: str
    title_regex: str | None
    priority: int
    enabled: bool
    created_at: datetime


class PatternTestIn(BaseModel):
    url: HttpUrl
    page_title: str | None = None
    pattern: PatternCreateIn


class PatternTestOut(BaseModel):
    matched: bool
    ats: str | None
    company: str | None
    role: str | None
    external_id: str | None
    sources: dict[str, str]
