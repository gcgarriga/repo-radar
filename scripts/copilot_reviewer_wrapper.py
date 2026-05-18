from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repo_radar.cli_args import non_negative_int  # noqa: E402
from repo_radar.copilot_cli import (  # noqa: E402
    ReviewRun,
    STATIC_REVIEW_SAFETY,
    WrapperError,
    read_required_file,
    run_review,
)


EVAL_SAFETY_INSTRUCTION = (
    "Broad local tool and path permissions are enabled only for noninteractive static review. "
    "Run this wrapper only against disposable or trusted local checkouts."
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Repo Radar eval report through Copilot CLI.",
        epilog=STATIC_REVIEW_SAFETY,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--eval-id", required=True)
    parser.add_argument("--target-repo", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    target_repo = args.target_repo.resolve()
    prompt_file = args.prompt_file.resolve()
    output_report = args.output_report.resolve()
    timeout_seconds = args.timeout_seconds or None

    try:
        review_prompt = read_required_file(prompt_file, "prompt file").strip()
        run_review(
            ReviewRun(
                run_label=f"Eval id: {args.eval_id}",
                target_repo=target_repo,
                review_prompt=review_prompt,
                output_report=output_report,
                copilot_bin=args.copilot_bin,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                timeout_seconds=timeout_seconds,
                runtime_description="an offline eval adapter",
                workflow_description="not a product CLI",
                request_heading="Original eval prompt",
                safety_instruction=EVAL_SAFETY_INSTRUCTION,
            )
        )
    except WrapperError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
