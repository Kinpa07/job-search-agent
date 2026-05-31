import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/jobsearch"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/jobsearch"
    redis_url: str = "redis://localhost:6379/0"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"

    # Claude API (Module 3+)
    anthropic_api_key: str = ""

    # LangSmith tracing (Module 3+, Standing Rule 7)
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "job-search-agent"


settings = Settings()

# LangChain/LangGraph auto-tracing reads os.environ, not this Settings object.
# Propagate the LangSmith config so tracing works when running locally from .env.
# (In Docker/Railway these are passed as real env vars and this is a no-op.)
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)
