from sqlmodel import SQLModel, create_engine, Session
from src.config import settings
import src.store.models
import src.store_status.models
import src.business_hours.models
import src.timezones.models

engine = create_engine(settings.DATABASE_URL)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
