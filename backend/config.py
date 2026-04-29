from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    jquants_email: str = ""
    jquants_password: str = ""
    database_url: str = "sqlite:///./screener.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
