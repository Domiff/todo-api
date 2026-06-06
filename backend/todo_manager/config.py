from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DJANGO_SECRET_KEY: str
    DJANGO_DEBUG: bool
    ALLOWED_HOSTS: list[str]

    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    model_config = SettingsConfigDict(
        env_file="../.env.django",
        env_file_encoding="utf-8",
    )


settings = Settings()
