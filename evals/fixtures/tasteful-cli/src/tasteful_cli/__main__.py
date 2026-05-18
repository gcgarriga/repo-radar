from __future__ import annotations

import argparse
from pathlib import Path

from tasteful_cli.domain import summarize
from tasteful_cli.io import read_events, write_summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    write_summary(args.output, summarize(read_events(args.input)))


if __name__ == "__main__":
    main()
