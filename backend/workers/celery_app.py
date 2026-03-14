"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "data_aggregator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["workers.tasks", "workers.scheduled_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Add beat schedule for periodic tasks
    beat_schedule={
        'refresh-recent-jobs': {
            'task': 'workers.scheduled_tasks.refresh_recent_jobs',
            'schedule': 5.0,  # Run every 5 seconds
            'args': (30,)  # ← Look back 30 minutes
        },
        'cleanup-old-jobs': {
            'task': 'workers.scheduled_tasks.cleanup_old_jobs',
            'schedule': 300.0,  # Run every 5 minutes
            'args': (60,)
        },
    }
)

# Fix the deprecation warning
celery_app.conf.broker_connection_retry_on_startup = True

celery_app.autodiscover_tasks(["workers"])