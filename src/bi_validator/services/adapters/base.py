from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from playwright.async_api import Page

from bi_validator.core.utils import stable_hash
from bi_validator.schemas.config import DashboardConfig
from bi_validator.services.automation.types import DashboardState, VisualSnapshot


class BasePlatformAdapter(ABC):
    platform_name = "generic"
    candidate_selectors: tuple[str, ...] = ()

    @classmethod
    @abstractmethod
    async def matches(cls, page: Page) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def discover_visuals(self, page: Page, ignore_selectors: Iterable[str] | None = None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    async def capture_visual(self, page: Page, discovery_item: dict) -> VisualSnapshot | None:
        raise NotImplementedError

    async def collect_page_snapshots(self, page: Page, ignore_selectors: Iterable[str] | None = None) -> list[VisualSnapshot]:
        snapshots: list[VisualSnapshot] = []
        seen_signatures: set[str] = set()
        for visual in await self.discover_visuals(page, ignore_selectors):
            snapshot = await self.capture_visual(page, visual)
            if not snapshot or snapshot.signature in seen_signatures:
                continue
            seen_signatures.add(snapshot.signature)
            snapshots.append(snapshot)
        return snapshots

    async def capture_state(self, page: Page) -> DashboardState:
        state = await page.evaluate(
            """
            () => {
              const toText = (nodes) => Array.from(nodes)
                .map((node) => (node.innerText || node.textContent || '').trim().replace(/\\s+/g, ' '))
                .filter(Boolean)
                .slice(0, 10);
              const breadcrumb = toText(
                document.querySelectorAll(
                  'nav[aria-label*="breadcrumb" i] a, nav[aria-label*="breadcrumb" i] span, .breadcrumb li, .breadcrumb-item'
                )
              );
              const headings = toText(document.querySelectorAll('h1, h2, h3, [role="heading"]'));
              return {
                url: window.location.href,
                title: document.title || headings[0] || window.location.pathname,
                breadcrumb,
                headings,
              };
            }
            """
        )
        state["state_hash"] = stable_hash(state)
        return DashboardState(**state)

    async def backtrack(self, page: Page, previous_state: DashboardState, dashboard_config: DashboardConfig) -> None:
        for selector in dashboard_config.back_selectors:
            locator = page.locator(selector)
            if await locator.count():
                try:
                    await locator.first.click(timeout=1500)
                    await page.wait_for_timeout(700)
                    return
                except Exception:
                    continue
        if page.url != previous_state.url:
            try:
                await page.go_back(wait_until="domcontentloaded", timeout=3000)
                await page.wait_for_timeout(700)
                return
            except Exception:
                pass
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
        except Exception:
            return


class AdapterRegistry:
    def __init__(self, adapters: list[type[BasePlatformAdapter]]):
        self._adapters = adapters

    async def resolve(self, page: Page, requested_platform: str) -> BasePlatformAdapter:
        if requested_platform and requested_platform != "generic":
            for adapter_cls in self._adapters:
                if adapter_cls.platform_name == requested_platform:
                    return adapter_cls()
        for adapter_cls in self._adapters:
            if await adapter_cls.matches(page):
                return adapter_cls()
        return self._adapters[0]()
