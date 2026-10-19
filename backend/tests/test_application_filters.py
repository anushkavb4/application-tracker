from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.application_filters import unattributed_condition
from app.models import Application
from app.routers.applications import _apply_filters


def _compiled_filter(unattributed: bool) -> str:
    statement = _apply_filters(
        select(Application), None, None, None, None, None, None, unattributed
    )
    return str(statement.compile(dialect=postgresql.dialect()))


def test_unattributed_filter_matches_missing_company_or_role() -> None:
    statement = _compiled_filter(unattributed=True)

    assert "applications.company_name IS NULL" in statement
    assert "applications.role IS NULL" in statement
    assert " OR " in statement


def test_unattributed_filter_is_disabled_by_default() -> None:
    statement = _compiled_filter(unattributed=False)

    assert "applications.company_name IS NULL" not in statement
    assert "applications.role IS NULL" not in statement


def test_unattributed_count_uses_the_same_filter_condition() -> None:
    statement = str(
        select(Application.id)
        .where(unattributed_condition())
        .compile(dialect=postgresql.dialect())
    )

    assert "applications.company_name IS NULL" in statement
    assert "applications.role IS NULL" in statement
    assert " OR " in statement