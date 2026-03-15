from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class UIObservation:
    font_family: str | None = None
    title_font_size_px: float | None = None
    title_font_weight: int | None = None
    padding_px: float | None = None
    margin_px: float | None = None
    text_align: str | None = None
    numeric_column_right_aligned: bool | None = None
    currency_symbols: list[str] = field(default_factory=list)
    percent_tokens: list[str] = field(default_factory=list)
    date_tokens: list[str] = field(default_factory=list)
    legend_items: list[str] = field(default_factory=list)
    axis_labels: list[str] = field(default_factory=list)
    column_headers: list[str] = field(default_factory=list)
    gridline_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GroupedValue:
    label: str
    value: float
    raw_value: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VisualSnapshot:
    dom_id: str
    label: str
    chart_type: str
    clickable: bool
    title: str | None
    subtitle: str | None
    raw_text: list[str]
    numeric_texts: list[str]
    numeric_values: list[float]
    primary_value: float | None
    primary_value_text: str | None
    table_rows: list[list[str]]
    grouped_values: list[GroupedValue]
    bbox: dict[str, float]
    ui: UIObservation
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def signature(self) -> str:
        return "|".join(
            [
                self.chart_type,
                self.label.lower(),
                str(round(self.bbox.get("x", 0), 0)),
                str(round(self.bbox.get("y", 0), 0)),
                str(round(self.bbox.get("width", 0), 0)),
                str(round(self.bbox.get("height", 0), 0)),
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["grouped_values"] = [value.to_dict() for value in self.grouped_values]
        payload["ui"] = self.ui.to_dict()
        return payload


@dataclass(slots=True)
class DashboardState:
    url: str
    title: str
    breadcrumb: list[str]
    headings: list[str]
    state_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationFindingRecord:
    category: str
    severity: str
    code: str
    message: str
    path: list[str]
    expected: str | None = None
    actual: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NavigationNode:
    label: str
    chart_type: str
    action: str
    depth: int
    path: list[str]
    page_title: str | None = None
    target_url: str | None = None
    state_hash: str | None = None
    screenshot_path: str | None = None
    snapshot: VisualSnapshot | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    findings: list[ValidationFindingRecord] = field(default_factory=list)
    children: list["NavigationNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "chart_type": self.chart_type,
            "action": self.action,
            "depth": self.depth,
            "path": self.path,
            "page_title": self.page_title,
            "target_url": self.target_url,
            "state_hash": self.state_hash,
            "screenshot_path": self.screenshot_path,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "metadata": self.metadata,
            "findings": [finding.to_dict() for finding in self.findings],
            "children": [child.to_dict() for child in self.children],
        }


@dataclass(slots=True)
class WorkflowPlan:
    source: str
    keywords: list[str]
    prioritized_signatures: list[str]
    rationale: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CrawlResult:
    root: NavigationNode
    logs: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    workflow: WorkflowPlan

    def flatten_findings(self) -> list[ValidationFindingRecord]:
        findings: list[ValidationFindingRecord] = []

        def _walk(node: NavigationNode) -> None:
            findings.extend(node.findings)
            for child in node.children:
                _walk(child)

        _walk(self.root)
        return findings
