from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from tests.helpers import COMPLETE_REPORT, ROOT, init_git_target, write_fake_copilot


def read_pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_pyproject_exposes_repo_radar_console_script() -> None:
    pyproject = read_pyproject()

    assert pyproject["project"]["scripts"]["repo-radar"] == "repo_radar.cli:main"
    assert pyproject["tool"]["setuptools"]["packages"] == ["repo_radar"]


def test_pyproject_has_publish_metadata() -> None:
    project = read_pyproject()["project"]

    assert project["readme"] == "README.md"
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]
    assert project["authors"] == [{"name": "gcgarriga"}]
    assert project["urls"]["Repository"] == "https://github.com/gcgarriga/repo-radar"
    assert "Programming Language :: Python :: 3.11" in project["classifiers"]
    assert "Programming Language :: Python :: 3.12" in project["classifiers"]
    assert {"code-review", "developer-tools", "repository-analysis"}.issubset(
        project["keywords"]
    )


def test_pyproject_ships_runtime_artifacts_as_package_data() -> None:
    pyproject = read_pyproject()
    package_data = pyproject["tool"]["setuptools"]["package-data"]

    assert set(package_data) == {"repo_radar"}
    assert "_artifacts/agents/*.md" in package_data["repo_radar"]
    assert "_artifacts/calibration/*.json" in package_data["repo_radar"]
    assert "_artifacts/skills/repo-radar/SKILL.md" in package_data["repo_radar"]
    assert "_artifacts/templates/*.md" in package_data["repo_radar"]
    assert "_artifacts/templates/*.json" in package_data["repo_radar"]


def test_repo_radar_package_is_importable() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import repo_radar; print(repo_radar.__version__)"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == read_pyproject()["project"]["version"]


def test_repo_radar_console_script_target_is_callable() -> None:
    pyproject = read_pyproject()
    module_name, function_name = pyproject["project"]["scripts"]["repo-radar"].split(
        ":", maxsplit=1
    )

    module = importlib.import_module(module_name)
    entrypoint = getattr(module, function_name)

    assert callable(entrypoint)


def test_repo_radar_help_describes_copilot_cli_wrapper() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "repo_radar.cli", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (
        "Run Repo Radar against a local repository through Copilot CLI."
        in result.stdout
    )
    assert "Static-review safety" in result.stdout
    assert "broad local tool and path permissions" in result.stdout
    assert "disposable or trusted local checkout" in result.stdout


def test_repo_radar_non_editable_install_exposes_help(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    shutil.copytree(
        ROOT,
        source_dir,
        ignore=shutil.ignore_patterns(
            ".git",
            ".pytest_cache",
            "__pycache__",
            "build",
            "dist",
            "repo_radar.egg-info",
        ),
    )

    venv_dir = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    if os.name == "nt":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_scripts = venv_dir / "Scripts"
        repo_radar_bin = venv_scripts / "repo-radar.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_scripts = venv_dir / "bin"
        repo_radar_bin = venv_scripts / "repo-radar"

    install_result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--quiet", "."],
        cwd=source_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    assert install_result.returncode == 0, (
        install_result.stderr or install_result.stdout
    )
    assert repo_radar_bin.exists(), f"{repo_radar_bin} not created by install"

    help_result = subprocess.run(
        [str(repo_radar_bin), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert help_result.returncode == 0, help_result.stderr or help_result.stdout
    assert (
        "Run Repo Radar against a local repository through Copilot CLI."
        in help_result.stdout
    )

    namespace_result = subprocess.run(
        [
            str(venv_python),
            "-c",
            (
                "import importlib.util; "
                "assert importlib.util.find_spec('agents') is None; "
                "assert importlib.util.find_spec('calibration') is None; "
                "assert importlib.util.find_spec('skills') is None; "
                "assert importlib.util.find_spec('templates') is None"
            ),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert namespace_result.returncode == 0, (
        namespace_result.stderr or namespace_result.stdout
    )


def test_parse_args_uses_cli_defaults_and_environment(monkeypatch) -> None:
    from repo_radar.cli import parse_args

    monkeypatch.setenv("REPO_RADAR_COPILOT_BIN", "env-copilot")
    monkeypatch.setenv("REPO_RADAR_COPILOT_MODEL", "env-model")
    monkeypatch.setenv("REPO_RADAR_COPILOT_REASONING_EFFORT", "high")

    args = parse_args(["target"])

    assert args.target_repo == Path("target")
    assert args.output == Path("repo-radar-report.md")
    assert args.copilot_bin == "env-copilot"
    assert args.model == "env-model"
    assert args.reasoning_effort == "high"
    assert args.timeout_seconds == 0


def test_default_review_prompt_requests_repo_radar_code_taste_sections() -> None:
    from repo_radar.cli import default_review_prompt

    prompt = default_review_prompt(Path("target"))

    assert "Repo Radar" in prompt
    assert "code taste" in prompt
    for expected in [
        "scores",
        "strengths",
        "taste smells",
        "recommendations",
        "calibration comparison",
        "verification and agent fit",
        "confidence limits",
    ]:
        assert expected in prompt.lower()


def test_repo_radar_module_invokes_copilot_and_writes_report(tmp_path: Path) -> None:
    target_repo = init_git_target(tmp_path)
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
Path(os.environ["FAKE_COPILOT_RECORD"]).write_text(
    json.dumps({{"argv": sys.argv[1:], "cwd": os.getcwd(), "prompt": prompt}}),
    encoding="utf-8",
)
print({COMPLETE_REPORT!r})
""",
    )
    output_report = tmp_path / "reports" / "repo-radar-report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "repo_radar.cli",
            str(target_repo),
            "--output",
            str(output_report),
            "--copilot-bin",
            str(fake_copilot),
            "--model",
            "gpt-test",
            "--reasoning-effort",
            "high",
            "--timeout-seconds",
            "30",
        ],
        cwd=ROOT,
        env={**os.environ, "FAKE_COPILOT_RECORD": str(record_path)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_report.read_text(encoding="utf-8") == COMPLETE_REPORT.strip() + "\n"

    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["cwd"] == str(target_repo)
    assert record["argv"][:3] == ["-C", str(target_repo), "--silent"]
    for expected in [
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
        str(output_report.parent / "copilot-session.md"),
        "--model",
        "gpt-test",
        "--effort",
        "high",
    ]:
        assert expected in record["argv"]

    prompt = record["prompt"]
    assert f"Target repository: {target_repo}" in prompt
    assert "Review the target repository with Repo Radar for code taste." in prompt
    for expected in [
        "scores",
        "strengths",
        "taste smells",
        "recommendations",
        "calibration comparison",
        "verification and agent fit",
        "confidence limits",
    ]:
        assert expected in prompt.lower()
    for artifact in [
        "skills/repo-radar/SKILL.md",
        "agents/repo-radar-reviewer.md",
        "calibration/default-corpus.json",
        "templates/repo-radar-report.md",
        "templates/report-contract.json",
    ]:
        assert artifact in prompt


def test_repo_radar_module_reports_invalid_target_path(tmp_path: Path) -> None:
    missing_target = tmp_path / "missing"
    output_report = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "repo_radar.cli",
            str(missing_target),
            "--output",
            str(output_report),
            "--copilot-bin",
            "unused-copilot",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "target repo does not exist" in result.stderr
    assert not output_report.exists()


def test_repo_radar_module_rejects_negative_timeout_before_running_copilot(
    tmp_path: Path,
) -> None:
    target_repo = init_git_target(tmp_path)
    fake_copilot = tmp_path / "fake-copilot"
    record_path = tmp_path / "record.json"
    write_fake_copilot(
        fake_copilot,
        """#!/usr/bin/env python3
import os
from pathlib import Path

Path(os.environ["FAKE_COPILOT_RECORD"]).write_text("ran", encoding="utf-8")
""",
    )
    output_report = tmp_path / "reports" / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "repo_radar.cli",
            str(target_repo),
            "--output",
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
