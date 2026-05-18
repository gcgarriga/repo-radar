from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from repo_radar.evals import EvalCase
from repo_radar.grading import grade_expectation
from tests.helpers import ROOT, load_python_module


def local_case() -> EvalCase:
    return EvalCase(
        id=0,
        prompt="Review the repo at ./evals/fixtures/tasteful-cli with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/tasteful-cli",
    )


def test_report_grading_uses_packaged_runtime_artifacts_without_root_files(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    shutil.copytree(
        ROOT / "repo_radar",
        source_root / "repo_radar",
        ignore=shutil.ignore_patterns("__pycache__"),
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from repo_radar.grading import REQUIRED_REPORT_SECTIONS, default_calibration_slugs; "
                "print(REQUIRED_REPORT_SECTIONS[0]); "
                "print(default_calibration_slugs()[0])"
            ),
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(source_root)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[:2] == ["## Verdict", "pallets/click"]


def test_structured_evidence_rule_uses_paths_not_prose() -> None:
    expectation = {
        "rule_id": "cites_repo_evidence",
        "text": "Human wording intentionally omits concrete file names.",
        "paths": ["README.md"],
    }
    report = """
# Repo Radar Report
## Strengths
- Evidence: README.md explains the happy path.
"""

    result = grade_expectation(local_case(), report, expectation)

    assert result.passed, result.evidence
    assert result.rule_id == "cites_repo_evidence"


def test_legacy_string_expectations_still_map_to_rule_ids() -> None:
    report = """
# Repo Radar Report
## Strengths
- Evidence: README.md explains the happy path.
"""

    result = grade_expectation(
        local_case(),
        report,
        "Report cites concrete repo evidence from README.md.",
    )

    assert result.passed, result.evidence
    assert result.rule_id == "cites_repo_evidence"


def test_unknown_structured_rule_id_fails_fast() -> None:
    with pytest.raises(ValueError, match="unknown expectation rule_id: missing_rule"):
        grade_expectation(
            local_case(),
            "# Repo Radar Report\n",
            {
                "rule_id": "missing_rule",
                "text": "Unknown rule should not silently pass.",
            },
        )


def test_positive_verdict_allows_weakens_as_a_verb() -> None:
    report = """
# Repo Radar Report
## Verdict
Strong small-repo code taste with medium confidence. A representation mismatch weakens usability.
## Recommendations
Small improvement: document the input format.
"""

    result = grade_expectation(
        local_case(),
        report,
        {
            "rule_id": "positive_but_not_uncritical",
            "text": "Report gives a positive but not uncritical verdict for the tasteful CLI.",
        },
    )

    assert result.passed, result.evidence


def test_eval_grader_accepts_semantic_messy_service_smells() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_messy_grading"
    )
    case = run_evals.EvalCase(
        id=1,
        prompt="Review the repo at ./evals/fixtures/messy-service with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/messy-service",
    )
    report = """
# Repo Radar Report
## Verdict
Weak code taste.
## Taste Smells
- Evidence: app.py relies on global state and implicit inputs.
- Evidence: run() owns too many responsibilities and mixes parsing, persistence, network calls, and output writing.
- Evidence: there are no tests or README, and notes.txt requires manual SQLite browser setup.
"""
    expectation = (
        "Report identifies unclear entry points or cryptic API shape, tangled responsibilities, "
        "hidden global state or side effects, missing tests/docs, and manual setup or recovery."
    )

    result = run_evals.grade_expectation(case, report, expectation)

    assert result.passed, result.evidence


def test_eval_grader_requires_expected_paths_to_be_cited_as_evidence() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_evidence_path_grading"
    )
    case = run_evals.EvalCase(
        id=0,
        prompt="Review the repo at ./evals/fixtures/tasteful-cli with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/tasteful-cli",
    )
    report = """
# Repo Radar Report
## Verdict
This report mentions README.md and src/tasteful_cli/domain.py in narrative prose.
## Taste Smells
- Evidence: docs/missing.md is the only evidence-shaped citation.
"""
    expectation = (
        "Report cites concrete repo evidence from README.md, "
        "src/tasteful_cli/domain.py, or pyproject.toml."
    )

    result = run_evals.grade_expectation(case, report, expectation)

    assert not result.passed
    assert "no expected evidence path cited" in result.evidence


def test_eval_grader_rejects_expected_paths_missing_from_local_fixture() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_missing_path_grading"
    )
    case = run_evals.EvalCase(
        id=0,
        prompt="Review the repo at ./evals/fixtures/tasteful-cli with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/tasteful-cli",
    )
    report = """
# Repo Radar Report
## Verdict
Weak evidence.
## Taste Smells
- Evidence: docs/missing.md is cited as if it exists.
"""
    expectation = "Report cites concrete repo evidence from docs/missing.md."

    result = run_evals.grade_expectation(case, report, expectation)

    assert not result.passed
    assert "expected evidence paths do not exist" in result.evidence


def test_eval_grader_accepts_coupled_concerns_as_tangled_responsibilities() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_coupled_grading"
    )
    case = run_evals.EvalCase(
        id=1,
        prompt="Review the repo at ./evals/fixtures/messy-service with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/messy-service",
    )
    report = """
# Repo Radar Report
## Verdict
Weak code taste.
## Taste Smells
- Evidence: the main path couples parsing, identity, persistence, network I/O, output writing, and config into one implicit flow.
- Evidence: import-time global state hides lifecycle and side effects.
- Evidence: there is no README or tests, and notes.txt has manual recovery steps.
"""
    expectation = (
        "Report identifies unclear entry points or cryptic API shape, tangled responsibilities, "
        "hidden global state or side effects, missing tests/docs, and manual setup or recovery."
    )

    result = run_evals.grade_expectation(case, report, expectation)

    assert result.passed, result.evidence


def test_eval_grader_accepts_stable_or_durable_id_recommendation() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_identity_grading"
    )
    case = run_evals.EvalCase(
        id=2,
        prompt="Review the repo at ./evals/fixtures/trap-stack with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/trap-stack",
    )
    report = """
# Repo Radar Report
## Verdict
Mixed prototype.
## Taste Smells
- Evidence: join_users.py matches on email, a mutable identifier.
- Recommendation: use stable provider IDs or a durable cross-provider subject.
"""
    expectation = (
        "Report flags email-based matching as a mutable identifier problem and recommends "
        "persistent user or provider IDs."
    )

    result = run_evals.grade_expectation(case, report, expectation)

    assert result.passed, result.evidence


def test_eval_grader_accepts_quick_wins_as_small_first_steps() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_small_steps_grading"
    )
    case = run_evals.EvalCase(
        id=1,
        prompt="Review the repo at ./evals/fixtures/messy-service with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/messy-service",
    )
    report = """
# Repo Radar Report
## Recommendations
1. Quick win: add a README with a copyable run path.
2. Small refactor: split run() into parsing, persistence, notification, and output helpers.
3. Verification work: add tests around input normalization.
"""

    result = run_evals.grade_expectation(
        case,
        report,
        "Report recommends small first steps instead of demanding a broad rewrite.",
    )

    assert result.passed, result.evidence


def test_eval_grader_accepts_minimal_or_tiny_recommendations_as_small_steps() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_minimal_steps_grading"
    )
    case = run_evals.EvalCase(
        id=1,
        prompt="Review the repo at ./evals/fixtures/messy-service with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/messy-service",
    )
    report = """
# Repo Radar Report
## Recommendations
1. Add a minimal agent-native README and tests.
2. Add a tiny schema initialization function.
3. Add small tests for identity handling.
"""

    result = run_evals.grade_expectation(
        case,
        report,
        "Report recommends small first steps instead of demanding a broad rewrite.",
    )

    assert result.passed, result.evidence


def test_eval_grader_accepts_remove_or_justify_copies_as_structural_efficiency() -> (
    None
):
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_structural_grading"
    )
    case = run_evals.EvalCase(
        id=2,
        prompt="Review the repo at ./evals/fixtures/trap-stack with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/trap-stack",
    )
    report = """
# Repo Radar Report
## Taste Smells
- Evidence: pipeline.py copies provider-a.csv and provider-b.json before normalization.
- Taste implication: this adds I/O and intermediate artifacts without documenting an audit boundary.
- Recommendation: remove the copies or justify them as an intentional audit snapshot.
## Verification and Agent Fit
- Structural efficiency: copying both inputs before normalization is avoidable unless it is intentional.
"""

    result = run_evals.grade_expectation(
        case,
        report,
        "Report flags structural efficiency or serialization/copying issues and recommends a smaller local/scripted workflow where appropriate.",
    )

    assert result.passed, result.evidence


def test_eval_grader_accepts_serialization_without_copy_as_structural_efficiency() -> (
    None
):
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_serialization_grading"
    )
    case = run_evals.EvalCase(
        id=2,
        prompt="Review the repo at ./evals/fixtures/trap-stack with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/trap-stack",
    )
    report = """
# Repo Radar Report
## Taste Smells
- Evidence: pipeline.py serializes the full dataset into an intermediate artifact before filtering.
- Taste implication: this adds avoidable I/O and intermediate data movement.
- Recommendation: remove the intermediate serialization or document it as an audit boundary.
## Verification and Agent Fit
- Structural efficiency: unnecessary serialization makes the workflow heavier than the fixture needs.
"""

    result = run_evals.grade_expectation(
        case,
        report,
        "Report flags structural efficiency or serialization/copying issues and recommends a smaller local/scripted workflow where appropriate.",
    )

    assert result.passed, result.evidence


def test_eval_grader_detects_misapplied_best_practice_trap() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_best_practice_trap"
    )
    case = run_evals.EvalCase(
        id=3,
        prompt="Review the repo at ./evals/fixtures/one-shot-cleanup with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/one-shot-cleanup",
    )
    report = """
# Repo Radar Report
## Inferred project values
| Value | Evidence | Confidence |
| --- | --- | --- |
| readability | README.md says this is an incident handoff script. | High |
| dev-speed | cleanup_export.py keeps the workflow local and single-file. | High |
## Taste Smells
- Evidence: tests/test_cleanup_export.py covers the behavior.
- Taste implication: generic framework adoption would not serve the inferred values.
- Recommendation: keep improvements small and local to docs and tests.
"""

    value_result = run_evals.grade_expectation(
        case,
        report,
        "Report infers readability or dev-speed as project values from evidence.",
    )
    avoidance_result = run_evals.grade_expectation(
        case,
        report,
        "Report avoids generic best-practice recommendations such as scalability, microservices, formal methods, or framework adoption unless it labels them as a tradeoff tied to inferred values.",
    )

    assert value_result.passed, value_result.evidence
    assert avoidance_result.passed, avoidance_result.evidence


def test_eval_grader_accepts_holdout_directory_and_extended_suffix_evidence() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_holdout_evidence"
    )
    case = run_evals.EvalCase(
        id=103,
        prompt="Review the repo at https://github.com/django/django pinned to 335c6d0129400eda792f3bec5c71bb28af5e5d37 with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=None,
        repo_url="https://github.com/django/django",
        pinned_ref="335c6d0129400eda792f3bec5c71bb28af5e5d37",
        label="mixed",
    )
    report = """
# Repo Radar Report
## Taste Smells
- Evidence: README.rst and django/conf/__init__.py show the framework entry path; docs/topics/ captures guidance.
"""

    result = run_evals.grade_expectation(
        case,
        report,
        "Report cites concrete repo evidence from README.rst, django/, docs/, or tests/.",
    )

    assert result.passed, result.evidence


def test_eval_grader_does_not_reduce_dot_in_evidence_to_parent_directory() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_dot_in_evidence"
    )
    case = run_evals.EvalCase(
        id=100,
        prompt="Review the repo at https://github.com/sqlite/sqlite pinned to abcdef.",
        expected_output="",
        expectations=[],
        target_repo=None,
        repo_url="https://github.com/sqlite/sqlite",
        pinned_ref="abcdef",
        label="positive",
    )

    directory_only = run_evals.grade_expectation(
        case,
        "# Repo Radar Report\n- Evidence: www/ has docs.\n",
        "Report cites concrete repo evidence from www/testing.in.",
    )
    exact_file = run_evals.grade_expectation(
        case,
        "# Repo Radar Report\n- Evidence: www/testing.in explains the testing model.\n",
        "Report cites concrete repo evidence from www/testing.in.",
    )

    assert not directory_only.passed
    assert exact_file.passed, exact_file.evidence


def test_eval_grader_requires_deeper_path_for_directory_evidence() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_directory_evidence"
    )
    case = run_evals.EvalCase(
        id=103,
        prompt="Review the repo at https://github.com/django/django pinned to abcdef.",
        expected_output="",
        expectations=[],
        target_repo=None,
        repo_url="https://github.com/django/django",
        pinned_ref="abcdef",
        label="mixed",
    )

    bare_directory = run_evals.grade_expectation(
        case,
        "# Repo Radar Report\n- Evidence: docs/ contains guidance.\n",
        "Report cites concrete repo evidence from docs/.",
    )
    deeper_directory = run_evals.grade_expectation(
        case,
        "# Repo Radar Report\n- Evidence: docs/topics/settings/ explains configuration taste.\n",
        "Report cites concrete repo evidence from docs/.",
    )

    assert not bare_directory.passed
    assert deeper_directory.passed, deeper_directory.evidence


def test_eval_grader_wildcard_evidence_matches_glob_segment_semantics(
    tmp_path: Path,
) -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_wildcard_segment_evidence"
    )
    target_repo = tmp_path / "repo"
    (target_repo / "src" / "nested").mkdir(parents=True)
    (target_repo / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (target_repo / "src" / "nested" / "util.py").write_text(
        "print('nested')\n", encoding="utf-8"
    )
    case = run_evals.EvalCase(
        id=0,
        prompt="Review the repo at ./evals/fixtures/tasteful-cli with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=target_repo,
    )
    expectation = "Report cites concrete repo evidence from src/*.py."

    nested_only = run_evals.grade_expectation(
        case,
        "# Repo Radar Report\n- Evidence: src/nested/util.py explains nested behavior.\n",
        expectation,
    )
    direct_child = run_evals.grade_expectation(
        case,
        "# Repo Radar Report\n- Evidence: src/main.py explains the entry point.\n",
        expectation,
    )

    assert not nested_only.passed
    assert direct_child.passed, direct_child.evidence


def test_eval_grader_requires_named_calibration_slug_in_calibration_section() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_calibration_slug"
    )
    case = run_evals.EvalCase(
        id=0,
        prompt="Review the repo at ./evals/fixtures/tasteful-cli with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/tasteful-cli",
    )

    heading_only = run_evals.grade_expectation(
        case,
        """
# Repo Radar Report
## Calibration Comparison
Compared with the default corpus.
""",
        "Report includes calibration comparison against the default corpus or named calibration repositories.",
    )
    named_slug = run_evals.grade_expectation(
        case,
        """
# Repo Radar Report
## Calibration Comparison
Compared with `pallets/click`, the fixture keeps a similarly copyable onboarding path.
""",
        "Report includes calibration comparison against the default corpus or named calibration repositories.",
    )

    assert not heading_only.passed
    assert named_slug.passed, named_slug.evidence


def test_eval_grader_requires_mixed_signal_in_verdict_section() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_mixed_verdict"
    )
    case = run_evals.EvalCase(
        id=103,
        prompt="Review the repo at https://github.com/django/django pinned to abcdef.",
        expected_output="",
        expectations=[],
        target_repo=None,
        repo_url="https://github.com/django/django",
        pinned_ref="abcdef",
        label="mixed",
    )

    tradeoff_elsewhere = run_evals.grade_expectation(
        case,
        """
# Repo Radar Report
## Verdict
Strong positive taste.
## Recommendations
This recommendation is a tradeoff.
""",
        "Report gives a mixed or nuanced verdict for the holdout repo.",
    )
    mixed_verdict = run_evals.grade_expectation(
        case,
        """
# Repo Radar Report
## Verdict
Mixed but mature taste: the framework docs are strong, but historical layers require scoped confidence.
""",
        "Report gives a mixed or nuanced verdict for the holdout repo.",
    )

    assert not tradeoff_elsewhere.passed
    assert mixed_verdict.passed, mixed_verdict.evidence


def test_eval_grader_requires_manual_ui_evidence_in_taste_smells() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_manual_ui_smell"
    )
    case = run_evals.EvalCase(
        id=2,
        prompt="Review the repo at ./evals/fixtures/trap-stack with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/trap-stack",
    )

    verification_only = run_evals.grade_expectation(
        case,
        """
# Repo Radar Report
## Taste Smells
- Evidence: README.md has sparse docs.
## Verification and Agent Fit
- Agent-native documentation is important.
""",
        "Report flags manual UI/spreadsheet steps or missing agent-native executable documentation.",
    )
    taste_smell_evidence = run_evals.grade_expectation(
        case,
        """
# Repo Radar Report
## Taste Smells
- Evidence: docs/ui-runbook.md requires spreadsheet fixes before review.
""",
        "Report flags manual UI/spreadsheet steps or missing agent-native executable documentation.",
    )

    assert not verification_only.passed
    assert taste_smell_evidence.passed, taste_smell_evidence.evidence


def test_eval_grader_rejects_unjustified_framework_adoption() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_bad_best_practice"
    )
    case = run_evals.EvalCase(
        id=3,
        prompt="Review the repo at ./evals/fixtures/one-shot-cleanup with Repo Radar for code taste.",
        expected_output="",
        expectations=[],
        target_repo=ROOT / "evals/fixtures/one-shot-cleanup",
    )
    report = """
# Repo Radar Report
## Inferred project values
| Value | Evidence | Confidence |
| --- | --- | --- |
| readability | README.md says this is an incident handoff script. | High |
## Recommendations
Recommend framework adoption and microservices for future scalability.
"""

    result = run_evals.grade_expectation(
        case,
        report,
        "Report avoids generic best-practice recommendations such as scalability, microservices, formal methods, or framework adoption unless it labels them as a tradeoff tied to inferred values.",
    )

    assert not result.passed
