from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    telegram_id: int
    api_token: str
    api_url: str
    model: str


    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()