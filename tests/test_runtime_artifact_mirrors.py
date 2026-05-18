from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from tests.helpers import ROOT, load_python_module, read_text


def test_runtime_artifact_mirrors_match_canonical_sources() -> None:
    sync_artifacts = load_python_module(
        "scripts/sync_runtime_artifacts.py", "sync_runtime_artifacts_for_test"
    )

    assert sync_artifacts.find_drift(ROOT) == []


def test_sync_runtime_artifacts_check_reports_drift(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    shutil.copytree(ROOT, source_root)
    (source_root / "repo_radar/_artifacts/templates/report-contract.json").write_text(
        '{"version": 999}\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/sync_runtime_artifacts.py",
            "--check",
            "--root",
            str(source_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert (
        "different: repo_radar/_artifacts/templates/report-contract.json"
        in result.stderr
    )
    assert "source: templates/report-contract.json" in result.stderr


def test_sync_runtime_artifacts_refreshes_package_mirror(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    shutil.copytree(ROOT, source_root)
    source_file = source_root / "templates/report-contract.json"
    mirror_file = source_root / "repo_radar/_artifacts/templates/report-contract.json"
    mirror_file.write_text('{"version": 999}\n', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/sync_runtime_artifacts.py",
            "--root",
            str(source_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert mirror_file.read_text(encoding="utf-8") == source_file.read_text(
        encoding="utf-8"
    )


def test_readme_declares_runtime_artifact_source_of_truth() -> None:
    readme = read_text("README.md")

    for required in [
        "Runtime artifact source of truth",
        "Root `skills/`, `agents/`, `templates/`, and `calibration/` files are canonical",
        "`repo_radar/_artifacts/` is a packaged mirror",
        "pytest tests/test_prompt_artifacts.py tests/test_runtime_artifact_mirrors.py",
        "python3 scripts/sync_runtime_artifacts.py --check",
        "python3 scripts/sync_runtime_artifacts.py",
    ]:
        assert required in readme, required
