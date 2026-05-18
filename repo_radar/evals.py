from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    id: int
    prompt: str
    expected_output: str
    expectations: list[Any]
    target_repo: Path | None
    repo_url: str | None = None
    pinned_ref: str | None = None
    label: str | None = None
