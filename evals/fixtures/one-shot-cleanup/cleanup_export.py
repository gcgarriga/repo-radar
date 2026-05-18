from __future__ import annotations

import sys
from pathlib import Path


def normalize_line(line: str) -> str:
    return " ".join(line.strip().split())


def render_handoff(raw_text: str) -> str:
    items = [normalize_line(line) for line in raw_text.splitlines()]
    visible_items = [item for item in items if item]
    return "\n".join(f"- {item}" for item in visible_items) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python cleanup_export.py <raw-export.txt>", file=sys.stderr)
        return 2
    print(render_handoff(Path(argv[1]).read_text(encoding="utf-8")), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
