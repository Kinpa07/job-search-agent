import structlog
from fastapi import FastAPI

from app.api.v1.jobs import router as jobs_router
from app.config import settings


def configure_logging() -> None:
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
    ]

    if settings.environment == "development":
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
        )
    else:
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
        )


configure_logging()

app = FastAPI(title="Job Search Agent")
app.include_router(jobs_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
