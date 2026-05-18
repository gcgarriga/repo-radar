from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.helpers import ROOT, load_python_module, read_text


def test_eval_fixtures_are_checked_in() -> None:
    fixture_paths = [
        "evals/fixtures/tasteful-cli/README.md",
        "evals/fixtures/tasteful-cli/examples/events.ndjson",
        "evals/fixtures/tasteful-cli/src/tasteful_cli/domain.py",
        "evals/fixtures/tasteful-cli/tests/test_domain.py",
        "evals/fixtures/messy-service/app.py",
        "evals/fixtures/messy-service/helpers.py",
        "evals/fixtures/messy-service/notes.txt",
        "evals/fixtures/trap-stack/README.md",
        "evals/fixtures/trap-stack/join_users.py",
        "evals/fixtures/trap-stack/pipeline.py",
        "evals/fixtures/trap-stack/docs/ui-runbook.md",
        "evals/fixtures/trap-stack/provider-a.csv",
        "evals/fixtures/trap-stack/provider-b.json",
        "evals/fixtures/one-shot-cleanup/README.md",
        "evals/fixtures/one-shot-cleanup/cleanup_export.py",
        "evals/fixtures/one-shot-cleanup/tests/test_cleanup_export.py",
    ]

    for relative_path in fixture_paths:
        assert read_text(relative_path)


def test_trap_stack_fixture_exposes_email_join_ambiguity(tmp_path: Path) -> None:
    fixture = ROOT / "evals/fixtures/trap-stack"
    join_users = load_python_module(
        "evals/fixtures/trap-stack/join_users.py", "join_users_fixture"
    )
    output_path = tmp_path / "matches.json"

    join_users.normalize(
        fixture / "provider-a.csv",
        fixture / "provider-b.json",
        output_path,
    )

    matches = json.loads(output_path.read_text(encoding="utf-8"))
    sam_matches = [match for match in matches if match["email"] == "sam@example.com"]
    assert len(sam_matches) == 2
    for match in sam_matches:
        provider_a = json.loads(match["provider_a"])
        provider_b = json.loads(match["provider_b"])
        assert provider_b["provider_b_id"] == "b-200"
        assert "provider_a_id" in provider_a
    provider_a_ids = {
        json.loads(match["provider_a"])["provider_a_id"] for match in sam_matches
    }
    assert provider_a_ids == {"a-100", "a-101"}


def test_tasteful_cli_quickstart_command_is_runnable(tmp_path: Path) -> None:
    fixture = ROOT / "evals/fixtures/tasteful-cli"
    input_path = fixture / "examples/events.ndjson"
    output_path = tmp_path / "summary.json"
    env = {
        **os.environ,
        "PYTHONPATH": str(fixture / "src"),
    }

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tasteful_cli",
            "--input",
            str(input_path.relative_to(fixture)),
            "--output",
            str(output_path),
        ],
        cwd=fixture,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists(), f"expected summary output at {output_path}"
    assert json.loads(output_path.read_text(encoding="utf-8")) == {
        "login": 5,
        "signup": 5,
    }
