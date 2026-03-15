from __future__ import annotations

import enum


class RunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class FindingCategory(str, enum.Enum):
    DATA = "data"
    UI = "ui"
    NAVIGATION = "navigation"
    SYSTEM = "system"


class FindingSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
