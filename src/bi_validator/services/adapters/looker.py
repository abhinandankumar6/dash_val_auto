from __future__ import annotations

from playwright.async_api import Page

from bi_validator.services.adapters.generic import GenericDOMAdapter


class LookerAdapter(GenericDOMAdapter):
    platform_name = "looker"
    candidate_selectors = GenericDOMAdapter.candidate_selectors + (
        "[class*='dashboard-element']",
        "[data-testid*='dashboard-tile']",
        "[data-testid*='vis']",
    )

    @classmethod
    async def matches(cls, page: Page) -> bool:
        content = await page.content()
        lowered = f"{page.url} {content}".lower()
        return "looker" in lowered
