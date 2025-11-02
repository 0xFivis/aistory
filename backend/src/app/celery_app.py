"""
Celery application factory configured via Settings
"""
import sys
from celery import Celery
from app.config.settings import get_settings
from app.utils.timezone import apply_timezone_settings


def create_celery() -> Celery:
    apply_timezone_settings()
    settings = get_settings()
    app = Celery(
        "aistory",
        broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
        backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
        include=[
            # Register our tasks package so Celery can discover tasks
            "app.tasks.storyboard_task",
            "app.tasks.image_task",
            "app.tasks.audio_task",
            "app.tasks.video_task",
            "app.tasks.scene_merge_task",
            "app.tasks.merge_task",
            "app.tasks.finalize_task",
        ],
    )

    # Basic config
    annotations = {"*": {"rate_limit": "10/s"}}
    if settings.MAX_RETRY_ATTEMPTS is not None:
        annotations["*"]["max_retries"] = settings.MAX_RETRY_ATTEMPTS

    config = dict(
        task_default_queue="default",
        task_ignore_result=False,
        task_annotations=annotations,
        # Broker connection retry behavior
        broker_connection_retry=settings.CELERY_BROKER_CONNECTION_RETRY,
        broker_connection_retry_on_startup=settings.CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP,
        worker_hijack_root_logger=False,
    )
    # Windows prefork support regressed on Python 3.13; fall back to solo pool.
    if sys.platform.startswith("win"):
        config.update(
            worker_pool="solo",
            worker_concurrency=1,
        )
    app.conf.update(config)
    return app


celery_app = create_celery()
