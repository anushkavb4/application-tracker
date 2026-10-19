from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from app.models import Application


def unattributed_condition() -> ColumnElement[bool]:
    return or_(Application.company_name.is_(None), Application.role.is_(None))