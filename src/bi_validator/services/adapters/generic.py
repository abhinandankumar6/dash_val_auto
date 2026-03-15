from __future__ import annotations

from collections.abc import Iterable

from playwright.async_api import Page

from bi_validator.core.utils import contains_date_like_token, detect_currency_symbols, extract_numeric_tokens, parse_number
from bi_validator.services.adapters.base import BasePlatformAdapter
from bi_validator.services.automation.types import GroupedValue, UIObservation, VisualSnapshot


DISCOVERY_SCRIPT = """
({ selectors, ignoreSelectors }) => {
  const matcher = window.__biValidatorMatcher = window.__biValidatorMatcher || { counter: 0 };
  const visible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width >= 80
      && rect.height >= 28
      && style.visibility !== 'hidden'
      && style.display !== 'none'
      && style.opacity !== '0';
  };
  const ignored = (el) => ignoreSelectors.some((selector) => {
    try {
      return el.matches(selector) || !!el.closest(selector);
    } catch {
      return false;
    }
  });
  const detectChartType = (el, text) => {
    const cls = ((typeof el.className === 'string' && el.className) || '').toLowerCase();
    const tag = el.tagName.toLowerCase();
    const role = (el.getAttribute('role') || '').toLowerCase();
    if (tag === 'table' || role === 'table' || role === 'grid' || el.querySelector('table, [role="table"], [role="grid"]')) return 'table';
    if (cls.includes('kpi') || cls.includes('card') || text.filter((item) => /[-+]?\\d/.test(item)).length === 1) return 'kpi_card';
    if (cls.includes('pie') || cls.includes('donut') || el.querySelector('path[d], [data-chart-type*="pie"]')) return 'pie_chart';
    if (cls.includes('line') || el.querySelector('polyline, path.line, [data-chart-type*="line"]')) return 'line_chart';
    if (cls.includes('bar') || cls.includes('column') || el.querySelector('rect, [data-chart-type*="bar"]')) return 'bar_chart';
    if ((cls.includes('series') || cls.includes('legend')) && el.querySelector('svg, canvas')) return 'multi_series_chart';
    return 'unknown';
  };
  const seen = new Set();
  const items = [];
  selectors.forEach((selector) => {
    document.querySelectorAll(selector).forEach((el) => {
      if (seen.has(el) || !visible(el) || ignored(el)) {
        return;
      }
      seen.add(el);
      if (!el.dataset.biValidatorId) {
        matcher.counter += 1;
        el.dataset.biValidatorId = `v-${matcher.counter}`;
      }
      const rect = el.getBoundingClientRect();
      const text = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || '')
        .split(/\\n+/)
        .map((item) => item.trim().replace(/\\s+/g, ' '))
        .filter(Boolean)
        .slice(0, 12);
      const style = getComputedStyle(el);
      const clickable = ['button', 'a'].includes(el.tagName.toLowerCase())
        || !!el.onclick
        || style.cursor === 'pointer'
        || ['button', 'link', 'tab', 'menuitem'].includes((el.getAttribute('role') || '').toLowerCase())
        || !!el.querySelector('a, button, [role="button"]');
      items.push({
        dom_id: el.dataset.biValidatorId,
        label: text[0] || el.getAttribute('aria-label') || el.getAttribute('title') || `Visual ${matcher.counter}`,
        chart_type: detectChartType(el, text),
        clickable,
        bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      });
    });
  });
  return items.slice(0, 80);
}
"""

VISUAL_SCRIPT = """
(domId) => {
  const el = document.querySelector(`[data-bi-validator-id="${domId}"]`);
  if (!el) return null;
  const toText = (nodes, limit = 24) => Array.from(nodes)
    .map((node) => (node.innerText || node.textContent || '').trim().replace(/\\s+/g, ' '))
    .filter(Boolean)
    .slice(0, limit);
  const rect = el.getBoundingClientRect();
  const rootStyle = getComputedStyle(el);
  const titleCandidates = toText(el.querySelectorAll('h1, h2, h3, h4, h5, [role="heading"], .title, [class*="title"]'), 4);
  const rawText = (el.innerText || el.getAttribute('aria-label') || '')
    .split(/\\n+/)
    .map((item) => item.trim().replace(/\\s+/g, ' '))
    .filter(Boolean)
    .slice(0, 30);
  const numericTexts = rawText.filter((item) => /[-+]?\\d[\\d,]*(?:\\.\\d+)?/.test(item)).slice(0, 12);
  const legendItems = toText(el.querySelectorAll('legend, .legend *, [class*="legend"] *, [aria-label*="legend" i], svg text'), 12);
  const axisLabels = toText(el.querySelectorAll('[class*="axis"] text, .tick text, [aria-label*="axis" i], [class*="tick"]'), 12);
  const headers = toText(el.querySelectorAll('th, [role="columnheader"], caption'), 12);
  const rows = Array.from(el.querySelectorAll('tr')).slice(0, 20).map((row) =>
    Array.from(row.querySelectorAll('th, td, [role="cell"], [role="gridcell"]'))
      .map((cell) => (cell.innerText || '').trim().replace(/\\s+/g, ' '))
      .filter(Boolean)
      .slice(0, 10)
  ).filter((row) => row.length > 0);
  const numericCells = Array.from(el.querySelectorAll('td, [role="cell"], [role="gridcell"]'))
    .filter((cell) => /[-+]?\\d/.test(cell.innerText || ''))
    .slice(0, 20);
  const rightAligned = numericCells.length > 0 && numericCells.every((cell) => {
    const style = getComputedStyle(cell);
    return style.textAlign === 'right' || style.justifyContent === 'flex-end';
  });
  const titleElement = el.querySelector('h1, h2, h3, h4, h5, [role="heading"], .title, [class*="title"]');
  const titleStyle = titleElement ? getComputedStyle(titleElement) : rootStyle;
  return {
    dom_id: domId,
    label: titleCandidates[0] || rawText[0] || el.getAttribute('aria-label') || domId,
    title: titleCandidates[0] || null,
    subtitle: titleCandidates[1] || null,
    raw_text: rawText,
    numeric_texts: numericTexts,
    legend_items: legendItems,
    axis_labels: axisLabels,
    column_headers: headers,
    table_rows: rows,
    bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
    font_family: titleStyle.fontFamily || rootStyle.fontFamily,
    title_font_size_px: parseFloat(titleStyle.fontSize || rootStyle.fontSize || '0'),
    title_font_weight: parseInt(titleStyle.fontWeight || rootStyle.fontWeight || '0', 10) || 0,
    padding_px: parseFloat(rootStyle.paddingTop || '0'),
    margin_px: parseFloat(rootStyle.marginTop || '0'),
    text_align: rootStyle.textAlign || null,
    numeric_column_right_aligned: rightAligned,
    gridline_count: el.querySelectorAll('.gridline, [class*="gridline"], .tick line, .y-grid line').length,
    has_percent: rawText.filter((item) => item.includes('%')),
  };
}
"""


class GenericDOMAdapter(BasePlatformAdapter):
    platform_name = "generic"
    candidate_selectors = (
        "[data-testid]",
        "[data-test]",
        "[data-automation-id]",
        "[role='button']",
        "button",
        "a",
        "svg",
        "canvas",
        "table",
        "[class*='chart']",
        "[class*='kpi']",
        "[class*='card']",
        "[onclick]",
    )

    @classmethod
    async def matches(cls, page: Page) -> bool:
        return True

    async def discover_visuals(self, page: Page, ignore_selectors: Iterable[str] | None = None) -> list[dict]:
        return await page.evaluate(
            DISCOVERY_SCRIPT,
            {
                "selectors": list(self.candidate_selectors),
                "ignoreSelectors": list(ignore_selectors or []),
            },
        )

    async def capture_visual(self, page: Page, discovery_item: dict) -> VisualSnapshot | None:
        raw = await page.evaluate(VISUAL_SCRIPT, discovery_item["dom_id"])
        if not raw:
            return None

        chart_type = discovery_item.get("chart_type") or "unknown"
        numeric_values = extract_numeric_tokens(raw["numeric_texts"])
        primary_value_text = None
        primary_value = None
        if raw["numeric_texts"]:
            scored = [(abs(parse_number(token) or 0), token) for token in raw["numeric_texts"]]
            scored.sort(reverse=True)
            primary_value_text = scored[0][1]
            primary_value = parse_number(primary_value_text)

        grouped_values = self._parse_grouped_values(raw["table_rows"])
        ui = UIObservation(
            font_family=raw["font_family"],
            title_font_size_px=raw["title_font_size_px"],
            title_font_weight=raw["title_font_weight"],
            padding_px=raw["padding_px"],
            margin_px=raw["margin_px"],
            text_align=raw["text_align"],
            numeric_column_right_aligned=raw["numeric_column_right_aligned"],
            currency_symbols=detect_currency_symbols(raw["raw_text"]),
            percent_tokens=raw["has_percent"],
            date_tokens=[token for token in raw["raw_text"] if contains_date_like_token([token])],
            legend_items=raw["legend_items"],
            axis_labels=raw["axis_labels"],
            column_headers=raw["column_headers"],
            gridline_count=raw["gridline_count"],
        )
        return VisualSnapshot(
            dom_id=discovery_item["dom_id"],
            label=raw["label"] or discovery_item["label"],
            chart_type=chart_type,
            clickable=discovery_item["clickable"],
            title=raw["title"],
            subtitle=raw["subtitle"],
            raw_text=raw["raw_text"],
            numeric_texts=raw["numeric_texts"],
            numeric_values=numeric_values,
            primary_value=primary_value,
            primary_value_text=primary_value_text,
            table_rows=raw["table_rows"],
            grouped_values=grouped_values,
            bbox=raw["bbox"],
            ui=ui,
            metadata={
                "legend_items": raw["legend_items"],
                "axis_labels": raw["axis_labels"],
                "column_headers": raw["column_headers"],
            },
        )

    def _parse_grouped_values(self, table_rows: list[list[str]]) -> list[GroupedValue]:
        grouped: list[GroupedValue] = []
        for row in table_rows:
            if len(row) < 2:
                continue
            numeric_cells = [cell for cell in row if parse_number(cell) is not None]
            if not numeric_cells:
                continue
            label = next((cell for cell in row if parse_number(cell) is None), row[0])
            raw_value = numeric_cells[-1]
            value = parse_number(raw_value)
            if value is None:
                continue
            grouped.append(GroupedValue(label=label, value=value, raw_value=raw_value))
        return grouped
