from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from repo_radar.cli_args import non_negative_int
from repo_radar.copilot_cli import (
    STATIC_REVIEW_SAFETY,
    ReviewRun,
    WrapperError,
    run_review,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Repo Radar against a local repository through Copilot CLI.",
        epilog=STATIC_REVIEW_SAFETY,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target_repo", type=Path)
    parser.add_argument("--output", type=Path, default=Path("repo-radar-report.md"))
    parser.add_argument(
        "--copilot-bin", default=os.environ.get("REPO_RADAR_COPILOT_BIN", "copilot")
    )
    parser.add_argument("--model", default=os.environ.get("REPO_RADAR_COPILOT_MODEL"))
    parser.add_argument(
        "--reasoning-effort",
        default=os.environ.get("REPO_RADAR_COPILOT_REASONING_EFFORT"),
    )
    parser.add_argument("--timeout-seconds", type=non_negative_int, default=0)
    return parser.parse_args(argv)


def default_review_prompt(target_repo: Path) -> str:
    return f"""Review the target repository with Repo Radar for code taste.

Target repository: {target_repo}

Produce a concise evidence-backed report with scores, strengths, taste smells, recommendations, calibration comparison, verification and agent fit, and confidence limits. Note uncertainty where static review cannot verify behavior."""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    timeout_seconds = args.timeout_seconds or None

    try:
        run_review(
            ReviewRun(
                run_label="Repo Radar CLI review",
                target_repo=args.target_repo,
                review_prompt=default_review_prompt(args.target_repo),
                output_report=args.output,
                copilot_bin=args.copilot_bin,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                timeout_seconds=timeout_seconds,
            )
        )
    except WrapperError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
