from __future__ import annotations

from datetime import datetime

from bi_validator.schemas.config import RuleBundle
from bi_validator.services.automation.types import ValidationFindingRecord, VisualSnapshot


class UIConsistencyValidator:
    def validate(self, snapshot: VisualSnapshot, rules: RuleBundle, path: list[str]) -> list[ValidationFindingRecord]:
        findings: list[ValidationFindingRecord] = []
        typography = rules.ui_rules.typography
        layout = rules.ui_rules.layout
        formatting = rules.ui_rules.formatting

        if typography.font_family and snapshot.ui.font_family:
            if typography.font_family.lower() not in snapshot.ui.font_family.lower():
                findings.append(
                    ValidationFindingRecord(
                        category="ui",
                        severity="error",
                        code="font_family_mismatch",
                        message=f"Expected font family containing '{typography.font_family}' for {snapshot.label}.",
                        expected=typography.font_family,
                        actual=snapshot.ui.font_family,
                        path=path,
                    )
                )

        if typography.title_font_size_px and snapshot.ui.title_font_size_px:
            if abs(snapshot.ui.title_font_size_px - typography.title_font_size_px) > 1:
                findings.append(
                    ValidationFindingRecord(
                        category="ui",
                        severity="warning",
                        code="title_font_size_mismatch",
                        message=f"Unexpected title font size for {snapshot.label}.",
                        expected=f"{typography.title_font_size_px}px",
                        actual=f"{snapshot.ui.title_font_size_px}px",
                        path=path,
                    )
                )

        if typography.title_font_weight and snapshot.ui.title_font_weight:
            if snapshot.ui.title_font_weight < typography.title_font_weight:
                findings.append(
                    ValidationFindingRecord(
                        category="ui",
                        severity="warning",
                        code="title_font_weight_mismatch",
                        message=f"Title font weight is lighter than expected for {snapshot.label}.",
                        expected=str(typography.title_font_weight),
                        actual=str(snapshot.ui.title_font_weight),
                        path=path,
                    )
                )

        if snapshot.ui.padding_px is not None and snapshot.ui.padding_px < layout.min_padding_px:
            findings.append(
                ValidationFindingRecord(
                    category="ui",
                    severity="warning",
                    code="padding_too_small",
                    message=f"Padding is below the configured minimum for {snapshot.label}.",
                    expected=f">= {layout.min_padding_px}px",
                    actual=f"{snapshot.ui.padding_px}px",
                    path=path,
                )
            )

        if snapshot.ui.margin_px is not None and snapshot.ui.margin_px > layout.max_margin_px:
            findings.append(
                ValidationFindingRecord(
                    category="ui",
                    severity="warning",
                    code="margin_too_large",
                    message=f"Margin exceeds the configured maximum for {snapshot.label}.",
                    expected=f"<= {layout.max_margin_px}px",
                    actual=f"{snapshot.ui.margin_px}px",
                    path=path,
                )
            )

        if layout.text_align_numeric and snapshot.chart_type == "table" and snapshot.ui.numeric_column_right_aligned is False:
            findings.append(
                ValidationFindingRecord(
                    category="ui",
                    severity="error",
                    code="numeric_alignment_mismatch",
                    message=f"Numeric columns are not {layout.text_align_numeric}-aligned in table {snapshot.label}.",
                    expected=layout.text_align_numeric,
                    actual="not right-aligned",
                    path=path,
                )
            )

        if snapshot.primary_value_text:
            allowed_symbols = set(formatting.currency_symbols)
            if allowed_symbols and any(symbol in snapshot.primary_value_text for symbol in ("$", "₹", "€", "£")):
                if not any(symbol in snapshot.primary_value_text for symbol in allowed_symbols):
                    findings.append(
                        ValidationFindingRecord(
                            category="ui",
                            severity="warning",
                            code="currency_symbol_mismatch",
                            message=f"Currency symbol does not match configured rules for {snapshot.label}.",
                            expected=", ".join(sorted(allowed_symbols)),
                            actual=snapshot.primary_value_text,
                            path=path,
                        )
                    )

            if "." in snapshot.primary_value_text:
                decimals = len(snapshot.primary_value_text.split(".")[-1].rstrip("%"))
                if decimals > formatting.decimal_precision:
                    findings.append(
                        ValidationFindingRecord(
                            category="ui",
                            severity="warning",
                            code="decimal_precision_mismatch",
                            message=f"Decimal precision exceeds configured limit for {snapshot.label}.",
                            expected=f"<= {formatting.decimal_precision}",
                            actual=str(decimals),
                            path=path,
                        )
                    )

        for token in snapshot.ui.date_tokens:
            if not any(self._matches_date_format(token, fmt) for fmt in formatting.accepted_date_formats):
                findings.append(
                    ValidationFindingRecord(
                        category="ui",
                        severity="warning",
                        code="date_format_mismatch",
                        message=f"Date token '{token}' does not match accepted formats.",
                        expected=", ".join(formatting.accepted_date_formats),
                        actual=token,
                        path=path,
                    )
                )
        return findings

    def _matches_date_format(self, value: str, fmt: str) -> bool:
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            return False
