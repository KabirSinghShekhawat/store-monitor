from fastapi import APIRouter, Depends, status, HTTPException, Query
from typing import List
from src.store.models import Store
from src.db import get_session
from sqlmodel import Session, select

from sqlalchemy.exc import IntegrityError

router = APIRouter(
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)


@router.post("/", response_model=Store)
def create_store(*, session: Session = Depends(get_session), store: Store):
    db_store = Store.from_orm(store)
    try:
        session.add(db_store)
        session.commit()
        session.refresh(db_store)
        return db_store
    except IntegrityError as e:
        session.rollback()
        print(f"Duplicate key error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Duplicate key error: {str(e)}")
    except Exception as e:
        session.rollback()
        print(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"an error occurred: {str(e)}")


@router.get("/all", response_model=List[Store])
def get_stores(*, skip: int = 0, limit: int = Query(default=100, le=100), session: Session = Depends(get_session)):
    statement = select(Store).offset(skip).limit(limit)
    results = session.exec(statement)
    stores = results.all()
    return stores


@router.get("/{store_id}")
def get_store(*, store_id: str, session: Session = Depends(get_session)):
    statement = select(Store).where(Store.store_id == store_id)
    results = session.exec(statement)
    store = results.one()
    return store
