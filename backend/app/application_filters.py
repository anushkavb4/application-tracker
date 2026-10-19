from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from app.models import Application
from app.parsing.resolver import APPLIED_CONFIDENCE_THRESHOLD


def unattributed_condition() -> ColumnElement[bool]:
    return or_(
        Application.company_name.is_(None),
        Application.company_name == "",
        Application.role.is_(None),
        Application.role == "",
        Application.ats.is_(None),
        Application.ats == "",
        Application.confidence < APPLIED_CONFIDENCE_THRESHOLD,
    )