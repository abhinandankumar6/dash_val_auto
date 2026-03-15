from __future__ import annotations

from playwright.async_api import Page

from bi_validator.services.adapters.generic import GenericDOMAdapter


class TableauAdapter(GenericDOMAdapter):
    platform_name = "tableau"
    candidate_selectors = GenericDOMAdapter.candidate_selectors + (
        "[class*='tabDashboard']",
        "[class*='mark-label']",
        "[data-tb-test-id]",
    )

    @classmethod
    async def matches(cls, page: Page) -> bool:
        content = await page.content()
        return "tableau" in page.url.lower() or "tableau" in content.lower()
