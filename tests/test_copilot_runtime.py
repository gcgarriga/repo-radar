from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from repo_radar.copilot_cli import (
    ARTIFACT_PATHS,
    STATIC_REVIEW_SAFETY,
    ReviewRun,
    build_copilot_command,
    build_review_prompt,
    choose_report,
    load_report_contract,
    missing_report_sections,
    required_report_sections,
    run_review,
)
from tests.helpers import COMPLETE_REPORT, ROOT, init_git_target, write_fake_copilot


def test_build_review_prompt_embeds_runtime_artifacts_and_request() -> None:
    target_repo = ROOT / "evals/fixtures/tasteful-cli"

    prompt = build_review_prompt(
        run_label="Manual run",
        target_repo=target_repo,
        review_prompt="Review this repo with Repo Radar.",
    )

    assert "Copilot CLI wrapper" in prompt
    assert "skill + reviewer-agent workflow, not a standalone model client" in prompt
    assert "Manual run" in prompt
    assert f"Target repository: {target_repo}" in prompt
    assert "Review this repo with Repo Radar." in prompt
    for artifact in ARTIFACT_PATHS:
        assert f"--- {artifact.label} ---" in prompt
        assert (ROOT / artifact.label).read_text(encoding="utf-8").strip() in prompt
    assert STATIC_REVIEW_SAFETY.split(":")[0] in prompt
    assert "Use safe static inspection only" in prompt
    assert "Output only the final Repo Radar Report markdown" in prompt


def test_copilot_runtime_import_does_not_require_runtime_artifacts(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    shutil.copytree(
        ROOT / "repo_radar",
        source_root / "repo_radar",
        ignore=shutil.ignore_patterns("__pycache__", "_artifacts"),
    )

    result = subprocess.run(
        [sys.executable, "-c", "import repo_radar.copilot_cli; print('imported')"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(source_root)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "imported"


def test_build_copilot_command_uses_noninteractive_static_review_flags(
    tmp_path: Path,
) -> None:
    target_repo = ROOT / "evals/fixtures/tasteful-cli"
    share_path = tmp_path / "session.md"

    command = build_copilot_command(
        copilot_bin="copilot",
        target_repo=target_repo,
        prompt="prompt text",
        share_path=share_path,
        model="gpt-test",
        reasoning_effort="high",
    )

    assert command[:3] == ["copilot", "-C", str(target_repo)]
    for flag in [
        "--silent",
        "--stream",
        "off",
        "--output-format",
        "text",
        "--no-remote",
        "--no-auto-update",
        "--no-custom-instructions",
        "--allow-all-tools",
        "--allow-all-paths",
        "--no-ask-user",
        "--share",
        str(share_path),
    ]:
        assert flag in command
    assert ["--model", "gpt-test"] == command[
        command.index("--model") : command.index("--model") + 2
    ]
    assert ["--effort", "high"] == command[
        command.index("--effort") : command.index("--effort") + 2
    ]
    assert command[-2:] == ["-p", "prompt text"]


def test_build_copilot_command_omits_optional_model_and_effort(tmp_path: Path) -> None:
    command = build_copilot_command(
        copilot_bin="copilot",
        target_repo=ROOT / "evals/fixtures/tasteful-cli",
        prompt="prompt text",
        share_path=tmp_path / "session.md",
        model=None,
        reasoning_effort=None,
    )

    assert "--model" not in command
    assert "--effort" not in command
    assert command[-2:] == ["-p", "prompt text"]


def test_missing_report_sections_uses_report_contract_and_rejects_incomplete_reports() -> (
    None
):
    sections = required_report_sections()
    assert sections == list(load_report_contract()["required_sections"])
    assert missing_report_sections(COMPLETE_REPORT) == []

    malformed_missing = missing_report_sections("not a report")
    assert "# Repo Radar Report" in malformed_missing
    for section in sections:
        assert section in malformed_missing

    incomplete_missing = missing_report_sections("# Repo Radar Report\n## Verdict\n")
    assert "# Repo Radar Report" not in incomplete_missing
    assert "## Verdict" not in incomplete_missing
    assert "## Scores" in incomplete_missing


def test_choose_report_ignores_later_unrelated_copilot_settings_heading(
    tmp_path: Path,
) -> None:
    transcript_cases = [
        ("## Copilot", "## GitHub Copilot Settings"),
        ("### Copilot", "## Copilot Settings"),
        ("### 💬 Copilot", "### Copilot Configuration"),
    ]
    for index, (copilot_heading, later_heading) in enumerate(transcript_cases, start=1):
        transcript_path = tmp_path / f"transcript-{index}.md"
        transcript_path.write_text(
            f"""# Copilot CLI Session

{copilot_heading}

{COMPLETE_REPORT}
---

{later_heading}

This heading is documentation, not an assistant message.
""",
            encoding="utf-8",
        )

        assert (
            choose_report("not a report", transcript_path)
            == COMPLETE_REPORT.strip() + "\n"
        )


def test_run_review_writes_normalized_report_and_diagnostics(tmp_path: Path) -> None:
    target_repo = init_git_target(tmp_path)
    fake_copilot = tmp_path / "fake-copilot"
    write_fake_copilot(
        fake_copilot,
        f"""#!/usr/bin/env python3
print("preamble before the final report")
print("```markdown")
print({COMPLETE_REPORT!r})
print("```")
""",
    )
    output_report = tmp_path / "out" / "report.md"

    run_review(
        ReviewRun(
            run_label="Manual run",
            target_repo=target_repo,
            review_prompt="Review this target.",
            output_report=output_report,
            copilot_bin=str(fake_copilot),
            model=None,
            reasoning_effort=None,
            timeout_seconds=None,
        )
    )

    assert output_report.read_text(encoding="utf-8") == COMPLETE_REPORT.strip() + "\n"
    diagnostics = json.loads(
        (output_report.parent / "copilot-output.json").read_text(encoding="utf-8")
    )
    assert diagnostics["returncode"] == 0
    assert diagnostics["args"][-2:] == ["-p", "<prompt omitted>"]
    assert diagnostics["stdout"].startswith("preamble before the final report")
    assert (output_report.parent / "target-git-status-before.txt").read_text(
        encoding="utf-8"
    ) == ""
    assert (output_report.parent / "target-git-status-after.txt").read_text(
        encoding="utf-8"
    ) == ""


def test_run_review_treats_zero_timeout_as_no_timeout(tmp_path: Path) -> None:
    target_repo = init_git_target(tmp_path)
    fake_copilot = tmp_path / "fake-copilot"
    write_fake_copilot(
        fake_copilot,
        f"""#!/usr/bin/env python3
print({COMPLETE_REPORT!r})
""",
    )
    output_report = tmp_path / "out" / "report.md"

    run_review(
        ReviewRun(
            run_label="Manual run",
            target_repo=target_repo,
            review_prompt="Review this target.",
            output_report=output_report,
            copilot_bin=str(fake_copilot),
            model=None,
            reasoning_effort=None,
            timeout_seconds=0,
        )
    )

    assert output_report.read_text(encoding="utf-8") == COMPLETE_REPORT.strip() + "\n"


def test_run_review_rejects_target_mutation_and_does_not_write_report(
    tmp_path: Path,
) -> None:
    target_repo = init_git_target(tmp_path)
    fake_copilot = tmp_path / "fake-copilot"
    write_fake_copilot(
        fake_copilot,
        f"""#!/usr/bin/env python3
from pathlib import Path
Path("README.md").write_text("mutated\\n", encoding="utf-8")
print({COMPLETE_REPORT!r})
""",
    )
    output_report = tmp_path / "out" / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "from repo_radar.copilot_cli import ReviewRun, run_review; "
                "run_review(ReviewRun('Manual run', Path(r'%s'), 'Review.', Path(r'%s'), r'%s', None, None, None))"
            )
            % (target_repo, output_report, fake_copilot),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "target repo changed unexpectedly during Copilot invocation" in result.stderr
    assert "README.md" in result.stderr
    assert not output_report.exists()
    assert (output_report.parent / "target-git-status-before.txt").exists()
    assert (output_report.parent / "target-git-status-after.txt").exists()


def test_run_review_rejects_committed_target_mutation_and_does_not_write_report(
    tmp_path: Path,
) -> None:
    target_repo = init_git_target(tmp_path)
    fake_copilot = tmp_path / "fake-copilot"
    write_fake_copilot(
        fake_copilot,
        f"""#!/usr/bin/env python3
import subprocess
subprocess.run(
    ["git", "commit", "--allow-empty", "-m", "test: copilot mutation"],
    check=True,
    capture_output=True,
    text=True,
)
print({COMPLETE_REPORT!r})
""",
    )
    output_report = tmp_path / "out" / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "from repo_radar.copilot_cli import ReviewRun, run_review; "
                "run_review(ReviewRun('Manual run', Path(r'%s'), 'Review.', Path(r'%s'), r'%s', None, None, None))"
            )
            % (target_repo, output_report, fake_copilot),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "target repo changed unexpectedly during Copilot invocation" in result.stderr
    assert not output_report.exists()
