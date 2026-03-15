from __future__ import annotations

import json
import re
from collections.abc import Iterable

from openai import AsyncOpenAI

from bi_validator.core.settings import Settings
from bi_validator.services.automation.types import DashboardState, VisualSnapshot, WorkflowPlan


STOPWORDS = {
    "the",
    "and",
    "that",
    "with",
    "from",
    "into",
    "verify",
    "validate",
    "dashboard",
    "drilldowns",
    "drilldown",
    "totals",
    "match",
}


class WorkflowPlanner:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def plan(
        self,
        prompt: str | None,
        state: DashboardState,
        snapshots: list[VisualSnapshot],
    ) -> WorkflowPlan:
        if prompt and self.settings.llm_provider == "openai" and self.settings.openai_api_key:
            try:
                return await self._generate_with_openai(prompt, state, snapshots)
            except Exception:
                pass
        return self._generate_heuristic(prompt, state, snapshots)

    def _generate_heuristic(
        self,
        prompt: str | None,
        state: DashboardState,
        snapshots: list[VisualSnapshot],
    ) -> WorkflowPlan:
        keywords = self._extract_keywords(prompt or "")
        scored = sorted(
            snapshots,
            key=lambda snapshot: self._score_snapshot(snapshot, keywords),
            reverse=True,
        )
        rationale = [
            f"Prioritized visuals matching keywords: {', '.join(keywords)}" if keywords else "No prompt keywords supplied; using DOM order.",
            f"Page title: {state.title}",
        ]
        prioritized = [snapshot.signature for snapshot in scored]
        return WorkflowPlan(source="heuristic", keywords=keywords, prioritized_signatures=prioritized, rationale=rationale)

    async def _generate_with_openai(
        self,
        prompt: str,
        state: DashboardState,
        snapshots: list[VisualSnapshot],
    ) -> WorkflowPlan:
        client = AsyncOpenAI(api_key=self.settings.openai_api_key, base_url=self.settings.llm_base_url or None)
        summary = [
            {
                "label": snapshot.label,
                "chart_type": snapshot.chart_type,
                "primary_value": snapshot.primary_value,
                "signature": snapshot.signature,
            }
            for snapshot in snapshots[:25]
        ]
        response = await client.responses.create(
            model=self.settings.llm_model,
            temperature=0,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are planning a BI dashboard validation workflow. "
                        "Return JSON with keys: keywords, prioritized_signatures, rationale."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": prompt,
                            "page_title": state.title,
                            "visuals": summary,
                        }
                    ),
                },
            ],
        )
        payload = json.loads(response.output_text)
        return WorkflowPlan(
            source="openai",
            keywords=payload.get("keywords", []),
            prioritized_signatures=payload.get("prioritized_signatures", []),
            rationale=payload.get("rationale", []),
        )

    def _extract_keywords(self, prompt: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z0-9]+", prompt.lower())
        return [token for token in tokens if token not in STOPWORDS and len(token) > 2][:10]

    def _score_snapshot(self, snapshot: VisualSnapshot, keywords: Iterable[str]) -> int:
        haystack = " ".join([snapshot.label, snapshot.title or "", " ".join(snapshot.raw_text)]).lower()
        score = 0
        for keyword in keywords:
            if keyword in haystack:
                score += 3
            if snapshot.chart_type.replace("_", " ") in keyword:
                score += 1
        if snapshot.clickable:
            score += 1
        return score
