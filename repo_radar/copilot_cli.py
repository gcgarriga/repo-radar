from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
STATIC_REVIEW_SAFETY = (
    "Static-review safety: this wrapper gives Copilot broad local tool and path permissions "
    "so noninteractive static reviews can run without prompts. Run it only against a disposable "
    "or trusted local checkout; the prompt still forbids dependency installation, network "
    "calls, file mutation, and commits."
)


class WrapperError(Exception):
    pass


@dataclass(frozen=True)
class RuntimeArtifact:
    label: str
    resource_path: str


ARTIFACT_PATHS = [
    RuntimeArtifact(
        "skills/repo-radar/SKILL.md", "_artifacts/skills/repo-radar/SKILL.md"
    ),
    RuntimeArtifact(
        "agents/repo-radar-reviewer.md", "_artifacts/agents/repo-radar-reviewer.md"
    ),
    RuntimeArtifact(
        "calibration/default-corpus.json", "_artifacts/calibration/default-corpus.json"
    ),
    RuntimeArtifact(
        "templates/repo-radar-report.md", "_artifacts/templates/repo-radar-report.md"
    ),
    RuntimeArtifact(
        "templates/report-contract.json", "_artifacts/templates/report-contract.json"
    ),
]
REPORT_CONTRACT_ARTIFACT = RuntimeArtifact(
    "templates/report-contract.json", "_artifacts/templates/report-contract.json"
)
DEFAULT_CALIBRATION_ARTIFACT = RuntimeArtifact(
    "calibration/default-corpus.json", "_artifacts/calibration/default-corpus.json"
)


def read_required_artifact(artifact: RuntimeArtifact) -> str:
    resource = resources.files("repo_radar").joinpath(artifact.resource_path)
    try:
        return resource.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise WrapperError(
            f"{artifact.label} does not exist in installed repo_radar package"
        ) from error


@lru_cache(maxsize=1)
def load_report_contract() -> dict:
    return json.loads(read_required_artifact(REPORT_CONTRACT_ARTIFACT))


def required_report_sections() -> list[str]:
    return list(load_report_contract()["required_sections"])


@dataclass(frozen=True)
class ReviewRun:
    run_label: str
    target_repo: Path
    review_prompt: str
    output_report: Path
    copilot_bin: str
    model: str | None
    reasoning_effort: str | None
    timeout_seconds: int | None
    runtime_description: str = "a Copilot CLI wrapper"
    workflow_description: str = "not a standalone model client"
    request_heading: str = "Original review request"
    safety_instruction: str = STATIC_REVIEW_SAFETY


@dataclass(frozen=True)
class TargetGitStatus:
    root: Path
    target_pathspec: str
    output_dir_exemption: str | None
    before: str
    before_head: str | None
    output_dir: Path


def read_required_file(path: Path, label: str) -> str:
    if not path.is_file():
        raise WrapperError(f"{label} does not exist: {path}")
    return path.read_text(encoding="utf-8")


def build_review_prompt(
    run_label: str,
    target_repo: Path,
    review_prompt: str,
    artifact_paths: Sequence[RuntimeArtifact] = ARTIFACT_PATHS,
    runtime_description: str = "a Copilot CLI wrapper",
    workflow_description: str = "not a standalone model client",
    request_heading: str = "Original review request",
    safety_instruction: str = STATIC_REVIEW_SAFETY,
) -> str:
    artifact_blocks = []
    for artifact in artifact_paths:
        artifact_blocks.append(
            f"--- {artifact.label} ---\n{read_required_artifact(artifact).strip()}"
        )

    return f"""You are running the Repo Radar runtime as {runtime_description}.

{run_label}
Target repository: {target_repo}

{request_heading}:
{review_prompt.strip()}

Use the local Repo Radar runtime artifacts below as the authoritative contract. This is a skill + reviewer-agent workflow, {workflow_description}. Follow the skill workflow, reviewer evidence protocol, calibration corpus, and report template.

{chr(10).join(artifact_blocks)}

Execution rules:
- Inspect the target repository rooted at the current working directory.
- {safety_instruction}
- Use safe static inspection only. Do not install dependencies, call network services, mutate repository files, or create commits.
- Cite concrete target-repo evidence for every important claim.
- Preserve the chain: repo evidence -> taste implication -> recommendation.
- Distinguish facts from taste judgments and state confidence limits.
- Output only the final Repo Radar Report markdown. Do not include preamble, transcript notes, or fenced code blocks.
"""


def build_copilot_command(
    copilot_bin: str,
    target_repo: Path,
    prompt: str,
    share_path: Path,
    model: str | None,
    reasoning_effort: str | None,
) -> list[str]:
    command = [
        copilot_bin,
        "-C",
        str(target_repo),
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
    ]
    if model:
        command.extend(["--model", model])
    if reasoning_effort:
        command.extend(["--effort", reasoning_effort])
    command.extend(["-p", prompt])
    return command


def normalize_report(stdout: str) -> str:
    report = stdout.strip()
    marker = "# Repo Radar Report"
    marker_index = report.rfind(marker)
    if marker_index >= 0:
        report = report[marker_index:]
    if report.startswith("```markdown"):
        report = report.removeprefix("```markdown").strip()
    elif report.startswith("```"):
        report = report.removeprefix("```").strip()
    if report.endswith("```"):
        report = report[: -len("```")].rstrip()
    return report + "\n" if report else ""


def missing_report_sections(report: str) -> list[str]:
    missing_sections = []
    if not report.startswith("# Repo Radar Report"):
        missing_sections.append("# Repo Radar Report")
    missing_sections.extend(
        section for section in required_report_sections() if section not in report
    )
    return missing_sections


def extract_final_copilot_message(transcript: str) -> str:
    lines = transcript.splitlines()
    message_start_indexes = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^#{1,6}\s+(?:💬\s*)?Copilot\s*$", line)
    ]
    if not message_start_indexes:
        return ""
    start = message_start_indexes[-1] + 1
    while start < len(lines) and not lines[start].strip():
        start += 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def choose_report(stdout: str, transcript_path: Path) -> str:
    report = normalize_report(stdout)
    if missing_report_sections(report) and transcript_path.is_file():
        transcript = transcript_path.read_text(encoding="utf-8")
        transcript_report = normalize_report(extract_final_copilot_message(transcript))
        if not missing_report_sections(transcript_report):
            return transcript_report
        if transcript.strip():
            raise WrapperError(
                "transcript file present but no complete Repo Radar report found in final Copilot message"
            )
    return report


def validate_report(report: str) -> None:
    missing_sections = missing_report_sections(report)
    if missing_sections:
        preview = report.strip()[:500] or "<empty output>"
        raise WrapperError(
            f"missing required report sections: {', '.join(missing_sections)}; output preview: {preview}"
        )


def git_root_for(path: Path) -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def target_pathspec(git_root: Path, target_repo: Path) -> str:
    try:
        relative_target = target_repo.relative_to(git_root)
    except ValueError as error:
        raise WrapperError(
            f"target repo is outside detected git root: {target_repo}"
        ) from error
    return "." if str(relative_target) == "." else relative_target.as_posix()


def output_dir_exemption(
    git_root: Path, target_repo: Path, output_dir: Path
) -> str | None:
    try:
        output_dir.relative_to(target_repo)
    except ValueError:
        return None
    if output_dir == target_repo:
        raise WrapperError("output report directory cannot be the target repo root")
    return output_dir.relative_to(git_root).as_posix()


def status_line_paths(line: str) -> list[str]:
    path_text = line[3:].strip()
    if " -> " in path_text:
        return path_text.split(" -> ")
    return [path_text]


def is_under_status_dir(path: str, directory: str) -> bool:
    return path == directory or path.startswith(f"{directory}/")


def filter_status(status: str, exempt_directory: str | None) -> str:
    if not exempt_directory:
        return status
    kept_lines = [
        line
        for line in status.splitlines()
        if not all(
            is_under_status_dir(path, exempt_directory)
            for path in status_line_paths(line)
        )
    ]
    return "\n".join(kept_lines) + ("\n" if kept_lines else "")


def git_status_for_target(
    git_root: Path, target_pathspec_value: str, exempt_directory: str | None
) -> str:
    result = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--untracked-files=all",
            "--",
            target_pathspec_value,
        ],
        cwd=git_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"exit code {result.returncode}"
        )
        raise WrapperError(f"git status failed for target repo: {detail}")
    return filter_status(result.stdout, exempt_directory)


def git_head_for(git_root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=git_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def begin_target_git_status(
    target_repo: Path, output_dir: Path
) -> TargetGitStatus | None:
    git_root = git_root_for(target_repo)
    if git_root is None:
        return None
    pathspec = target_pathspec(git_root, target_repo)
    exemption = output_dir_exemption(git_root, target_repo, output_dir)
    before = git_status_for_target(git_root, pathspec, exemption)
    before_head = git_head_for(git_root)
    (output_dir / "target-git-status-before.txt").write_text(before, encoding="utf-8")
    (output_dir / "target-git-head-before.txt").write_text(
        (before_head or "") + "\n", encoding="utf-8"
    )
    return TargetGitStatus(
        root=git_root,
        target_pathspec=pathspec,
        output_dir_exemption=exemption,
        before=before,
        before_head=before_head,
        output_dir=output_dir,
    )


def target_mutation_error(status: TargetGitStatus | None) -> WrapperError | None:
    if status is None:
        return None
    after = git_status_for_target(
        status.root, status.target_pathspec, status.output_dir_exemption
    )
    after_head = git_head_for(status.root)
    (status.output_dir / "target-git-status-after.txt").write_text(
        after, encoding="utf-8"
    )
    (status.output_dir / "target-git-head-after.txt").write_text(
        (after_head or "") + "\n", encoding="utf-8"
    )
    status_changed = status.before != after
    head_changed = status.before_head != after_head
    if not status_changed and not head_changed:
        return None
    message_parts = ["target repo changed unexpectedly during Copilot invocation"]
    if status_changed:
        message_parts.append(f"before git status:\n{status.before or '<clean>'}")
        message_parts.append(f"after git status:\n{after or '<clean>'}")
    if head_changed:
        message_parts.append(f"before HEAD: {status.before_head or '<none>'}")
        message_parts.append(f"after HEAD: {after_head or '<none>'}")
    return WrapperError("\n".join(message_parts))


def diagnostic_args(command: list[str]) -> list[str]:
    redacted = []
    skip_next = False
    for item in command:
        if skip_next:
            redacted.append("<prompt omitted>")
            skip_next = False
            continue
        redacted.append(item)
        if item == "-p":
            skip_next = True
    return redacted


def write_copilot_diagnostics(
    path: Path, command: list[str], result: subprocess.CompletedProcess[str]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "args": diagnostic_args(command),
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


def run_copilot(
    command: list[str],
    target_repo: Path,
    timeout_seconds: int | None,
    diagnostics_path: Path,
) -> str:
    if timeout_seconds is not None and timeout_seconds < 0:
        raise WrapperError(
            f"timeout must be non-negative, got {timeout_seconds} seconds"
        )
    timeout = None if timeout_seconds == 0 else timeout_seconds

    try:
        result = subprocess.run(
            command,
            cwd=target_repo,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as error:
        raise WrapperError(f"copilot binary not found: {command[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise WrapperError(
            f"copilot invocation timed out after {timeout_seconds} seconds"
        ) from error

    write_copilot_diagnostics(diagnostics_path, command, result)
    if result.returncode != 0:
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"exit code {result.returncode}"
        )
        raise WrapperError(f"copilot invocation failed: {detail}")
    return result.stdout


def run_review(review: ReviewRun) -> None:
    target_repo = review.target_repo.resolve()
    output_report = review.output_report.resolve()
    if not target_repo.is_dir():
        raise WrapperError(f"target repo does not exist: {target_repo}")

    prompt = build_review_prompt(
        review.run_label,
        target_repo,
        review.review_prompt,
        runtime_description=review.runtime_description,
        workflow_description=review.workflow_description,
        request_heading=review.request_heading,
        safety_instruction=review.safety_instruction,
    )
    output_report.parent.mkdir(parents=True, exist_ok=True)
    share_path = output_report.parent / "copilot-session.md"
    command = build_copilot_command(
        review.copilot_bin,
        target_repo,
        prompt,
        share_path,
        review.model,
        review.reasoning_effort,
    )
    target_status = begin_target_git_status(target_repo, output_report.parent)
    copilot_error = None
    stdout = ""
    try:
        stdout = run_copilot(
            command,
            target_repo,
            review.timeout_seconds,
            output_report.parent / "copilot-output.json",
        )
    except WrapperError as error:
        copilot_error = error

    mutation_error = target_mutation_error(target_status)
    if mutation_error and copilot_error:
        raise WrapperError(f"{copilot_error}\n{mutation_error}") from copilot_error
    if mutation_error:
        raise mutation_error
    if copilot_error:
        raise copilot_error

    report = choose_report(stdout, share_path)
    validate_report(report)
    output_report.write_text(report, encoding="utf-8")
