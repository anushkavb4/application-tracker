import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models import Application, ApplicationEvent, ManualOverride
from app.processing import _apply_manual_override
from app.routers.applications import update_application
from app.schemas import ApplicationPatchIn


class FakeSession:
    def __init__(self, application: Application | None) -> None:
        self.application = application
        self.override: ManualOverride | None = None
        self.added: list[object] = []
        self.committed = False

    async def get(self, model: type[Application], application_id: object) -> Application | None:
        return self.application

    async def scalar(self, statement: object) -> ManualOverride | None:
        return self.override

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, ManualOverride):
            self.override = value

    async def commit(self) -> None:
        self.committed = True


def test_update_application_persists_manual_fields_and_status_event() -> None:
    now = datetime.now(timezone.utc)
    application = Application(
        id=uuid4(),
        dedup_key="greenhouse:role-123",
        company_name="Old Company",
        role="Old Role",
        ats="greenhouse",
        external_id="role-123",
        url="https://boards.greenhouse.io/example/jobs/123",
        status="viewed",
        status_source="automatic",
        confidence=10,
        first_seen_at=now,
        last_seen_at=now,
        applied_at=None,
        notes=None,
    )
    session = FakeSession(application)

    result = asyncio.run(
        update_application(
            application.id,
            ApplicationPatchIn(company_name="New Company", role="Analyst", status="interview", notes=""),
            session,
        )
    )

    assert session.committed
    assert application.company_name == "New Company"
    assert application.role == "Analyst"
    assert application.status == "interview"
    assert application.status_source == "manual"
    assert application.notes == ""
    assert result.manual_fields == ["company_name", "role", "status", "notes"]
    assert session.override is not None
    assert session.override.notes == ""
    events = [value for value in session.added if isinstance(value, ApplicationEvent)]
    assert len(events) == 1
    assert events[0].source == "manual"
    assert events[0].status == "interview"


def test_update_application_returns_not_found_for_unknown_id() -> None:
    session = FakeSession(None)

    with pytest.raises(HTTPException) as error:
        asyncio.run(update_application(uuid4(), ApplicationPatchIn(company_name="New Company"), session))

    assert error.value.status_code == 404


def test_manual_override_replay_preserves_explicit_empty_values() -> None:
    application = Application(
        dedup_key="greenhouse:role-123",
        company_name="Old Company",
        role="Old Role",
        status="viewed",
        status_source="automatic",
        notes="Previous note",
    )
    override = ManualOverride(
        dedup_key=application.dedup_key,
        company_name="",
        role="",
        status="interview",
        notes="",
    )

    _apply_manual_override(application, override)

    assert application.company_name == ""
    assert application.role == ""
    assert application.status == "interview"
    assert application.status_source == "manual"
    assert application.notes == ""
