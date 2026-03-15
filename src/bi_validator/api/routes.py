from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from bi_validator.db.session import get_db
from bi_validator.models.run import DashboardRun
from bi_validator.schemas.run import (
    ReportLinks,
    RunCreateRequest,
    RunDetailResponse,
    RunLaunchRequest,
    RunResponse,
    ScheduleCreateRequest,
    ScheduleResponse,
)
from bi_validator.services.dashboard_validation import DashboardValidationCoordinator
from bi_validator.services.queue.redis_queue import enqueue_validation_run, queue_supports_scheduling
from bi_validator.services.queue.scheduler import schedule_validation_run


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/validation-runs", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
def create_validation_run(payload: RunCreateRequest, db: Session = Depends(get_db)) -> RunResponse:
    coordinator = DashboardValidationCoordinator()
    run = coordinator.create_run(db, payload)
    enqueue_validation_run(str(run.id), payload.model_dump(mode="json"))
    return RunResponse.model_validate(run, from_attributes=True)


@router.post("/validation-schedules", response_model=ScheduleResponse, status_code=status.HTTP_202_ACCEPTED)
def create_validation_schedule(payload: ScheduleCreateRequest) -> ScheduleResponse:
    if not queue_supports_scheduling():
        raise HTTPException(
            status_code=501,
            detail="Scheduled jobs require Redis queue mode. Standalone builds run validations inline.",
        )
    result = schedule_validation_run(payload.model_dump(mode="json", exclude={"cron"}), payload.cron)
    return ScheduleResponse.model_validate(result)


@router.post("/validation-runs/direct", response_model=RunDetailResponse)
def execute_validation_run_direct(payload: RunCreateRequest, db: Session = Depends(get_db)) -> RunDetailResponse:
    coordinator = DashboardValidationCoordinator()
    run = coordinator.create_run(db, payload)
    run = coordinator.execute_run(db, run.id, payload)
    return RunDetailResponse.model_validate(run, from_attributes=True)


@router.post("/validation-runs/launch", response_model=RunDetailResponse)
def execute_validation_run_launch(payload: RunLaunchRequest, db: Session = Depends(get_db)) -> RunDetailResponse:
    coordinator = DashboardValidationCoordinator()
    run = coordinator.create_run(db, payload)
    run = coordinator.execute_run(db, run.id, payload)
    return RunDetailResponse.model_validate(run, from_attributes=True)


@router.get("/validation-runs", response_model=list[RunResponse])
def list_validation_runs(db: Session = Depends(get_db)) -> list[RunResponse]:
    runs = db.query(DashboardRun).order_by(DashboardRun.created_at.desc()).limit(50).all()
    return [RunResponse.model_validate(run, from_attributes=True) for run in runs]


@router.get("/validation-runs/{run_id}", response_model=RunDetailResponse)
def get_validation_run(run_id: UUID, db: Session = Depends(get_db)) -> RunDetailResponse:
    run = db.get(DashboardRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunDetailResponse.model_validate(run, from_attributes=True)


@router.get("/validation-runs/{run_id}/reports", response_model=ReportLinks)
def get_validation_run_reports(run_id: UUID, db: Session = Depends(get_db)) -> ReportLinks:
    run = db.get(DashboardRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    reports = run.summary.get("reports", {})
    if not reports:
        raise HTTPException(status_code=404, detail="Reports not available yet")
    return ReportLinks.model_validate(reports)


@router.get("/validation-runs/{run_id}/reports/{report_type}")
def download_validation_run_report(report_type: str, run_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    run = db.get(DashboardRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run.report_dir:
        raise HTTPException(status_code=404, detail="Reports not available yet")

    name_map = {"html": "report.html", "json": "report.json", "csv": "report.csv"}
    filename = name_map.get(report_type.lower())
    if filename is None:
        raise HTTPException(status_code=404, detail="Unsupported report type")
    path = Path(run.report_dir) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    media_type = {"html": "text/html", "json": "application/json", "csv": "text/csv"}[report_type.lower()]
    if report_type.lower() == "html":
        return FileResponse(path, media_type=media_type)
    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/validation-runs/{run_id}/screenshots/{filename}")
def download_validation_screenshot(filename: str, run_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    run = db.get(DashboardRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    screenshot_path = Path(DashboardValidationCoordinator().settings.screenshot_root) / str(run_id) / filename
    if not screenshot_path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(screenshot_path, media_type="image/png", filename=filename)
