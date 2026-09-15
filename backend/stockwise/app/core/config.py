from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "stockwise"
    postgres_password: str = "stockwise_local_password"
    postgres_db: str = "stockwise"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    sqlalchemy_pool_size: int = 5
    sqlalchemy_max_overflow: int = 10
    sqlalchemy_pool_timeout: int = 5
    allowed_cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    secret_key: str = "dev-secret-change-in-production"
    session_cookie_secure: bool = False
    session_cookie_same_site: str = "lax"
    session_cookie_max_age: int = 86400 * 7  # 7 days
    csrf_cookie_max_age: int = 86400  # 1 day

    rate_limit_register: str = "5/minute"
    rate_limit_login: str = "10/minute"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
