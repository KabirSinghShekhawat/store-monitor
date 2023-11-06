from fastapi import APIRouter, Depends, status, HTTPException
from src.business_hours.models import BusinessHours
from src.db import get_session
from sqlmodel import Session

from sqlalchemy.exc import IntegrityError

router = APIRouter(
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)


@router.post("/", response_model=BusinessHours)
def create_timezone(*, session: Session = Depends(get_session), business_hour: BusinessHours):
    db_business_hour = BusinessHours.from_orm(business_hour)
    try:
        session.add(db_business_hour)
        session.commit()
        session.refresh(db_business_hour)
        return db_business_hour
    except IntegrityError as e:
        session.rollback()
        print(f"Duplicate key error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Duplicate key error: {str(e)}")
    except Exception as e:
        session.rollback()
        print(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"an error occurred: {str(e)}")
