from typing import Optional, List, TYPE_CHECKING

from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from src.store_status.models import StoreStatus
    from src.business_hours.models import BusinessHours
    from src.timezones.models import Timezone


class Store(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    store_id: str = Field(index=True, unique=True)

    status_polls: List["StoreStatus"] = Relationship(back_populates="store")
    business_hours: List["BusinessHours"] = Relationship(back_populates="store")
    timezone: Optional["Timezone"] = Relationship(back_populates="store")
