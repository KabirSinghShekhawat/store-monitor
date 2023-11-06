from typing import Optional
from src.timezones.models import Timezone
from sqlmodel import Session, select


def get_timezone(store_id, session: Session) -> str:
    """Get Store's timezone_str (if exists) else default timezone"""
    result: Optional[Timezone] = None
    try:
        statement = select(Timezone).where(Timezone.store_id == store_id)
        result = session.exec(statement).one()
    except Exception as e:
        print(e)

    default_timezone = "America/Chicago"
    if result is None:
        return default_timezone
    else:
        return result.timezone_str
