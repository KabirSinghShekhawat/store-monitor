from typing import Optional, TYPE_CHECKING

from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from src.store.models import Store


class Timezone(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timezone_str: str

    store_id: str = Field(unique=True, foreign_key="store.store_id")
    store: "Store" = Relationship(back_populates="timezone")
