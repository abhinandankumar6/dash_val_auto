from bi_validator.schemas.config import RuleBundle
from bi_validator.services.automation.types import GroupedValue, UIObservation, VisualSnapshot
from bi_validator.services.validation.chart_rules import ChartStructureValidator
from bi_validator.services.validation.data_validator import DataConsistencyValidator
from bi_validator.services.validation.ui_validator import UIConsistencyValidator


def make_snapshot(**overrides):
    base = VisualSnapshot(
        dom_id="v-1",
        label="Revenue KPI",
        chart_type="kpi_card",
        clickable=True,
        title="Revenue KPI",
        subtitle=None,
        raw_text=["Revenue KPI", "$1,000.00"],
        numeric_texts=["$1,000.00"],
        numeric_values=[1000.0],
        primary_value=1000.0,
        primary_value_text="$1,000.00",
        table_rows=[],
        grouped_values=[],
        bbox={"x": 0.0, "y": 0.0, "width": 300.0, "height": 120.0},
        ui=UIObservation(
            font_family="Inter",
            title_font_size_px=16,
            title_font_weight=600,
            padding_px=12,
            margin_px=12,
            text_align="left",
            numeric_column_right_aligned=True,
            currency_symbols=["$"],
            percent_tokens=[],
            date_tokens=[],
            legend_items=[],
            axis_labels=[],
            column_headers=[],
            gridline_count=0,
        ),
        metadata={},
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_data_validator_detects_mismatch():
    parent = make_snapshot()
    child = make_snapshot(
        dom_id="v-2",
        label="Region Table",
        chart_type="table",
        title="Region Table",
        primary_value=None,
        primary_value_text=None,
        numeric_texts=[],
        numeric_values=[],
        table_rows=[["East", "$400.00"], ["West", "$500.00"]],
        grouped_values=[
            GroupedValue(label="East", value=400.0, raw_value="$400.00"),
            GroupedValue(label="West", value=500.0, raw_value="$500.00"),
        ],
        ui=UIObservation(
            font_family="Inter",
            title_font_size_px=16,
            title_font_weight=600,
            padding_px=12,
            margin_px=12,
            text_align="left",
            numeric_column_right_aligned=True,
            currency_symbols=["$"],
            percent_tokens=[],
            date_tokens=[],
            legend_items=[],
            axis_labels=[],
            column_headers=["Region", "Revenue"],
            gridline_count=0,
        ),
    )
    findings = DataConsistencyValidator().validate_drilldown(parent, [child], ["Dashboard", "Revenue KPI"], RuleBundle())
    assert findings
    assert findings[0].code == "drilldown_total_mismatch"


def test_ui_validator_flags_wrong_font():
    snapshot = make_snapshot()
    snapshot.ui.font_family = "Arial"
    findings = UIConsistencyValidator().validate(snapshot, RuleBundle(), ["Dashboard", "Revenue KPI"])
    assert any(finding.code == "font_family_mismatch" for finding in findings)


def test_chart_validator_requires_headers_for_table():
    snapshot = make_snapshot(
        chart_type="table",
        table_rows=[["East", "100"]],
        grouped_values=[GroupedValue(label="East", value=100.0, raw_value="100")],
        ui=UIObservation(
            font_family="Inter",
            title_font_size_px=16,
            title_font_weight=600,
            padding_px=12,
            margin_px=12,
            text_align="left",
            numeric_column_right_aligned=False,
            currency_symbols=[],
            percent_tokens=[],
            date_tokens=[],
            legend_items=[],
            axis_labels=[],
            column_headers=[],
            gridline_count=0,
        ),
    )
    findings = ChartStructureValidator().validate(snapshot, RuleBundle(), ["Dashboard", "Table"])
    assert any(finding.code == "missing_table_headers" for finding in findings)
