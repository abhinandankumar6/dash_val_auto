from __future__ import annotations

from math import isclose

from bi_validator.schemas.config import RuleBundle
from bi_validator.services.automation.types import ValidationFindingRecord, VisualSnapshot


class DataConsistencyValidator:
    def validate_drilldown(
        self,
        parent_snapshot: VisualSnapshot,
        child_snapshots: list[VisualSnapshot],
        path: list[str],
        rules: RuleBundle,
    ) -> list[ValidationFindingRecord]:
        if not rules.data_rules.require_child_sum_match:
            return []
        if parent_snapshot.primary_value is None:
            return [
                ValidationFindingRecord(
                    category="data",
                    severity="warning",
                    code="parent_total_missing",
                    message=f"Unable to determine a numeric parent total for {parent_snapshot.label}.",
                    path=path,
                )
            ]

        aggregate, source, evidence = self._select_child_aggregate(child_snapshots)
        if aggregate is None:
            return [
                ValidationFindingRecord(
                    category="data",
                    severity="warning",
                    code="child_totals_missing",
                    message=f"No child totals were detected after drilling into {parent_snapshot.label}.",
                    path=path,
                )
            ]

        tolerance = abs(parent_snapshot.primary_value) * (rules.data_rules.allow_variance_percent / 100)
        tolerance = max(tolerance, 10 ** (-rules.data_rules.rounding_precision))
        if not isclose(parent_snapshot.primary_value, aggregate, abs_tol=tolerance):
            return [
                ValidationFindingRecord(
                    category="data",
                    severity="error",
                    code="drilldown_total_mismatch",
                    message=f"Child totals do not match parent total for {parent_snapshot.label}.",
                    expected=str(round(parent_snapshot.primary_value, rules.data_rules.rounding_precision)),
                    actual=str(round(aggregate, rules.data_rules.rounding_precision)),
                    path=path,
                    metadata={"aggregate_source": source, "evidence": evidence},
                )
            ]
        return []

    def _select_child_aggregate(self, child_snapshots: list[VisualSnapshot]) -> tuple[float | None, str | None, dict]:
        grouped_candidates = [snapshot for snapshot in child_snapshots if len(snapshot.grouped_values) > 1]
        if grouped_candidates:
            selected = max(grouped_candidates, key=lambda item: len(item.grouped_values))
            total = sum(item.value for item in selected.grouped_values)
            return total, "grouped_values", {"label": selected.label, "groups": len(selected.grouped_values)}

        table_candidates = [snapshot for snapshot in child_snapshots if snapshot.chart_type == "table" and snapshot.grouped_values]
        if table_candidates:
            selected = max(table_candidates, key=lambda item: len(item.grouped_values))
            total = sum(item.value for item in selected.grouped_values)
            return total, "table_rows", {"label": selected.label, "groups": len(selected.grouped_values)}

        primary_values = [snapshot.primary_value for snapshot in child_snapshots if snapshot.primary_value is not None]
        if len(primary_values) > 1:
            return sum(primary_values), "child_primary_values", {"count": len(primary_values)}
        if len(primary_values) == 1:
            return primary_values[0], "single_child_metric", {"count": 1}
        return None, None, {}
