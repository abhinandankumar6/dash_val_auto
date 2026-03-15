from __future__ import annotations

from threading import Thread

from redis import Redis
from rq import Queue, Retry

from bi_validator.core.settings import get_settings


settings = get_settings()


def get_redis_connection() -> Redis:
    if settings.queue_backend != "redis":
        raise RuntimeError("Redis queue backend is disabled for this runtime.")
    return Redis.from_url(settings.redis_url)


def get_queue() -> Queue:
    return Queue(settings.queue_name, connection=get_redis_connection(), default_timeout=3600)


def queue_supports_scheduling() -> bool:
    return settings.queue_backend == "redis"


def _run_inline_validation(run_id: str, request_payload: dict) -> None:
    from bi_validator.services.queue.worker import process_validation_run

    process_validation_run(run_id, request_payload)


def enqueue_validation_run(run_id: str, request_payload: dict) -> None:
    if settings.queue_backend != "redis":
        worker = Thread(
            target=_run_inline_validation,
            args=(run_id, request_payload),
            name=f"validation-run-{run_id}",
            daemon=True,
        )
        worker.start()
        return

    queue = get_queue()
    queue.enqueue(
        "bi_validator.services.queue.worker.process_validation_run",
        run_id,
        request_payload,
        job_id=run_id,
        retry=Retry(max=2, interval=[15, 60]),
    )
