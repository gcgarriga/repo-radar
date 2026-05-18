from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from tests.helpers import ROOT, load_python_module, read_text


def test_repo_holdouts_are_machine_readable_and_disjoint_from_default_corpus() -> None:
    corpus = json.loads(read_text("calibration/default-corpus.json"))
    holdouts = json.loads(read_text("evals/repo-holdouts.json"))
    default_slugs = {repo["slug"] for repo in corpus["repos"]}
    seen_ids = set()
    labels = set()

    assert holdouts["skill_name"] == "repo-radar"
    for eval_case in holdouts["evals"]:
        seen_ids.add(eval_case["id"])
        labels.add(eval_case["label"])
        assert eval_case["repo_url"].startswith("https://github.com/")
        assert re.fullmatch(r"[a-f0-9]{40}", eval_case["pinned_ref"])
        assert f"pinned to {eval_case['pinned_ref']}" in eval_case["prompt"]
        assert len(eval_case["starter_files"]) >= 1
        assert len(eval_case["expected_findings"]) >= 3
        assert len(eval_case["forbidden_shortcuts"]) >= 2
        assert len(eval_case["expectations"]) >= 5
        slug = eval_case["repo_url"].removeprefix("https://github.com/")
        assert slug not in default_slugs

    assert len(seen_ids) == len(holdouts["evals"])
    assert {"positive", "negative", "mixed"}.issubset(labels)


def test_eval_runner_requires_inferred_project_values_section() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_required_sections"
    )

    assert "## Inferred project values" in run_evals.REQUIRED_REPORT_SECTIONS


def test_eval_cases_are_machine_readable_and_gradable() -> None:
    evals = json.loads(read_text("evals/evals.json"))

    assert evals["skill_name"] == "repo-radar"
    assert len(evals["evals"]) >= 4

    for eval_case in evals["evals"]:
        assert isinstance(eval_case["id"], int)
        assert eval_case["prompt"]
        assert "<repo-radar-repo>" not in eval_case["prompt"]
        target_match = re.search(r"(\./evals/fixtures/[\w/-]+)", eval_case["prompt"])
        assert target_match, eval_case["prompt"]
        assert (ROOT / target_match.group(1)).is_dir()
        assert eval_case["expected_output"]
        assert eval_case["files"] == []
        assert len(eval_case["expectations"]) >= 5
        assert all(expectation for expectation in eval_case["expectations"])


def test_eval_expectations_use_structured_rule_ids() -> None:
    for relative_path in ["evals/evals.json", "evals/repo-holdouts.json"]:
        evals = json.loads(read_text(relative_path))
        for eval_case in evals["evals"]:
            for expectation in eval_case["expectations"]:
                assert isinstance(expectation, dict), (
                    relative_path,
                    eval_case["id"],
                    expectation,
                )
                assert expectation["rule_id"], (
                    relative_path,
                    eval_case["id"],
                    expectation,
                )
                assert expectation["text"], (
                    relative_path,
                    eval_case["id"],
                    expectation,
                )
                if expectation["rule_id"] == "cites_repo_evidence":
                    assert expectation["paths"], (
                        relative_path,
                        eval_case["id"],
                        expectation,
                    )


def test_eval_runner_executes_all_cases_with_report_command(tmp_path: Path) -> None:
    reporter = ROOT / "tests/fixtures/mock_reporter.py"
    output_dir = tmp_path / "run"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_evals.py",
            "--output",
            str(output_dir),
            "--report-command",
            sys.executable,
            str(reporter),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    expected_eval_count = len(json.loads(read_text("evals/evals.json"))["evals"])
    assert summary["skill_name"] == "repo-radar"
    assert summary["run_mode"] == "report-command"
    assert summary["eval_count"] == expected_eval_count
    assert summary["passed_expectations"] == summary["total_expectations"]
    for case in summary["cases"]:
        assert case["status"] == "passed"
        case_dir = output_dir / f"eval-{case['id']}"
        assert (case_dir / "prompt.md").exists()
        assert (case_dir / "report.md").exists()
        assert (case_dir / "grading.json").exists()


def test_mock_reporter_fixture_is_import_safe() -> None:
    mock_reporter = load_python_module(
        "tests/fixtures/mock_reporter.py", "mock_reporter_fixture_import_safe"
    )

    assert callable(mock_reporter.report_for)


def test_eval_runner_dry_run_writes_prompts_without_reports(tmp_path: Path) -> None:
    output_dir = tmp_path / "dry-run"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_evals.py",
            "--output",
            str(output_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["run_mode"] == "dry-run"
    assert summary["skipped_eval_count"] == summary["eval_count"]
    assert summary["graded_eval_count"] == 0
    for case in summary["cases"]:
        case_dir = output_dir / f"eval-{case['id']}"
        assert (case_dir / "prompt.md").exists()
        assert (case_dir / "metadata.json").exists()
        assert not (case_dir / "report.md").exists()


def test_eval_runner_dry_run_supports_remote_repo_holdouts(tmp_path: Path) -> None:
    output_dir = tmp_path / "remote-dry-run"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_evals.py",
            "--evals",
            "evals/repo-holdouts.json",
            "--output",
            str(output_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["run_mode"] == "dry-run"
    assert summary["eval_count"] >= 6
    assert summary["skipped_eval_count"] == summary["eval_count"]
    assert {case["label"] for case in summary["cases"]} >= {
        "positive",
        "negative",
        "mixed",
    }

    first_case = summary["cases"][0]
    metadata = json.loads(
        (output_dir / f"eval-{first_case['id']}" / "metadata.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["target_repo"].startswith("https://github.com/")
    assert metadata["target_repo_url"].startswith("https://github.com/")
    assert re.fullmatch(r"[a-f0-9]{40}", metadata["pinned_ref"])


def test_eval_grading_lives_in_dedicated_module() -> None:
    from repo_radar.evals import EvalCase
    from repo_radar import grading

    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_grading_module"
    )
    run_evals_source = read_text("scripts/run_evals.py")

    assert hasattr(grading, "ReportView")
    assert hasattr(grading, "REQUIRED_REPORT_SECTIONS")
    assert hasattr(grading, "grade_expectation")
    assert hasattr(grading, "grade_report")
    assert run_evals.REQUIRED_REPORT_SECTIONS == grading.REQUIRED_REPORT_SECTIONS
    assert run_evals.grade_expectation.__module__ == "repo_radar.grading"
    assert run_evals.EvalCase is EvalCase
    assert "def grade_expectation" not in run_evals_source
    assert "def parse_report" not in run_evals_source


def test_eval_runner_rejects_empty_report_command(tmp_path: Path) -> None:
    output_dir = tmp_path / "empty-command"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_evals.py",
            "--output",
            str(output_dir),
            "--report-command",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--report-command requires at least one argument" in result.stderr
