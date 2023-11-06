from uuid import uuid4

from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlmodel import Session

from src.db import get_session
from src.report.utils import get_report_status, create_report

router = APIRouter(
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}}
)


@router.get("/get_report/{report_id}")
def get_report(*, report_id: str):
    return get_report_status(report_id)


@router.post("/trigger_report")
def trigger_report_generation(*, session: Session = Depends(get_session), background_tasks: BackgroundTasks):
    report_id: str = str(uuid4())
    background_tasks.add_task(create_report, report_id, session)
    return {"report_id": report_id}
