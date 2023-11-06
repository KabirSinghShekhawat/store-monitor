from fastapi import APIRouter, Depends, status, HTTPException
from src.store_status.models import StoreStatus
from src.db import get_session
from sqlmodel import Session

from sqlalchemy.exc import IntegrityError

router = APIRouter(
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)


@router.post("/", response_model=StoreStatus)
def create_store(*, session: Session = Depends(get_session), store_status: StoreStatus):
    db_store_status = StoreStatus.from_orm(store_status)
    try:
        session.add(db_store_status)
        session.commit()
        session.refresh(db_store_status)
        return db_store_status
    except IntegrityError as e:
        session.rollback()
        print(f"Duplicate key error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Duplicate key error: {str(e)}")
    except Exception as e:
        session.rollback()
        print(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"an error occurred: {str(e)}")
