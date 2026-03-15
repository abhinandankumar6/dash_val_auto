from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog
from playwright.async_api import BrowserContext, Locator, Page, TimeoutError as PlaywrightTimeoutError, async_playwright

from bi_validator.core.settings import Settings
from bi_validator.core.utils import ensure_directory, slugify
from bi_validator.schemas.config import DashboardConfig, RuleBundle
from bi_validator.schemas.run import RunCreateRequest, RunLaunchRequest
from bi_validator.services.adapters.base import AdapterRegistry, BasePlatformAdapter
from bi_validator.services.ai.workflow import WorkflowPlanner
from bi_validator.services.automation.types import CrawlResult, DashboardState, NavigationNode, ValidationFindingRecord, VisualSnapshot
from bi_validator.services.validation.chart_rules import ChartStructureValidator
from bi_validator.services.validation.data_validator import DataConsistencyValidator
from bi_validator.services.validation.ui_validator import UIConsistencyValidator


class PlaywrightDashboardCrawler:
    def __init__(
        self,
        settings: Settings,
        adapter_registry: AdapterRegistry,
        workflow_planner: WorkflowPlanner,
        ui_validator: UIConsistencyValidator,
        chart_validator: ChartStructureValidator,
        data_validator: DataConsistencyValidator,
    ) -> None:
        self.settings = settings
        self.adapter_registry = adapter_registry
        self.workflow_planner = workflow_planner
        self.ui_validator = ui_validator
        self.chart_validator = chart_validator
        self.data_validator = data_validator
        self.logger = structlog.get_logger(__name__)

    async def crawl(
        self,
        run_id: str,
        request: RunCreateRequest | RunLaunchRequest,
        dashboard_config: DashboardConfig,
        rules: RuleBundle,
    ) -> CrawlResult:
        logs: list[dict[str, Any]] = []
        artifacts: list[dict[str, Any]] = []
        screenshot_dir = ensure_directory(Path(self.settings.screenshot_root) / run_id)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=self.settings.playwright_headless if request.headless is None else request.headless,
                slow_mo=self.settings.playwright_slow_mo_ms,
            )
            context = await browser.new_context(ignore_https_errors=True, extra_http_headers=dashboard_config.extra_headers)
            page = await context.new_page()
            await self._log(logs, "info", "opening_dashboard", url=str(request.dashboard_url))
            await page.goto(str(request.dashboard_url), wait_until="domcontentloaded", timeout=self.settings.playwright_timeout_ms)
            await self._run_login(page, dashboard_config, logs)
            adapter = await self.adapter_registry.resolve(page, dashboard_config.platform or request.platform)
            state = await adapter.capture_state(page)
            await self._log(logs, "info", "dashboard_loaded", page_title=state.title, url=state.url)
            root = NavigationNode(
                label=request.dashboard_name,
                chart_type="dashboard",
                action="open_dashboard",
                depth=0,
                path=[request.dashboard_name],
                page_title=state.title,
                target_url=state.url,
                state_hash=state.state_hash,
                screenshot_path=await self._capture_page(page, screenshot_dir, "dashboard-root"),
                metadata={"platform_adapter": adapter.platform_name},
            )
            snapshots = await adapter.collect_page_snapshots(page, dashboard_config.ignore_selectors)
            await self._log(logs, "info", "visuals_discovered", count=len(snapshots))
            workflow = await self.workflow_planner.plan(request.prompt, state, snapshots)
            root.metadata["workflow"] = workflow.to_dict()
            visited_visuals: set[tuple[str, str]] = set()
            await self._walk_page(
                current_page=page,
                adapter=adapter,
                parent_node=root,
                dashboard_config=dashboard_config,
                rules=rules,
                workflow_signatures=workflow.prioritized_signatures,
                logs=logs,
                screenshot_dir=screenshot_dir,
                visited_visuals=visited_visuals,
                state_stack=[state.state_hash],
                depth_limit=request.max_depth or rules.execution.max_depth or self.settings.navigation_max_depth,
            )
            await browser.close()
            return CrawlResult(root=root, logs=logs, artifacts=artifacts, workflow=workflow)

    async def _walk_page(
        self,
        current_page: Page,
        adapter: BasePlatformAdapter,
        parent_node: NavigationNode,
        dashboard_config: DashboardConfig,
        rules: RuleBundle,
        workflow_signatures: list[str],
        logs: list[dict[str, Any]],
        screenshot_dir: Path,
        visited_visuals: set[tuple[str, str]],
        state_stack: list[str],
        depth_limit: int,
    ) -> None:
        if parent_node.depth >= depth_limit:
            await self._log(logs, "info", "depth_limit_reached", path=parent_node.path, depth=parent_node.depth)
            return

        state = await adapter.capture_state(current_page)
        snapshots = await adapter.collect_page_snapshots(current_page, dashboard_config.ignore_selectors)
        ordered_snapshots = self._prioritize_snapshots(snapshots, workflow_signatures)

        for snapshot in ordered_snapshots:
            visit_key = (state.state_hash, snapshot.signature)
            if visit_key in visited_visuals:
                continue
            visited_visuals.add(visit_key)
            node = await self._process_snapshot(
                current_page=current_page,
                adapter=adapter,
                snapshot=snapshot,
                parent_path=parent_node.path,
                dashboard_config=dashboard_config,
                rules=rules,
                logs=logs,
                screenshot_dir=screenshot_dir,
                state_stack=state_stack,
                depth_limit=depth_limit,
                visited_visuals=visited_visuals,
                workflow_signatures=workflow_signatures,
            )
            parent_node.children.append(node)

    async def _process_snapshot(
        self,
        current_page: Page,
        adapter: BasePlatformAdapter,
        snapshot: VisualSnapshot,
        parent_path: list[str],
        dashboard_config: DashboardConfig,
        rules: RuleBundle,
        logs: list[dict[str, Any]],
        screenshot_dir: Path,
        state_stack: list[str],
        depth_limit: int,
        visited_visuals: set[tuple[str, str]],
        workflow_signatures: list[str],
    ) -> NavigationNode:
        path = parent_path + [snapshot.label]
        node = NavigationNode(
            label=snapshot.label,
            chart_type=snapshot.chart_type,
            action="inspect_visual",
            depth=len(path) - 1,
            path=path,
            page_title=current_page.url,
            target_url=current_page.url,
            snapshot=snapshot,
            metadata={"clickable": snapshot.clickable},
        )
        node.findings.extend(self.ui_validator.validate(snapshot, rules, path))
        node.findings.extend(self.chart_validator.validate(snapshot, rules, path))
        node.screenshot_path = await self._capture_visual(current_page, snapshot.dom_id, screenshot_dir, node.label)
        await self._log(logs, "info", "validating_visual", label=snapshot.label, chart_type=snapshot.chart_type, path=path)

        if not snapshot.clickable or node.depth >= depth_limit:
            return node

        before_state = await adapter.capture_state(current_page)
        interaction = await self._click_visual(current_page, snapshot.dom_id, rules.execution.click_timeout_ms)
        after_page = interaction["page"]
        after_state = await self._wait_for_state_change(after_page, adapter, before_state.state_hash)

        if not interaction["clicked"] or (after_state.state_hash == before_state.state_hash and not interaction["popup_opened"]):
            node.metadata["drilldown_opened"] = False
            return node

        node.action = "click_drilldown"
        node.metadata["drilldown_opened"] = True
        node.page_title = after_state.title
        node.target_url = after_state.url
        node.state_hash = after_state.state_hash
        await self._log(logs, "info", "drilldown_opened", label=snapshot.label, page_title=after_state.title, path=path)

        child_snapshots = await adapter.collect_page_snapshots(after_page, dashboard_config.ignore_selectors)
        node.findings.extend(self.data_validator.validate_drilldown(snapshot, child_snapshots, path, rules))

        if after_state.state_hash in state_stack:
            node.findings.append(
                ValidationFindingRecord(
                    category="navigation",
                    severity="warning",
                    code="navigation_loop_detected",
                    message=f"Skipping recursive traversal for {snapshot.label} because it revisited a previous state.",
                    path=path,
                )
            )
        else:
            await self._walk_page(
                current_page=after_page,
                adapter=adapter,
                parent_node=node,
                dashboard_config=dashboard_config,
                rules=rules,
                workflow_signatures=workflow_signatures,
                logs=logs,
                screenshot_dir=screenshot_dir,
                visited_visuals=visited_visuals,
                state_stack=[*state_stack, after_state.state_hash],
                depth_limit=depth_limit,
            )

        await self._restore_page_context(
            adapter=adapter,
            origin_page=current_page,
            active_page=after_page,
            popup_opened=interaction["popup_opened"],
            previous_state=before_state,
            dashboard_config=dashboard_config,
        )
        return node

    async def _run_login(self, page: Page, dashboard_config: DashboardConfig, logs: list[dict[str, Any]]) -> None:
        for step in dashboard_config.login_steps:
            timeout = step.timeout_ms or self.settings.playwright_timeout_ms
            value = step.value
            if step.env:
                value = __import__("os").environ.get(step.env, value)
            if step.action == "goto" and value:
                await self._log(logs, "info", "login_step_goto", target=value)
                await page.goto(value, wait_until="domcontentloaded", timeout=timeout)
            elif step.action == "fill" and step.selector and value is not None:
                await self._log(logs, "info", "login_step_fill", selector=step.selector)
                await page.locator(step.selector).fill(value, timeout=timeout)
            elif step.action == "click" and step.selector:
                await self._log(logs, "info", "login_step_click", selector=step.selector)
                await page.locator(step.selector).click(timeout=timeout)
            elif step.action == "press" and value:
                await page.keyboard.press(value)
            elif step.action == "wait_for" and step.selector:
                await page.locator(step.selector).wait_for(timeout=timeout)
            elif step.action == "sleep" and value:
                await page.wait_for_timeout(int(value))

    async def _click_visual(self, page: Page, dom_id: str, timeout_ms: int) -> dict[str, Any]:
        locator = page.locator(f'[data-bi-validator-id="{dom_id}"]').first
        popup_task = asyncio.create_task(page.context.wait_for_event("page", timeout=1500))
        try:
            await locator.scroll_into_view_if_needed(timeout=timeout_ms)
            await locator.click(timeout=timeout_ms)
            popup_page: Page | None = None
            popup_opened = False
            try:
                popup_page = await popup_task
                popup_opened = True
                await popup_page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            except Exception:
                popup_task.cancel()
            return {"clicked": True, "page": popup_page or page, "popup_opened": popup_opened}
        except PlaywrightTimeoutError:
            popup_task.cancel()
            return {"clicked": False, "page": page, "popup_opened": False}
        except Exception:
            popup_task.cancel()
            try:
                await locator.dblclick(timeout=timeout_ms)
                return {"clicked": True, "page": page, "popup_opened": False}
            except Exception:
                return {"clicked": False, "page": page, "popup_opened": False}

    async def _wait_for_state_change(self, page: Page, adapter: BasePlatformAdapter, before_hash: str) -> DashboardState:
        for _ in range(8):
            try:
                await page.wait_for_load_state("networkidle", timeout=1000)
            except Exception:
                pass
            state = await adapter.capture_state(page)
            if state.state_hash != before_hash:
                return state
            await page.wait_for_timeout(500)
        return await adapter.capture_state(page)

    async def _restore_page_context(
        self,
        adapter: BasePlatformAdapter,
        origin_page: Page,
        active_page: Page,
        popup_opened: bool,
        previous_state: DashboardState,
        dashboard_config: DashboardConfig,
    ) -> None:
        if popup_opened and active_page is not origin_page:
            await active_page.close()
            await origin_page.bring_to_front()
            return
        await adapter.backtrack(origin_page, previous_state, dashboard_config)

    async def _capture_page(self, page: Page, screenshot_dir: Path, label: str) -> str:
        filename = screenshot_dir / f"{slugify(label)}.png"
        await page.screenshot(path=str(filename), full_page=True)
        return str(filename)

    async def _capture_visual(self, page: Page, dom_id: str, screenshot_dir: Path, label: str) -> str | None:
        locator = page.locator(f'[data-bi-validator-id="{dom_id}"]').first
        filename = screenshot_dir / f"{slugify(label)}-{dom_id}.png"
        try:
            await locator.screenshot(path=str(filename))
            return str(filename)
        except Exception:
            try:
                await page.screenshot(path=str(filename), full_page=False)
                return str(filename)
            except Exception:
                return None

    async def _log(self, logs: list[dict[str, Any]], level: str, event: str, **details: Any) -> None:
        logs.append({"level": level, "event": event, "details": details})
        getattr(self.logger, level)(event, **details)

    def _prioritize_snapshots(self, snapshots: list[VisualSnapshot], prioritized_signatures: list[str]) -> list[VisualSnapshot]:
        if not prioritized_signatures:
            return snapshots
        score_map = {signature: index for index, signature in enumerate(prioritized_signatures)}
        return sorted(snapshots, key=lambda snapshot: score_map.get(snapshot.signature, len(score_map)))
