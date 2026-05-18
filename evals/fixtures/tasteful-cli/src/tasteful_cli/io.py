from __future__ import annotations

import json
from pathlib import Path

from tasteful_cli.domain import Event, parse_event


def read_events(path: Path) -> list[Event]:
    return [parse_event(line) for line in path.read_text().splitlines() if line.strip()]


def write_summary(path: Path, summary: dict[str, int]) -> None:
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
