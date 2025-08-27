from typing import Optional

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    telegram_id: Optional[str]
    api_token: Optional[str]
    api_url: Optional[str]
    model: Optional[str]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()