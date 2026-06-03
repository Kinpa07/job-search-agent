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
    anthropic_model: str = "claude-sonnet-4-6"
    # Dev record/replay cache for tool-calling LLM invocations (Standing Rule 6). Off by
    # default — flip on (LLM_CACHE_ENABLED=true) to replay identical requests for free.
    llm_cache_enabled: bool = False

    # LangSmith tracing (Module 3+, Standing Rule 7)
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "job-search-agent"
    # Data region endpoint — US by default; EU workspaces must set this to
    # https://eu.api.smith.langchain.com or ingestion 403s.
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # Source slug registries (Module 1)
    greenhouse_slugs: dict[str, str] = {
        "sumup": "SumUp",
        "ocadogroup": "Ocado Group",
        "sofiastars": "Sofia Stars",
        "workboard": "WorkBoard",
        "pointwild": "Point Wild",
        "conga": "Conga",
        "bettyjobboard": "Betty",
        "payhawkio": "Payhawk",
        "skyscanner": "Skyscanner",
    }
    lever_slugs: dict[str, str] = {
        "Fliff": "Fliff",
        "capital": "Capital.com",
        "crypto": "Crypto.com",
        "binance": "Binance",
        "OpenPayd": "OpenPayd",
        "doola": "doola",
        "remofirst": "RemoFirst",
        "pipedrive": "Pipedrive",
    }
    ashby_slugs: dict[str, str] = {
        "trading212": "Trading212",
        "elevenlabs": "ElevenLabs",
        "searchapi": "SearchApi",
        "n8n": "n8n",
        "Redis": "Redis",
        "lucidlink": "LucidLink",
        "p2p.org": "P2P.org",
        "duvo": "Duvo",
    }

    # Polling cadence (Module 2)
    poll_interval_seconds: int = 6 * 60 * 60  # 6 hours

    # Default operator filters (Module 1 — used by JobFilters)
    default_entry_level_only: bool = True
    default_posted_within_days: int = 1
    default_remote_ok: bool = False
    default_location: str | None = None

    # Title-filter term lists (Module 1 — used by title_allowed in adapters/base.py)
    seniority_terms: tuple[str, ...] = (
        "senior",
        "sr",
        "lead",
        "principal",
        "staff",
        "head of",
        "director",
        "vp",
        "vice president",
    )
    exclude_title_terms: tuple[str, ...] = (
        "manager",
        "designer",
        "recruiter",
        "sales",
        "account executive",
        "marketing",
        "human resources",
        "accountant",
        "customer success",
        "scrum master",
    )


settings = Settings()

# LangChain/LangGraph auto-tracing reads os.environ, not this Settings object.
# Propagate the LangSmith config so tracing works when running locally from .env.
# (In Docker these are passed as real env vars and this is a no-op.)
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)
    os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.langchain_endpoint)
