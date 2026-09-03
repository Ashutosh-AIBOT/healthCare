from celery import Celery

from app.core.config import settings

celery_app = Celery("aarogya", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_default_queue = "default"
celery_app.conf.imports = ("app.tasks.document_tasks",)
celery_app.autodiscover_tasks(["app.tasks"])
