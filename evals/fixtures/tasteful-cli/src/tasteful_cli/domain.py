from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    kind: str
    value: int


def parse_event(line: str) -> Event:
    kind, raw_value = line.strip().split(",", maxsplit=1)
    return Event(kind=kind, value=int(raw_value))


def summarize(events: list[Event]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for event in events:
        totals[event.kind] = totals.get(event.kind, 0) + event.value
    return totals
