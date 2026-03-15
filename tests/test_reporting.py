from pathlib import Path
from uuid import uuid4

from bi_validator.models.enums import RunStatus
from bi_validator.models.run import DashboardRun
from bi_validator.services.automation.types import CrawlResult, NavigationNode, WorkflowPlan
from bi_validator.services.reporting.report_builder import ReportBuilder


def test_report_builder_writes_all_formats(tmp_path: Path):
    run = DashboardRun(
        id=uuid4(),
        dashboard_name="Sales Overview",
        dashboard_url="https://example.com",
        platform="generic",
        status=RunStatus.COMPLETED,
        rules_path="config/rules/default_rules.yaml",
        summary={"validation_status": "PASSED", "failed_checks": 0, "navigation_nodes": 1},
        navigation_tree={},
    )
    root = NavigationNode(
        label="Sales Overview",
        chart_type="dashboard",
        action="open_dashboard",
        depth=0,
        path=["Sales Overview"],
    )
    result = CrawlResult(
        root=root,
        logs=[],
        artifacts=[],
        workflow=WorkflowPlan(source="heuristic", keywords=["sales"], prioritized_signatures=[], rationale=["test"]),
    )
    reports = ReportBuilder().build(run, result, tmp_path)
    assert Path(reports["json_report"]).exists()
    assert Path(reports["csv_report"]).exists()
    assert Path(reports["html_report"]).exists()
