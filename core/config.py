from typing import Final, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_CONFIGFILE: Final[str] = ".env"

LOG_LEVEL_LITERAL = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_CONFIGFILE,
        env_file_encoding="utf-8",
    )

    tg_api_token: str = Field(default=...)
    payment_provider_token: str = Field(default="TEST_PROVIDER_TOKEN")

    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="postgres")

    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)

    log_level: LOG_LEVEL_LITERAL = Field(default="INFO")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
