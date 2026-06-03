from celery import Celery

from app.config import settings

celery_app = Celery("job_search_agent", broker=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # acknowledge after completion, not receipt — survives worker crash
    task_reject_on_worker_lost=True,
)

celery_app.autodiscover_tasks(["app.tasks"])

celery_app.conf.beat_schedule = {
    "poll-all-sources": {
        "task": "app.tasks.poll_all_sources",
        "schedule": settings.poll_interval_seconds,
    },
}
