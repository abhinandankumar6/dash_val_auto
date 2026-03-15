from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class TypographyRules(BaseModel):
    font_family: str | None = "Inter"
    title_font_size_px: float | None = 16
    title_font_weight: int | None = 600
    value_font_weight: int | None = 700


class LayoutRules(BaseModel):
    min_padding_px: float = 8
    max_margin_px: float = 32
    text_align_numeric: str | None = "right"


class FormattingRules(BaseModel):
    currency_symbols: list[str] = Field(default_factory=lambda: ["$"])
    decimal_precision: int = 2
    thousand_separator: str = ","
    accepted_date_formats: list[str] = Field(default_factory=lambda: ["%Y-%m-%d"])


class UIRules(BaseModel):
    typography: TypographyRules = Field(default_factory=TypographyRules)
    layout: LayoutRules = Field(default_factory=LayoutRules)
    formatting: FormattingRules = Field(default_factory=FormattingRules)


class ChartRuleConfig(BaseModel):
    require_title: bool = True
    require_axis_labels: bool = False
    require_legend: bool = False
    require_legend_if_multi_series: bool = False
    require_headers: bool = False
    numeric_right_aligned: bool = False
    require_gridlines: bool = False


class DataRules(BaseModel):
    rounding_precision: int = 2
    allow_variance_percent: float = 0.1
    require_child_sum_match: bool = True


class ExecutionRules(BaseModel):
    max_depth: int = 4
    retry_attempts: int = 2
    click_timeout_ms: int = 15000


class RuleBundle(BaseModel):
    ui_rules: UIRules = Field(default_factory=UIRules)
    data_rules: DataRules = Field(default_factory=DataRules)
    chart_rules: dict[str, ChartRuleConfig] = Field(
        default_factory=lambda: {
            "kpi_card": ChartRuleConfig(require_title=True),
            "table": ChartRuleConfig(require_title=True, require_headers=True, numeric_right_aligned=True),
            "bar_chart": ChartRuleConfig(require_title=True, require_axis_labels=True, require_legend_if_multi_series=True),
            "line_chart": ChartRuleConfig(require_title=True, require_axis_labels=True, require_legend_if_multi_series=True),
            "pie_chart": ChartRuleConfig(require_title=True, require_legend=True),
            "multi_series_chart": ChartRuleConfig(
                require_title=True,
                require_axis_labels=True,
                require_legend=True,
            ),
            "unknown": ChartRuleConfig(require_title=False),
        }
    )
    execution: ExecutionRules = Field(default_factory=ExecutionRules)


class LoginStep(BaseModel):
    action: Literal["goto", "fill", "click", "press", "wait_for", "sleep"]
    selector: str | None = None
    value: str | None = None
    env: str | None = None
    timeout_ms: int | None = None


class DashboardConfig(BaseModel):
    name: str
    url: str
    platform: str = "generic"
    login_steps: list[LoginStep] = Field(default_factory=list)
    back_selectors: list[str] = Field(default_factory=list)
    ignore_selectors: list[str] = Field(default_factory=list)
    target_hints: list[str] = Field(default_factory=list)
    extra_headers: dict[str, str] = Field(default_factory=dict)
