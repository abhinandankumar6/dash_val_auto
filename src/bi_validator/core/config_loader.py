from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

from bi_validator.core.runtime import resolve_existing_path
from bi_validator.schemas.config import DashboardConfig, RuleBundle

T = TypeVar("T", bound=BaseModel)


def _load_yaml(path: str | Path) -> dict:
    file_path = resolve_existing_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_model(path: str | Path, model_cls: type[T]) -> T:
    return model_cls.model_validate(_load_yaml(path))


def load_rule_bundle(path: str | Path) -> RuleBundle:
    return load_model(path, RuleBundle)


def load_dashboard_config(path: str | Path | None, default_name: str, default_url: str, platform: str) -> DashboardConfig:
    if not path:
        return DashboardConfig(name=default_name, url=default_url, platform=platform)

    raw = _load_yaml(path)
    raw.setdefault("name", default_name)
    raw.setdefault("url", default_url)
    raw.setdefault("platform", platform)
    return DashboardConfig.model_validate(raw)
