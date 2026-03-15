from __future__ import annotations

import os
import sys
from pathlib import Path

from platformdirs import user_data_dir

from bi_validator.core.utils import ensure_directory


APP_DIR_NAME = "bi-dashboard-validator"


def is_frozen_bundle() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def bundle_root() -> Path:
    if is_frozen_bundle():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[3]


def executable_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def resolve_existing_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute() and candidate.exists():
        return candidate

    search_roots = [Path.cwd(), executable_root(), bundle_root()]
    for root in search_roots:
        resolved = (root / candidate).resolve()
        if resolved.exists():
            return resolved

    return candidate.resolve()


def app_data_root() -> Path:
    override = os.environ.get("BI_VALIDATOR_HOME")
    if override:
        return ensure_directory(Path(override).expanduser())
    return ensure_directory(Path(user_data_dir(APP_DIR_NAME, "Codex")).expanduser())


def bundled_playwright_browsers_path() -> Path | None:
    candidates = [
        bundle_root() / ".playwright-browsers",
        bundle_root() / "playwright" / "driver" / "package" / ".local-browsers",
        bundle_root() / ".local-browsers",
        executable_root() / ".playwright-browsers",
        executable_root() / "playwright" / "driver" / "package" / ".local-browsers",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
