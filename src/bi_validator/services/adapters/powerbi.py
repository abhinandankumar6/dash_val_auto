from __future__ import annotations

from playwright.async_api import Page

from bi_validator.services.adapters.generic import GenericDOMAdapter


class PowerBIAdapter(GenericDOMAdapter):
    platform_name = "powerbi"
    candidate_selectors = GenericDOMAdapter.candidate_selectors + (
        "[class*='visual-container']",
        "[class*='cardContainer']",
        "[class*='pivotTable']",
    )

    @classmethod
    async def matches(cls, page: Page) -> bool:
        content = await page.content()
        lowered = f"{page.url} {content}".lower()
        return "powerbi" in lowered
