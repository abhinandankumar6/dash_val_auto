from __future__ import annotations

from uuid import UUID

from redis import Redis
from rq import Worker

from bi_validator.core.settings import get_settings
from bi_validator.db.session import SessionLocal
from bi_validator.schemas.run import RunCreateRequest
from bi_validator.services.dashboard_validation import DashboardValidationCoordinator


settings = get_settings()


def process_validation_run(run_id: str, request_payload: dict) -> dict[str, str]:
    db = SessionLocal()
    try:
        coordinator = DashboardValidationCoordinator(settings)
        request = RunCreateRequest.model_validate(request_payload)
        run = coordinator.execute_run(db, run_id=UUID(run_id), request=request)
        return {"run_id": str(run.id), "status": run.status.value}
    finally:
        db.close()


def process_scheduled_validation(request_payload: dict) -> dict[str, str]:
    db = SessionLocal()
    try:
        coordinator = DashboardValidationCoordinator(settings)
        request = RunCreateRequest.model_validate(request_payload)
        run = coordinator.create_run(db, request)
        run = coordinator.execute_run(db, run_id=run.id, request=request)
        return {"run_id": str(run.id), "status": run.status.value}
    finally:
        db.close()


def main() -> None:
    redis_connection = Redis.from_url(settings.redis_url)
    worker = Worker([settings.queue_name], connection=redis_connection)
    worker.work()


if __name__ == "__main__":
    main()
