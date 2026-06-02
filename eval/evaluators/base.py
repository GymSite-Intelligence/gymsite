from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EvalStatus = Literal["PASS", "WARN", "FAIL", "SKIP"]


@dataclass
class EvalResult:
    status: EvalStatus
    evaluator: str = ""
    reason: str = ""
    issues: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status in ("PASS", "SKIP")
