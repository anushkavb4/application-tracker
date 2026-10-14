from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models import Application
from app.routers.applications import _apply_filters


def _compiled_filter(unattributed: bool) -> str:
    statement = _apply_filters(
        select(Application), None, None, None, None, None, None, unattributed
    )
    return str(statement.compile(dialect=postgresql.dialect()))


def test_unattributed_filter_selects_missing_company_names() -> None:
    statement = _compiled_filter(unattributed=True)

    assert "applications.company_name IS NULL" in statement


def test_unattributed_filter_is_disabled_by_default() -> None:
    statement = _compiled_filter(unattributed=False)

    assert "applications.company_name IS NULL" not in statement