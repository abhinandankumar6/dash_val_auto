from __future__ import annotations

from rq_scheduler import Scheduler

from bi_validator.core.settings import get_settings
from bi_validator.services.queue.redis_queue import get_redis_connection


settings = get_settings()


def get_scheduler() -> Scheduler:
    return Scheduler(queue_name=settings.queue_name, connection=get_redis_connection())


def schedule_validation_run(request_payload: dict, cron: str) -> dict[str, str]:
    scheduler = get_scheduler()
    job = scheduler.cron(
        cron_string=cron,
        func="bi_validator.services.queue.worker.process_scheduled_validation",
        args=[request_payload],
        queue_name=settings.queue_name,
        use_local_timezone=True,
    )
    return {"schedule_id": job.id, "cron": cron}


def main() -> None:
    scheduler = get_scheduler()
    scheduler.run()


if __name__ == "__main__":
    main()
