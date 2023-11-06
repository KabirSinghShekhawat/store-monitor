from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint

if TYPE_CHECKING:
    from src.store.models import Store


class StoreStatus(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("timestamp_utc", "store_id", name="unique_store_event"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp_utc: datetime
    status: str

    store_id: str = Field(foreign_key="store.store_id")
    store: "Store" = Relationship(back_populates="status_polls")
