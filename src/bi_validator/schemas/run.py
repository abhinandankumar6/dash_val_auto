from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from bi_validator.models.enums import RunStatus


class RunCreateRequest(BaseModel):
    dashboard_name: str = Field(..., description="Human-friendly dashboard name.")
    dashboard_url: HttpUrl
    platform: str = "generic"
    prompt: str | None = None
    rules_path: str = "config/rules/default_rules.yaml"
    dashboard_config_path: str | None = None
    headless: bool | None = None
    max_depth: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LaunchLoginStep(BaseModel):
    action: Literal["goto", "fill", "click", "press", "wait_for", "sleep"]
    selector: str | None = None
    value: str | None = None
    credential_key: str | None = None
    timeout_ms: int | None = None


class InlineDashboardConfigInput(BaseModel):
    login_steps: list[LaunchLoginStep] = Field(default_factory=list)
    back_selectors: list[str] = Field(default_factory=list)
    ignore_selectors: list[str] = Field(default_factory=list)
    target_hints: list[str] = Field(default_factory=list)
    extra_headers: dict[str, str] = Field(default_factory=dict)


class RunLaunchRequest(BaseModel):
    dashboard_name: str = Field(..., description="Human-friendly dashboard name.")
    dashboard_url: HttpUrl
    platform: str = "generic"
    prompt: str | None = None
    rules_path: str = "config/rules/default_rules.yaml"
    dashboard_config_path: str | None = None
    headless: bool | None = None
    max_depth: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    inline_dashboard_config: InlineDashboardConfigInput | None = None
    credentials: dict[str, str] = Field(default_factory=dict, repr=False)


class RunResponse(BaseModel):
    id: UUID
    dashboard_name: str
    platform: str
    status: RunStatus
    created_at: datetime


class RunDetailResponse(RunResponse):
    dashboard_url: str
    prompt: str | None = None
    rules_path: str
    dashboard_config_path: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    navigation_tree: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    report_dir: str | None = None


class ReportLinks(BaseModel):
    json_report: str
    csv_report: str
    html_report: str


class ScheduleCreateRequest(RunCreateRequest):
    cron: str = Field(..., description="Cron expression for recurring dashboard validation.")


class ScheduleResponse(BaseModel):
    schedule_id: str
    cron: str
