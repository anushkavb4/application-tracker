import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models import UrlPattern
from app.routers.patterns import create_pattern, delete_pattern, dry_run_pattern, update_pattern
from app.schemas import PatternCreateIn, PatternPatchIn, PatternTestIn


class FakeSession:
    def __init__(self, records: list[UrlPattern] | None = None) -> None:
        self.records = records or []
        self.added: list[UrlPattern] = []
        self.deleted: list[UrlPattern] = []
        self.committed = False

    async def get(self, model: type[UrlPattern], pattern_id: UUID) -> UrlPattern | None:
        return next((record for record in self.records if record.id == pattern_id), None)

    def add(self, record: UrlPattern) -> None:
        if record.id is None:
            record.id = uuid4()
        if record.created_at is None:
            record.created_at = datetime.now(timezone.utc)
        self.added.append(record)
        self.records.append(record)

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, record: UrlPattern) -> None:
        return None

    async def delete(self, record: UrlPattern) -> None:
        self.deleted.append(record)
        self.records.remove(record)


def test_create_pattern_saves_validated_pattern() -> None:
    session = FakeSession()
    pattern = PatternCreateIn(
        ats=" example ",
        url_regex=r"jobs\.example\.com",
        title_regex=None,
    )

    result = asyncio.run(create_pattern(pattern, session))

    assert session.committed
    assert result.ats == "example"
    assert result.kind == "job_posting"
    assert result.id is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [("url_regex", "("), ("title_regex", "(")],
)
def test_invalid_regex_is_rejected(field: str, value: str) -> None:
    values = {"ats": "example", "url_regex": r"jobs\.example\.com"}
    values[field] = value

    with pytest.raises(ValidationError):
        PatternCreateIn(**values)


def test_update_pattern_supports_disabling_and_clearing_title_regex() -> None:
    record = UrlPattern(
        id=uuid4(),
        ats="example",
        kind="ats",
        url_regex=r"jobs\.example\.com",
        title_regex=r"(?P<role>Engineer)",
        priority=10,
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    session = FakeSession([record])

    result = asyncio.run(
        update_pattern(record.id, PatternPatchIn(enabled=False, title_regex=None), session)
    )

    assert session.committed
    assert result.enabled is False
    assert result.title_regex is None


def test_update_pattern_rejects_empty_patch() -> None:
    record = UrlPattern(
        id=uuid4(),
        ats="example",
        kind="ats",
        url_regex="example",
        priority=10,
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(update_pattern(record.id, PatternPatchIn(), FakeSession([record])))
    assert error.value.status_code == 422


def test_delete_pattern_removes_record() -> None:
    record = UrlPattern(
        id=uuid4(),
        ats="example",
        kind="ats",
        url_regex="example",
        priority=10,
        enabled=True,
        created_at=datetime.now(timezone.utc),
    )
    session = FakeSession([record])

    asyncio.run(delete_pattern(record.id, session))

    assert session.committed
    assert session.deleted == [record]
    assert session.records == []


def test_pattern_dry_run_reports_matched_fields_and_sources() -> None:
    candidate = PatternTestIn(
        url="https://jobs.example.com/acme/123",
        page_title="Senior Engineer at Acme",
        pattern=PatternCreateIn(
            ats="example",
            kind="ats",
            url_regex=r"jobs\.example\.com/(?P<company>[^/]+)/(?P<external_id>\d+)",
            title_regex=r"(?P<role>Senior Engineer) at (?P<company>Acme)",
        ),
    )

    result = asyncio.run(dry_run_pattern(candidate))

    assert result.matched
    assert result.ats == "example"
    assert result.company == "Acme"
    assert result.role == "Senior Engineer"
    assert result.external_id == "123"
    assert result.sources == {
        "company": "title",
        "external_id": "url",
        "role": "title",
    }


def test_pattern_dry_run_reports_unmatched_url() -> None:
    candidate = PatternTestIn(
        url="https://other.example.com/jobs/123",
        pattern=PatternCreateIn(ats="example", url_regex=r"jobs\.example\.com/(?P<external_id>\d+)"),
    )

    result = asyncio.run(dry_run_pattern(candidate))

    assert not result.matched
    assert result.ats is None
    assert result.external_id is None
