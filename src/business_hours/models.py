from typing import Optional, TYPE_CHECKING
from datetime import time

from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from src.store.models import Store


class BusinessHours(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day_of_week: int
    start_time_local: time
    end_time_local: time

    store_id: str = Field(foreign_key="store.store_id")
    store: "Store" = Relationship(back_populates="business_hours")
