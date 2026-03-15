from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from bi_validator.core.config_loader import load_dashboard_config, load_rule_bundle
from bi_validator.core.settings import Settings, get_settings
from bi_validator.core.utils import ensure_directory, utc_now
from bi_validator.models.enums import FindingCategory, FindingSeverity, RunStatus
from bi_validator.models.run import Artifact, DashboardRun, ExecutionLog, NavigationEvent, ValidationFinding
from bi_validator.schemas.config import DashboardConfig, LoginStep
from bi_validator.schemas.run import RunCreateRequest, RunLaunchRequest
from bi_validator.services.adapters.base import AdapterRegistry
from bi_validator.services.adapters.generic import GenericDOMAdapter
from bi_validator.services.adapters.looker import LookerAdapter
from bi_validator.services.adapters.powerbi import PowerBIAdapter
from bi_validator.services.adapters.tableau import TableauAdapter
from bi_validator.services.ai.workflow import WorkflowPlanner
from bi_validator.services.automation.playwright_runner import PlaywrightDashboardCrawler
from bi_validator.services.automation.types import CrawlResult, NavigationNode, ValidationFindingRecord
from bi_validator.services.reporting.report_builder import ReportBuilder
from bi_validator.services.validation.chart_rules import ChartStructureValidator
from bi_validator.services.validation.data_validator import DataConsistencyValidator
from bi_validator.services.validation.ui_validator import UIConsistencyValidator


class DashboardValidationCoordinator:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = structlog.get_logger(__name__)
        registry = AdapterRegistry([GenericDOMAdapter, TableauAdapter, PowerBIAdapter, LookerAdapter])
        self.crawler = PlaywrightDashboardCrawler(
            settings=self.settings,
            adapter_registry=registry,
            workflow_planner=WorkflowPlanner(self.settings),
            ui_validator=UIConsistencyValidator(),
            chart_validator=ChartStructureValidator(),
            data_validator=DataConsistencyValidator(),
        )
        self.report_builder = ReportBuilder()

    def create_run(self, db: Session, request: RunCreateRequest | RunLaunchRequest) -> DashboardRun:
        run = DashboardRun(
            dashboard_name=request.dashboard_name,
            dashboard_url=str(request.dashboard_url),
            platform=request.platform,
            prompt=request.prompt,
            rules_path=request.rules_path,
            dashboard_config_path=request.dashboard_config_path,
            status=RunStatus.PENDING,
            summary={},
            navigation_tree={},
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    def execute_run(self, db: Session, run_id: UUID, request: RunCreateRequest | RunLaunchRequest) -> DashboardRun:
        run = db.get(DashboardRun, run_id)
        if run is None:
            raise ValueError(f"Run {run_id} not found")
        run_uuid = run.id

        run.status = RunStatus.RUNNING
        run.started_at = utc_now()
        db.commit()
        db.refresh(run)

        rules = load_rule_bundle(request.rules_path)
        dashboard_config = self._resolve_dashboard_config(request)
        output_dir = ensure_directory(Path(self.settings.report_root) / str(run.id))
        ensure_directory(Path(self.settings.screenshot_root) / str(run.id))

        try:
            result = asyncio.run(
                self.crawler.crawl(
                    run_id=str(run.id),
                    request=request,
                    dashboard_config=dashboard_config,
                    rules=rules,
                )
            )
            summary = self._build_summary(result)
            run.status = RunStatus.FAILED if summary["failed_checks"] else RunStatus.COMPLETED
            run.summary = summary
            run.navigation_tree = result.root.to_dict()
            run.report_dir = str(output_dir)
            reports = self.report_builder.build(run, result, output_dir)
            run.summary["reports"] = reports
            self._persist_result(db, run, result)
            db.add(Artifact(run_id=run.id, kind="json_report", path=reports["json_report"], metadata_json={}))
            db.add(Artifact(run_id=run.id, kind="csv_report", path=reports["csv_report"], metadata_json={}))
            db.add(Artifact(run_id=run.id, kind="html_report", path=reports["html_report"], metadata_json={}))
            run.completed_at = utc_now()
            db.commit()
            db.refresh(run)
            return run
        except Exception as exc:
            db.rollback()
            run = db.get(DashboardRun, run_uuid)
            if run is None:
                raise
            run.status = RunStatus.FAILED
            run.error_message = str(exc)
            run.completed_at = utc_now()
            db.add(
                ExecutionLog(
                    run_id=run.id,
                    level="error",
                    event="run_failed",
                    details={"error": str(exc)},
                )
            )
            db.commit()
            db.refresh(run)
            raise

    def _resolve_dashboard_config(self, request: RunCreateRequest | RunLaunchRequest) -> DashboardConfig:
        if isinstance(request, RunLaunchRequest) and request.inline_dashboard_config:
            credentials = {key: value for key, value in request.credentials.items() if value}
            login_steps = []
            for step in request.inline_dashboard_config.login_steps:
                value = step.value
                if step.credential_key:
                    value = credentials.get(step.credential_key, value)
                login_steps.append(
                    LoginStep(
                        action=step.action,
                        selector=step.selector,
                        value=value,
                        timeout_ms=step.timeout_ms,
                    )
                )

            return DashboardConfig(
                name=request.dashboard_name,
                url=str(request.dashboard_url),
                platform=request.platform,
                login_steps=login_steps,
                back_selectors=request.inline_dashboard_config.back_selectors,
                ignore_selectors=request.inline_dashboard_config.ignore_selectors,
                target_hints=request.inline_dashboard_config.target_hints,
                extra_headers=request.inline_dashboard_config.extra_headers,
            )

        return load_dashboard_config(
            request.dashboard_config_path,
            default_name=request.dashboard_name,
            default_url=str(request.dashboard_url),
            platform=request.platform,
        )

    def _build_summary(self, result: CrawlResult) -> dict[str, Any]:
        findings = result.flatten_findings()
        severity_counts = Counter(finding.severity for finding in findings)
        category_counts = Counter(finding.category for finding in findings)
        failed_checks = severity_counts.get("error", 0) + severity_counts.get("critical", 0)
        return {
            "validation_status": "FAILED" if failed_checks else "PASSED",
            "failed_checks": failed_checks,
            "warning_checks": severity_counts.get("warning", 0),
            "info_checks": severity_counts.get("info", 0),
            "category_counts": dict(category_counts),
            "workflow": result.workflow.to_dict(),
            "navigation_nodes": self._count_nodes(result.root),
        }

    def _count_nodes(self, node: NavigationNode) -> int:
        return 1 + sum(self._count_nodes(child) for child in node.children)

    def _persist_result(self, db: Session, run: DashboardRun, result: CrawlResult) -> None:
        sequence = 0

        def persist_node(node: NavigationNode, parent_id: UUID | None = None) -> None:
            nonlocal sequence
            sequence += 1
            event = NavigationEvent(
                run_id=run.id,
                parent_id=parent_id,
                sequence=sequence,
                depth=node.depth,
                label=node.label,
                chart_type=node.chart_type,
                action=node.action,
                page_title=node.page_title,
                target_url=node.target_url,
                state_hash=node.state_hash,
                screenshot_path=node.screenshot_path,
                metadata_json=node.metadata,
            )
            db.add(event)
            db.flush()
            if node.screenshot_path:
                db.add(
                    Artifact(
                        run_id=run.id,
                        event_id=event.id,
                        kind="screenshot",
                        path=node.screenshot_path,
                        metadata_json={"path": node.path},
                    )
                )
            for finding in node.findings:
                db.add(self._to_orm_finding(run.id, event.id, finding))
            for child in node.children:
                persist_node(child, event.id)

        persist_node(result.root)
        for log_entry in result.logs:
            db.add(
                ExecutionLog(
                    run_id=run.id,
                    level=log_entry["level"],
                    event=log_entry["event"],
                    details=log_entry["details"],
                )
            )
        for artifact in result.artifacts:
            db.add(
                Artifact(
                    run_id=run.id,
                    kind=artifact["kind"],
                    path=artifact["path"],
                    metadata_json=artifact.get("metadata", {}),
                )
            )

    def _to_orm_finding(self, run_id: UUID, event_id: UUID | None, finding: ValidationFindingRecord) -> ValidationFinding:
        return ValidationFinding(
            run_id=run_id,
            event_id=event_id,
            category=FindingCategory(finding.category),
            severity=FindingSeverity(finding.severity),
            code=finding.code,
            message=finding.message,
            expected=finding.expected,
            actual=finding.actual,
            path=finding.path,
            metadata_json=finding.metadata,
        )
