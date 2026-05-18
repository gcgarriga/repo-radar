from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Needed only when this script is invoked directly (e.g. python scripts/run_evals.py)
# without an editable install; has no effect when the package is installed.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repo_radar.evals import EvalCase  # noqa: E402  (sys.path tweak above)
from repo_radar.grading import (  # noqa: E402, F401  (REQUIRED_REPORT_SECTIONS and grade_expectation are re-exported for tests/test_run_evals.py)
    ExpectationResult,
    REQUIRED_REPORT_SECTIONS,
    grade_expectation,
    grade_report,
)

DEFAULT_EVALS = ROOT / "evals/evals.json"
FIXTURE_PATH_PATTERN = re.compile(r"(\./evals/fixtures/[\w/-]+)")


def load_eval_cases(evals_path: Path) -> tuple[str, list[EvalCase]]:
    data = json.loads(evals_path.read_text(encoding="utf-8"))
    cases = []
    for raw_case in data["evals"]:
        target_repo = extract_target_repo(raw_case["prompt"])
        repo_url = raw_case.get("repo_url")
        if target_repo is None and not repo_url:
            raise ValueError(
                f"eval {raw_case['id']} must include either a repo-relative fixture path or repo_url"
            )
        cases.append(
            EvalCase(
                id=raw_case["id"],
                prompt=raw_case["prompt"],
                expected_output=raw_case["expected_output"],
                expectations=list(raw_case["expectations"]),
                target_repo=target_repo,
                repo_url=repo_url,
                pinned_ref=raw_case.get("pinned_ref"),
                label=raw_case.get("label"),
            )
        )
    return data["skill_name"], cases


def extract_target_repo(prompt: str) -> Path | None:
    match = FIXTURE_PATH_PATTERN.search(prompt)
    if not match:
        return None
    target_repo = ROOT / match.group(1)
    if not target_repo.is_dir():
        raise ValueError(f"eval fixture target does not exist: {target_repo}")
    return target_repo


def default_output_dir() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "evals/runs" / timestamp


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_case_inputs(case_dir: Path, case: EvalCase) -> Path:
    case_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = case_dir / "prompt.md"
    prompt_file.write_text(case.prompt + "\n", encoding="utf-8")
    (case_dir / "expected_output.md").write_text(
        case.expected_output + "\n", encoding="utf-8"
    )
    write_json(
        case_dir / "metadata.json",
        {
            "eval_id": case.id,
            "prompt": case.prompt,
            "target_repo": target_repo_display(case),
            "target_repo_url": case.repo_url,
            "pinned_ref": case.pinned_ref,
            "label": case.label,
            "expected_output": case.expected_output,
            "expectations": case.expectations,
        },
    )
    return prompt_file


def target_repo_display(case: EvalCase) -> str:
    if case.target_repo is not None:
        return str(case.target_repo.relative_to(ROOT))
    if case.repo_url and case.pinned_ref:
        return f"{case.repo_url}@{case.pinned_ref}"
    if case.repo_url:
        return case.repo_url
    return "<unknown>"


def report_path_from_reports_dir(reports_dir: Path, case_id: int) -> Path | None:
    candidates = [
        reports_dir / f"eval-{case_id}.md",
        reports_dir / f"{case_id}.md",
        reports_dir / f"eval-{case_id}" / "report.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def run_report_command(
    command: list[str], case: EvalCase, prompt_file: Path, report_file: Path
) -> None:
    result = subprocess.run(
        command
        + [
            "--eval-id",
            str(case.id),
            "--target-repo",
            str(case.target_repo),
            "--prompt-file",
            str(prompt_file),
            "--output-report",
            str(report_file),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    (report_file.parent / "command.json").write_text(
        json.dumps(
            {
                "args": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr
            or result.stdout
            or f"report command exited {result.returncode}"
        )
    if not report_file.exists() and result.stdout.strip():
        report_file.write_text(result.stdout, encoding="utf-8")
    if not report_file.exists():
        raise RuntimeError(
            "report command succeeded but did not write a report or stdout"
        )


def run_case(
    case: EvalCase,
    output_dir: Path,
    report_command: list[str] | None,
    reports_dir: Path | None,
) -> dict[str, Any]:
    case_dir = output_dir / f"eval-{case.id}"
    prompt_file = write_case_inputs(case_dir, case)
    report_file = case_dir / "report.md"

    if reports_dir:
        source_report = report_path_from_reports_dir(reports_dir, case.id)
        if not source_report:
            return case_summary(
                case, "error", [], f"missing report for eval {case.id} in {reports_dir}"
            )
        report_file.write_text(
            source_report.read_text(encoding="utf-8"), encoding="utf-8"
        )
    elif report_command:
        if case.target_repo is None:
            return case_summary(
                case,
                "error",
                [],
                "remote repo evals require a checked-out target repo; use --reports-dir for pre-generated reports",
            )
        run_report_command(report_command, case, prompt_file, report_file)
    else:
        return case_summary(
            case, "skipped", [], "dry run: prompt written, no report generated"
        )

    report = report_file.read_text(encoding="utf-8")
    grading = grade_report(case, report)
    write_json(
        case_dir / "grading.json",
        {
            "eval_id": case.id,
            "expectations": [
                {
                    "rule_id": result.rule_id,
                    "text": result.text,
                    "passed": result.passed,
                    "evidence": result.evidence,
                }
                for result in grading
            ],
        },
    )
    status = "passed" if all(result.passed for result in grading) else "failed"
    return case_summary(case, status, grading, "")


def case_summary(
    case: EvalCase, status: str, grading: list[ExpectationResult], error: str
) -> dict[str, Any]:
    passed = sum(1 for result in grading if result.passed)
    return {
        "id": case.id,
        "target_repo": target_repo_display(case),
        "label": case.label,
        "status": status,
        "expectation_count": len(grading),
        "passed_expectation_count": passed,
        "failed_expectation_count": len(grading) - passed,
        "error": error,
    }


def write_summary(
    output_dir: Path, skill_name: str, run_mode: str, cases: list[dict[str, Any]]
) -> None:
    graded_cases = [case for case in cases if case["status"] in {"passed", "failed"}]
    failed_cases = [case for case in cases if case["status"] in {"failed", "error"}]
    summary = {
        "skill_name": skill_name,
        "run_mode": run_mode,
        "eval_count": len(cases),
        "graded_eval_count": len(graded_cases),
        "skipped_eval_count": sum(1 for case in cases if case["status"] == "skipped"),
        "failed_eval_count": len(failed_cases),
        "total_expectations": sum(case["expectation_count"] for case in graded_cases),
        "passed_expectations": sum(
            case["passed_expectation_count"] for case in graded_cases
        ),
        "cases": cases,
    }
    write_json(output_dir / "summary.json", summary)
    lines = [
        "# Repo Radar Eval Run",
        "",
        f"- Skill: `{skill_name}`",
        f"- Mode: `{run_mode}`",
        f"- Evals: {summary['eval_count']}",
        f"- Graded: {summary['graded_eval_count']}",
        f"- Passed expectations: {summary['passed_expectations']}/{summary['total_expectations']}",
        "",
        "## Cases",
    ]
    for case in cases:
        lines.append(
            f"- Eval {case['id']} `{case['target_repo']}`: {case['status']} "
            f"({case['passed_expectation_count']}/{case['expectation_count']})"
        )
        if case["error"]:
            lines.append(f"  - Error: {case['error']}")
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run offline Repo Radar eval fixtures."
    )
    parser.add_argument(
        "--evals", type=Path, default=DEFAULT_EVALS, help="Path to evals.json."
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Directory for eval run artifacts."
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=None,
        help="Directory of existing reports to grade.",
    )
    parser.add_argument(
        "--report-command",
        nargs=argparse.REMAINDER,
        help=(
            "Command used to generate each report. The runner appends --eval-id, "
            "--target-repo, --prompt-file, and --output-report."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.report_command == []:
        print("--report-command requires at least one argument.", file=sys.stderr)
        return 2
    if args.reports_dir and args.report_command:
        print(
            "Use either --reports-dir or --report-command, not both.", file=sys.stderr
        )
        return 2

    output_dir = args.output or default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_name, cases = load_eval_cases(args.evals)
    run_mode = "dry-run"
    if args.reports_dir:
        run_mode = "reports-dir"
    elif args.report_command:
        run_mode = "report-command"

    summaries = []
    for case in cases:
        try:
            summaries.append(
                run_case(case, output_dir, args.report_command, args.reports_dir)
            )
        except Exception as error:
            summaries.append(case_summary(case, "error", [], str(error)))

    write_summary(output_dir, skill_name, run_mode, summaries)
    print(f"Wrote eval run to {output_dir}")
    return 1 if any(case["status"] in {"failed", "error"} for case in summaries) else 0


if __name__ == "__main__":
    raise SystemExit(main())
