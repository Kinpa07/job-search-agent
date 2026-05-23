from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/jobsearch"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/jobsearch"
    redis_url: str = "redis://localhost:6379/0"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
