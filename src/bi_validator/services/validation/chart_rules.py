from __future__ import annotations

from bi_validator.schemas.config import RuleBundle
from bi_validator.services.automation.types import ValidationFindingRecord, VisualSnapshot


class ChartStructureValidator:
    def validate(self, snapshot: VisualSnapshot, rules: RuleBundle, path: list[str]) -> list[ValidationFindingRecord]:
        findings: list[ValidationFindingRecord] = []
        rule = rules.chart_rules.get(snapshot.chart_type, rules.chart_rules.get("unknown"))
        if not rule:
            return findings

        if rule.require_title and not snapshot.title:
            findings.append(
                ValidationFindingRecord(
                    category="ui",
                    severity="error",
                    code="missing_title",
                    message=f"{snapshot.chart_type} is missing a visible title.",
                    path=path,
                )
            )

        if rule.require_axis_labels and not snapshot.ui.axis_labels:
            findings.append(
                ValidationFindingRecord(
                    category="ui",
                    severity="error",
                    code="missing_axis_labels",
                    message=f"{snapshot.label} is missing axis labels.",
                    path=path,
                )
            )

        if rule.require_legend and not snapshot.ui.legend_items:
            findings.append(
                ValidationFindingRecord(
                    category="ui",
                    severity="error",
                    code="missing_legend",
                    message=f"{snapshot.label} is missing a legend.",
                    path=path,
                )
            )

        if rule.require_legend_if_multi_series and len(snapshot.ui.legend_items) <= 1 and snapshot.chart_type in {"bar_chart", "line_chart", "multi_series_chart"}:
            findings.append(
                ValidationFindingRecord(
                    category="ui",
                    severity="warning",
                    code="legend_missing_for_multiseries",
                    message=f"{snapshot.label} appears to be multi-series without a clear legend.",
                    path=path,
                )
            )

        if rule.require_headers and not snapshot.ui.column_headers:
            findings.append(
                ValidationFindingRecord(
                    category="ui",
                    severity="error",
                    code="missing_table_headers",
                    message=f"Table {snapshot.label} is missing column headers.",
                    path=path,
                )
            )

        if rule.numeric_right_aligned and snapshot.ui.numeric_column_right_aligned is False:
            findings.append(
                ValidationFindingRecord(
                    category="ui",
                    severity="error",
                    code="numeric_columns_not_right_aligned",
                    message=f"Table {snapshot.label} has numeric values that are not right-aligned.",
                    path=path,
                )
            )

        if rule.require_gridlines and snapshot.ui.gridline_count == 0:
            findings.append(
                ValidationFindingRecord(
                    category="ui",
                    severity="warning",
                    code="missing_gridlines",
                    message=f"{snapshot.label} is missing expected gridlines.",
                    path=path,
                )
            )
        return findings
