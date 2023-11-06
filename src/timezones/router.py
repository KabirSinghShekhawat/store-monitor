from fastapi import APIRouter, Depends, status, HTTPException
from src.timezones.models import Timezone
from src.db import get_session
from sqlmodel import Session

from sqlalchemy.exc import IntegrityError

router = APIRouter(
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)


@router.post("/", response_model=Timezone)
def create_timezone(*, session: Session = Depends(get_session), timezone: Timezone):
    db_timezone = Timezone.from_orm(timezone)
    try:
        session.add(db_timezone)
        session.commit()
        session.refresh(db_timezone)
        return db_timezone
    except IntegrityError as e:
        session.rollback()
        print(f"Duplicate key error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Duplicate key error: {str(e)}")
    except Exception as e:
        session.rollback()
        print(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"an error occurred: {str(e)}")
