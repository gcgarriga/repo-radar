from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.helpers import (
    COMPLETE_REPORT,
    ROOT,
    init_git_target,
    run_wrapper,
    write_fake_copilot,
)


def test_copilot_reviewer_wrapper_fails_when_git_target_is_mutated(
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
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(
        "Review the fixture with Repo Radar for code taste.\n", encoding="utf-8"
    )
    output_report = tmp_path / "reports" / "report.md"

    result = run_wrapper(target_repo, prompt_file, output_report, fake_copilot)

    assert result.returncode == 1
    assert "target repo changed unexpectedly during Copilot invocation" in result.stderr
    assert "README.md" in result.stderr
    assert not output_report.exists()
    assert (output_report.parent / "target-git-status-before.txt").exists()
    assert (output_report.parent / "target-git-status-after.txt").exists()


def test_copilot_reviewer_wrapper_exempts_configured_output_directory(
    tmp_path: Path,
) -> None:
    target_repo = init_git_target(tmp_path)
    fake_copilot = tmp_path / "fake-copilot"
    write_fake_copilot(
        fake_copilot,
        f"""#!/usr/bin/env python3
print({COMPLETE_REPORT!r})
""",
    )
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(
        "Review the fixture with Repo Radar for code taste.\n", encoding="utf-8"
    )
    output_report = target_repo / ".repo-radar-eval" / "report.md"

    result = run_wrapper(target_repo, prompt_file, output_report, fake_copilot)

    assert result.returncode == 0, result.stderr
    assert output_report.exists()
    assert (output_report.parent / "target-git-status-before.txt").read_text(
        encoding="utf-8"
    ) == ""
    assert (output_report.parent / "target-git-status-after.txt").read_text(
        encoding="utf-8"
    ) == ""


def test_copilot_reviewer_wrapper_invokes_copilot_and_writes_report(
    tmp_path: Path,
) -> None:
    fake_copilot = tmp_path / "fake-copilot"
    record_path = tmp_path / "record.json"
    fake_copilot.write_text(
        '''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

prompt = sys.argv[sys.argv.index("-p") + 1]
Path(os.environ["FAKE_COPILOT_RECORD"]).write_text(
    json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "prompt": prompt}),
    encoding="utf-8",
)
print("""# Repo Radar Report
## Verdict
Strong positive but not uncritical.
## Inferred project values
| Value | Evidence | Confidence |
| --- | --- | --- |
| readability | README.md explains the common path. | High |
## Scores
| Dimension | Score | Confidence | Aligned value(s) | Why |
| --- | --- | --- | --- | --- |
| Simplicity | 4 | High | readability | Cites README.md. |
## Strengths
- Evidence: README.md explains the common path.
## Taste Smells
- Evidence: src/tasteful_cli/domain.py could document one edge.
- Taste implication: minor usability improvement.
- Recommendation: add a focused example.
## Recommendations
Add one example.
## Calibration Comparison
Compared with `pallets/click`.
## Verification and Agent Fit
The docs are agent-readable.
## Confidence Limits
Static fixture review only.
""")
''',
        encoding="utf-8",
    )
    fake_copilot.chmod(0o755)
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(
        "Review the fixture with Repo Radar for code taste.\n", encoding="utf-8"
    )
    output_report = tmp_path / "nested" / "report.md"
    target_repo = ROOT / "evals/fixtures/tasteful-cli"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/copilot_reviewer_wrapper.py",
            "--eval-id",
            "0",
            "--target-repo",
            str(target_repo),
            "--prompt-file",
            str(prompt_file),
            "--output-report",
            str(output_report),
            "--copilot-bin",
            str(fake_copilot),
        ],
        cwd=ROOT,
        env={**os.environ, "FAKE_COPILOT_RECORD": str(record_path)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_report.read_text(encoding="utf-8").startswith("# Repo Radar Report\n")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["cwd"] == str(target_repo)
    assert "-C" in record["argv"]
    assert str(target_repo) in record["argv"]
    assert "--allow-all-tools" in record["argv"]
    assert "--allow-all-paths" in record["argv"]
    assert "--no-ask-user" in record["argv"]
    assert "--silent" in record["argv"]
    assert "--share" in record["argv"]
    assert "Review the fixture with Repo Radar for code taste." in record["prompt"]
    assert "skills/repo-radar/SKILL.md" in record["prompt"]
    assert "agents/repo-radar-reviewer.md" in record["prompt"]
    assert "calibration/default-corpus.json" in record["prompt"]
    assert "templates/repo-radar-report.md" in record["prompt"]
    assert "templates/report-contract.json" in record["prompt"]
    assert (
        "Broad local tool and path permissions are enabled only for noninteractive static review"
        in record["prompt"]
    )
    assert (
        "Run this wrapper only against disposable or trusted local checkouts"
        in record["prompt"]
    )


def test_copilot_reviewer_wrapper_includes_eval_id_and_prompt_file_content(
    tmp_path: Path,
) -> None:
    fake_copilot = tmp_path / "fake-copilot"
    record_path = tmp_path / "record.json"
    write_fake_copilot(
        fake_copilot,
        f"""#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

prompt = sys.argv[sys.argv.index("-p") + 1]
Path(os.environ["FAKE_COPILOT_RECORD"]).write_text(json.dumps({{"prompt": prompt}}), encoding="utf-8")
print({COMPLETE_REPORT!r})
""",
    )
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Eval-specific Repo Radar request.\n", encoding="utf-8")
    output_report = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/copilot_reviewer_wrapper.py",
            "--eval-id",
            "42",
            "--target-repo",
            "evals/fixtures/tasteful-cli",
            "--prompt-file",
            str(prompt_file),
            "--output-report",
            str(output_report),
            "--copilot-bin",
            str(fake_copilot),
        ],
        cwd=ROOT,
        env={**os.environ, "FAKE_COPILOT_RECORD": str(record_path)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert "Eval id: 42" in record["prompt"]
    assert "Eval-specific Repo Radar request." in record["prompt"]
    assert "offline eval adapter" in record["prompt"]
    assert "not a product CLI" in record["prompt"]


def test_copilot_reviewer_wrapper_help_warns_about_static_review_safety() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/copilot_reviewer_wrapper.py",
            "--help",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Static-review safety" in result.stdout
    assert "broad local tool and path permissions" in result.stdout
    assert "disposable or trusted local checkout" in result.stdout


def test_copilot_reviewer_wrapper_rejects_negative_timeout_before_running_copilot(
    tmp_path: Path,
) -> None:
    target_repo = tmp_path / "missing-target"
    fake_copilot = tmp_path / "fake-copilot"
    record_path = tmp_path / "record.txt"
    write_fake_copilot(
        fake_copilot,
        """#!/usr/bin/env python3
import os
from pathlib import Path

Path(os.environ["FAKE_COPILOT_RECORD"]).write_text("ran", encoding="utf-8")
""",
    )
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(
        "Review the fixture with Repo Radar for code taste.\n", encoding="utf-8"
    )
    output_report = tmp_path / "reports" / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/copilot_reviewer_wrapper.py",
            "--eval-id",
            "0",
            "--target-repo",
            str(target_repo),
            "--prompt-file",
            str(prompt_file),
            "--output-report",
            str(output_report),
            "--copilot-bin",
            str(fake_copilot),
            "--timeout-seconds",
            "-1",
        ],
        cwd=ROOT,
        env={**os.environ, "FAKE_COPILOT_RECORD": str(record_path)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "timeout must be non-negative" in result.stderr
    assert not record_path.exists()
    assert not output_report.exists()
    assert not output_report.parent.exists()


def test_copilot_reviewer_wrapper_falls_back_to_share_transcript(
    tmp_path: Path,
) -> None:
    fake_copilot = tmp_path / "fake-copilot"
    fake_copilot.write_text(
        '''#!/usr/bin/env python3
import sys
from pathlib import Path

share_path = Path(sys.argv[sys.argv.index("--share") + 1])
share_path.write_text("""# Copilot CLI Session

### 💬 Copilot

Using Repo Radar to inspect the target.

---

### 💬 Copilot

# Repo Radar Report

## Verdict
Strong positive but not uncritical.

## Inferred project values
| Value | Evidence | Confidence |
| --- | --- | --- |
| readability | README.md explains the common path. | High |

## Scores
| Dimension | Score | Confidence | Aligned value(s) | Why |
| --- | --- | --- | --- | --- |
| Simplicity | 4 | High | readability | Cites README.md. |

## Strengths
- Evidence: README.md explains the common path.

## Taste Smells
- Evidence: src/tasteful_cli/domain.py could document one edge.
- Taste implication: minor usability improvement.
- Recommendation: add a focused example.

## Recommendations
Add one example.

## Calibration Comparison
Compared with `pallets/click`.

## Verification and Agent Fit
The docs are agent-readable.

## Confidence Limits
Static fixture review only.

---
""", encoding="utf-8")
''',
        encoding="utf-8",
    )
    fake_copilot.chmod(0o755)
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(
        "Review the fixture with Repo Radar for code taste.\n", encoding="utf-8"
    )
    output_report = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/copilot_reviewer_wrapper.py",
            "--eval-id",
            "0",
            "--target-repo",
            str(ROOT / "evals/fixtures/tasteful-cli"),
            "--prompt-file",
            str(prompt_file),
            "--output-report",
            str(output_report),
            "--copilot-bin",
            str(fake_copilot),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = output_report.read_text(encoding="utf-8")
    assert report.startswith("# Repo Radar Report\n")
    assert "Using Repo Radar" not in report


def test_copilot_reviewer_wrapper_accepts_changed_share_heading_level(
    tmp_path: Path,
) -> None:
    fake_copilot = tmp_path / "fake-copilot"
    fake_copilot.write_text(
        '''#!/usr/bin/env python3
import sys
from pathlib import Path

share_path = Path(sys.argv[sys.argv.index("--share") + 1])
share_path.write_text("""# Copilot CLI Session

## Copilot

# Repo Radar Report

## Verdict
Strong positive but not uncritical.

## Inferred project values
| Value | Evidence | Confidence |
| --- | --- | --- |
| readability | README.md explains the common path. | High |

## Scores
| Dimension | Score | Confidence | Aligned value(s) | Why |
| --- | --- | --- | --- | --- |
| Simplicity | 4 | High | readability | Cites README.md. |

## Strengths
- Evidence: README.md explains the common path.

## Taste Smells
- Evidence: src/tasteful_cli/domain.py could document one edge.
- Taste implication: minor usability improvement.
- Recommendation: add a focused example.

## Recommendations
Add one example.

## Calibration Comparison
Compared with `pallets/click`.

## Verification and Agent Fit
The docs are agent-readable.

## Confidence Limits
Static fixture review only.
""", encoding="utf-8")
''',
        encoding="utf-8",
    )
    fake_copilot.chmod(0o755)
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(
        "Review the fixture with Repo Radar for code taste.\n", encoding="utf-8"
    )
    output_report = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/copilot_reviewer_wrapper.py",
            "--eval-id",
            "0",
            "--target-repo",
            str(ROOT / "evals/fixtures/tasteful-cli"),
            "--prompt-file",
            str(prompt_file),
            "--output-report",
            str(output_report),
            "--copilot-bin",
            str(fake_copilot),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_report.read_text(encoding="utf-8").startswith("# Repo Radar Report\n")


def test_copilot_reviewer_wrapper_reports_unparseable_transcript(
    tmp_path: Path,
) -> None:
    fake_copilot = tmp_path / "fake-copilot"
    fake_copilot.write_text(
        '''#!/usr/bin/env python3
import sys
from pathlib import Path

share_path = Path(sys.argv[sys.argv.index("--share") + 1])
share_path.write_text("""# Copilot CLI Session

## Copilot

I could not produce the report.
""", encoding="utf-8")
''',
        encoding="utf-8",
    )
    fake_copilot.chmod(0o755)
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(
        "Review the fixture with Repo Radar for code taste.\n", encoding="utf-8"
    )
    output_report = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/copilot_reviewer_wrapper.py",
            "--eval-id",
            "0",
            "--target-repo",
            str(ROOT / "evals/fixtures/tasteful-cli"),
            "--prompt-file",
            str(prompt_file),
            "--output-report",
            str(output_report),
            "--copilot-bin",
            str(fake_copilot),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert (
        "transcript file present but no complete Repo Radar report found"
        in result.stderr
    )
    assert not output_report.exists()


def test_copilot_reviewer_wrapper_rejects_malformed_report(tmp_path: Path) -> None:
    fake_copilot = tmp_path / "fake-copilot"
    fake_copilot.write_text(
        """#!/usr/bin/env python3
print("not a Repo Radar report")
""",
        encoding="utf-8",
    )
    fake_copilot.chmod(0o755)
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(
        "Review the fixture with Repo Radar for code taste.\n", encoding="utf-8"
    )
    output_report = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/copilot_reviewer_wrapper.py",
            "--eval-id",
            "0",
            "--target-repo",
            str(ROOT / "evals/fixtures/tasteful-cli"),
            "--prompt-file",
            str(prompt_file),
            "--output-report",
            str(output_report),
            "--copilot-bin",
            str(fake_copilot),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "missing required report sections" in result.stderr
    assert "not a Repo Radar report" in result.stderr
    diagnostics = json.loads(
        (tmp_path / "copilot-output.json").read_text(encoding="utf-8")
    )
    assert diagnostics["returncode"] == 0
    assert diagnostics["stdout"] == "not a Repo Radar report\n"
    assert not output_report.exists()
