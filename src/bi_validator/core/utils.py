from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


NUMBER_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
DATE_TOKEN_RE = re.compile(r"\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b")


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_number(raw: str | None) -> float | None:
    if not raw:
        return None

    candidate = raw.strip().replace("(", "-").replace(")", "")
    match = NUMBER_RE.search(candidate)
    if not match:
        return None

    number = match.group(0).replace(",", "")
    try:
        return float(number)
    except ValueError:
        return None


def extract_numeric_tokens(values: list[str]) -> list[float]:
    parsed = [parse_number(value) for value in values]
    return [value for value in parsed if value is not None]


def detect_currency_symbols(values: list[str]) -> list[str]:
    symbols = []
    for value in values:
        for symbol in ("$", "₹", "€", "£"):
            if symbol in value and symbol not in symbols:
                symbols.append(symbol)
    return symbols


def contains_date_like_token(values: list[str]) -> bool:
    return any(DATE_TOKEN_RE.search(value) for value in values)


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return normalized.strip("-") or "item"
