"""Plain data structures shared across the package."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        """Higher rank = worse. Lets us find the overall status with max()."""
        return {Status.OK: 0, Status.WARNING: 1, Status.CRITICAL: 2}[self]


@dataclass(frozen=True)
class CheckResult:
    """The outcome of evaluating one rule against one piece of collected data."""
    name: str
    status: Status
    detail: str

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status.value, "detail": self.detail}
