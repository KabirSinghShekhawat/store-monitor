from datetime import datetime, timedelta, timezone, time
from enum import Enum
from typing import List
from zoneinfo import ZoneInfo

import pandas as pd
from pandas.errors import EmptyDataError
from sqlalchemy import func
from sqlmodel import select, Session

from src.business_hours.models import BusinessHours
from src.store.models import Store
from src.store.utils import get_timezone
from src.store_status.models import StoreStatus


class StoreStatusEnum(str, Enum):
    active = "active"
    inactive = "inactive"


class WeeklyReport:
    def __init__(self, store_id: str):
        # uptime, downtime, day
        self.daily_reports = {}
        self.store_id: str = store_id
        self.uptime_last_hour = 0
        self.downtime_last_hour = 0

    def update_last_hour_records(self, minutes: int, status: str):
        if not (0 <= minutes <= 60):
            raise ValueError(f"minutes={minutes}. minutes must be between 0, 60.")

        if status == StoreStatusEnum.active.value:
            self.uptime_last_hour += minutes
        elif status == StoreStatusEnum.inactive.value:
            self.downtime_last_hour += minutes

    def record_hours(self, day: int, hours: int, status: str):
        if day < 0:
            raise ValueError(f"day={day}. day cannot be < 0.")

        add_uptime, add_downtime = 0, 0
        if status == StoreStatusEnum.active.value:
            add_uptime = hours
        elif status == StoreStatusEnum.inactive.value:
            add_downtime = hours

        if self.daily_reports.get(str(day), None) is None:
            self.daily_reports[str(day)] = {"uptime": 0, "downtime": 0}

        self.daily_reports[str(day)]["uptime"] += add_uptime
        self.daily_reports[str(day)]["downtime"] += add_downtime

    def get_last_day_report(self) -> dict:
        return self.daily_reports.get("1", {"uptime": 0, "downtime": 0})

    def get_report(self):
        last_day_report = self.get_last_day_report()
        uptime_last_week, downtime_last_week = 0, 0
        for k, v in self.daily_reports.items():
            uptime_last_week += v["uptime"]
            downtime_last_week += v["downtime"]

        return {
            "store_id": self.store_id,
            "uptime_last_hour": self.uptime_last_hour,
            "uptime_last_day": last_day_report["uptime"],
            "uptime_last_week": uptime_last_week,
            "downtime_last_hour": self.downtime_last_hour,
            "downtime_last_day": last_day_report["downtime"],
            "downtime_last_week": downtime_last_week,
        }


def get_filename(report_id: str) -> str:
    file_name = 'report-' + report_id + '.csv'
    return file_name


def store_report_to_disk(report_id: str, reports):
    df = pd.DataFrame(reports)
    file_name = get_filename(report_id)
    df.to_csv(file_name, index=False)
    print(f"stored {file_name} to disk.")


def load_report_from_disk(report_id: str):
    file_name = get_filename(report_id)
    try:
        df = pd.read_csv(file_name)
        # Convert the DataFrame to a list of dictionaries (each row)
        data = df.to_dict(orient="records")
        return data
    except EmptyDataError:
        print(f"file '{file_name}' has no data.")
        return {}


def get_report_status(report_id: str):
    try:
        report = load_report_from_disk(report_id)

        return {
            "status": "COMPLETE",
            "report": report
        }
    except Exception as e:
        print(e)
        return {"status": "RUNNING"}


def find_business_hours_by_day(db_business_hours: List["BusinessHours"], day_of_week: int) -> dict:
    """Find the business hours for a particular day of the week (Mon=0, Sun=6)"""
    # select the business day and respective timings.
    business_hours = {}
    for dbh in db_business_hours:
        if dbh.day_of_week == day_of_week:
            business_hours["start_time"] = dbh.start_time_local
            business_hours["end_time"] = dbh.end_time_local
            business_hours["day"] = dbh.day_of_week
            break
    # if no business day is found, fallback to 24x7 timings.
    if len(business_hours) == 0:
        business_hours["start_time"] = time().fromisoformat("00:00:00")
        business_hours["end_time"] = time().fromisoformat("23:59:59")
        business_hours["day"] = day_of_week

    return business_hours


def calculate_last_hour(max_timestamp_utc, store: Store, db_business_hours: List["BusinessHours"], session: Session,
                        weekly_report: WeeklyReport, timezone: str):
    """Calculate uptime/downtime for the last hour"""
    one_hour_ago = max_timestamp_utc + timedelta(hours=-1)
    last_hour_events_statement = select(StoreStatus).where(StoreStatus.store_id == store.store_id,
                                                           StoreStatus.timestamp_utc >= one_hour_ago,
                                                           StoreStatus.timestamp_utc < max_timestamp_utc).order_by(
        StoreStatus.timestamp_utc)

    # last hour's events
    last_hour_events: List["StoreStatus"] = session.exec(last_hour_events_statement).all()
    # day_of_week in db_business_hours is 0 indexed (0-6) but
    # `isoweekday()` is 1 indexed (1-7)
    day_of_week = one_hour_ago.isoweekday() - 1
    bh = find_business_hours_by_day(db_business_hours, day_of_week)
    opening_time: time = bh["start_time"]
    closing_time: time = bh["end_time"]

    window = opening_time
    while window < closing_time:
        if not (one_hour_ago.time() <= opening_time <= max_timestamp_utc.time()):
            break

        if len(last_hour_events) == 0:
            minutes: int = 60
            weekly_report.update_last_hour_records(minutes, StoreStatusEnum.inactive.value)
            break

        e = last_hour_events.pop()  # oldest event first
        event_timestamp_local = e.timestamp_utc.astimezone(ZoneInfo(timezone))

        if event_timestamp_local.time() >= closing_time:
            minutes: int = abs(closing_time.minute - window.minute)
            weekly_report.update_last_hour_records(minutes, e.status)
            break
        elif window <= event_timestamp_local.time() < closing_time:
            minutes: int = abs(event_timestamp_local.time().minute - window.minute)
            weekly_report.update_last_hour_records(minutes, status=e.status)
            window = event_timestamp_local.time()


def report_generator(store: Store, session: Session):
    max_timestamp_utc: datetime = session.exec(select([func.max(StoreStatus.timestamp_utc)])).first()
    timezone_str: str = get_timezone(store.store_id, session)

    # convert max timestamp into current store's local timezone for easy comparisons.
    max_timestamp_local: datetime = max_timestamp_utc.astimezone(ZoneInfo(timezone_str))

    db_business_hours = session.exec(
        select(BusinessHours).where(BusinessHours.store_id == store.store_id).order_by(BusinessHours.day_of_week)).all()

    weekly_report = WeeklyReport(store.store_id)

    calculate_last_hour(max_timestamp_utc=max_timestamp_utc, store=store, db_business_hours=db_business_hours,
                        session=session, weekly_report=weekly_report, timezone=timezone_str)

    """Calculating the uptime/downtime for each day of the week."""
    curr_t = datetime(year=max_timestamp_local.year, month=max_timestamp_local.month, day=max_timestamp_local.day,
                      tzinfo=max_timestamp_local.tzinfo)
    days_in_week = 7
    days = []
    for i in range(days_in_week):
        curr_t = curr_t + timedelta(days=-1)
        days.append(curr_t)

        current_day_utc = curr_t.astimezone(timezone.utc)
        next_day_utc = current_day_utc + timedelta(days=1)
        store_events_statement = select(StoreStatus).where(StoreStatus.store_id == store.store_id,
                                                           StoreStatus.timestamp_utc >= current_day_utc,
                                                           StoreStatus.timestamp_utc < next_day_utc).order_by(
            StoreStatus.timestamp_utc)
        # current day's events
        store_events: List["StoreStatus"] = session.exec(store_events_statement).all()

        current_day_of_week = curr_t.isoweekday() - 1
        # day_of_week in db_business_hours is 0 indexed (0-6) but
        # `isoweekday()` is 1 indexed (1-7)
        business_hours_today = find_business_hours_by_day(db_business_hours, current_day_of_week)
        start_time = business_hours_today["start_time"]
        end_time = business_hours_today["end_time"]
        window = start_time

        while window < end_time:
            if len(store_events) == 0:
                weekly_report.record_hours(day=(i + 1), hours=abs(end_time.hour - window.hour),
                                           status=StoreStatusEnum.inactive.value)
                break

            e = store_events.pop()  # oldest event first
            event_timestamp_local = e.timestamp_utc.astimezone(ZoneInfo(timezone_str))

            if event_timestamp_local.time() >= end_time:
                weekly_report.record_hours(day=(i + 1), hours=abs(end_time.hour - window.hour), status=e.status)
                break
            elif window <= event_timestamp_local.time() < end_time:
                weekly_report.record_hours(day=(i + 1), hours=abs(event_timestamp_local.time().hour - window.hour),
                                           status=e.status)
                window = event_timestamp_local.time()

    return weekly_report.get_report()


def create_report(report_id: str, session: Session):
    reports = []
    statement = select(Store)
    results = session.exec(statement)
    stores: List["Store"] = results.all()
    for store in stores:
        report = report_generator(store, session)
        reports.append(report)

    store_report_to_disk(report_id, reports)

    return {
        "report_id": report_id,
        "report": reports,
    }
