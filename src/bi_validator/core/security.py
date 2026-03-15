from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "authorization"}


def redact_sensitive(data: Mapping[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}

    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if any(marker in key.lower() for marker in SENSITIVE_KEYS):
            redacted[key] = "***"
        elif isinstance(value, Mapping):
            redacted[key] = redact_sensitive(value)
        else:
            redacted[key] = value
    return redacted
