from celery import Celery

from app.core.config import settings

celery_app = Celery("aarogya", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_default_queue = "default"
celery_app.conf.imports = ("app.tasks.document_tasks", "app.tasks.telegram_tasks")
celery_app.autodiscover_tasks(["app.tasks"])
celery_app.conf.beat_schedule = {
    # Long-poll fallback: picks up updates when no webhook is registered.
    "telegram-poll": {
        "task": "app.tasks.telegram_tasks.poll_telegram_once",
        "schedule": 30.0,
    },
    # Check-in tick: morning slot generation + due sender.
    "telegram-checkins": {
        "task": "app.tasks.telegram_tasks.run_checkin_tick",
        "schedule": 600.0,
    },
}
