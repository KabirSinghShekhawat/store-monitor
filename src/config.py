import os

from dotenv import dotenv_values
from pydantic import BaseSettings

config = {
    **dotenv_values(".env"),
    **os.environ,  # override loaded values with environment variables
}


class CommonSettings(BaseSettings):
    DEBUG_MODE: bool = bool(config.get("DEBUG")) and config.get("DEBUG") == "true"


class ServerSettings(BaseSettings):
    HOST: str = "127.0.0.1"
    PORT: int = int(config.get("PORT")) or 8000


class DatabaseSettings(BaseSettings):
    DATABASE_URL: str = config.get("DATABASE_URL")


class Settings(
    CommonSettings,
    ServerSettings,
    DatabaseSettings,
):
    pass


settings = Settings()
