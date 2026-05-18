from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COMPLETE_REPORT = (ROOT / "tests/fixtures/complete_report.md").read_text(
    encoding="utf-8"
)


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_python_module(relative_path: str, module_name: str):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def init_git_target(tmp_path: Path) -> Path:
    target_repo = tmp_path / "target"
    target_repo.mkdir()
    (target_repo / "README.md").write_text("clean\n", encoding="utf-8")
    subprocess.run(
        ["git", "init"], cwd=target_repo, check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=target_repo, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=target_repo, check=True
    )
    subprocess.run(["git", "add", "README.md"], cwd=target_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test: initial"],
        cwd=target_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return target_repo


def write_fake_copilot(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def run_wrapper(
    target_repo: Path, prompt_file: Path, output_report: Path, fake_copilot: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
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
        capture_output=True,
        text=True,
        check=False,
    )
