from __future__ import annotations

import csv
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from bi_validator.core.utils import ensure_directory
from bi_validator.models.run import DashboardRun
from bi_validator.services.automation.types import CrawlResult, NavigationNode, ValidationFindingRecord


class ReportBuilder:
    def __init__(self) -> None:
        template_root = Path(__file__).resolve().parents[2] / "templates"
        self.environment = Environment(
            loader=FileSystemLoader(template_root),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def build(self, run: DashboardRun, result: CrawlResult, output_dir: Path) -> dict[str, str]:
        ensure_directory(output_dir)
        report_json = output_dir / "report.json"
        report_csv = output_dir / "report.csv"
        report_html = output_dir / "report.html"

        findings = [finding.to_dict() for finding in result.flatten_findings()]
        payload = {
            "dashboard": run.dashboard_name,
            "status": run.summary.get("validation_status", "UNKNOWN"),
            "platform": run.platform,
            "summary": run.summary,
            "workflow": result.workflow.to_dict(),
            "navigation_tree": result.root.to_dict(),
            "findings": findings,
        }
        report_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._write_csv(report_csv, result.flatten_findings())
        self._write_html(report_html, payload, result.root, str(run.id))
        return {
            "json_report": str(report_json),
            "csv_report": str(report_csv),
            "html_report": str(report_html),
        }

    def _write_csv(self, path: Path, findings: list[ValidationFindingRecord]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["category", "severity", "code", "message", "expected", "actual", "path"],
            )
            writer.writeheader()
            for finding in findings:
                writer.writerow(
                    {
                        "category": finding.category,
                        "severity": finding.severity,
                        "code": finding.code,
                        "message": finding.message,
                        "expected": finding.expected,
                        "actual": finding.actual,
                        "path": " -> ".join(finding.path),
                    }
                )

    def _write_html(self, path: Path, payload: dict, root: NavigationNode, run_id: str) -> None:
        template = self.environment.get_template("report.html.j2")
        html = template.render(
            payload=payload,
            navigation_html=self._render_navigation_html(root, run_id),
        )
        path.write_text(html, encoding="utf-8")

    def _render_navigation_html(self, node: NavigationNode, run_id: str) -> str:
        findings = "".join(
            f"<li><strong>{finding.severity.upper()}</strong> {finding.message}</li>" for finding in node.findings
        )
        children = "".join(self._render_navigation_html(child, run_id) for child in node.children)
        findings_block = f"<ul class='findings'>{findings}</ul>" if findings else ""
        children_block = f"<ul>{children}</ul>" if children else ""
        screenshot = (
            f'<div class="shot"><a href="/api/v1/validation-runs/{run_id}/screenshots/{Path(node.screenshot_path).name}">Screenshot</a></div>'
            if node.screenshot_path
            else ""
        )
        return (
            "<li>"
            f"<div><strong>{node.label}</strong> <span>({node.chart_type})</span></div>"
            f"<div class='meta'>{' -> '.join(node.path)}</div>"
            f"{screenshot}"
            f"{findings_block}"
            f"{children_block}"
            "</li>"
        )
