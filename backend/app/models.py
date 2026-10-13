import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RawEvent(Base):
    __tablename__ = "raw_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_event_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    page_title: Mapped[str] = mapped_column(Text, nullable=False)
    referrer: Mapped[str | None] = mapped_column(Text)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    tab_id: Mapped[int | None] = mapped_column(Integer)
    nav_chain_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dedup_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    company_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(512))
    ats: Mapped[str | None] = mapped_column(String(128))
    external_id: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="viewed")
    status_source: Mapped[str] = mapped_column(String(32), nullable=False, default="automatic")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    raw_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="automatic")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


class UrlPattern(Base):
    __tablename__ = "url_patterns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ats: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="job_posting")
    url_regex: Mapped[str] = mapped_column(Text, nullable=False)
    title_regex: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ManualOverride(Base):
    __tablename__ = "manual_overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dedup_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    status: Mapped[str | None] = mapped_column(String(32))
    company_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
