# repo-radar

> **Status:** alpha. APIs, prompts, and the report contract may change. `repo-radar` depends on a working [Copilot CLI](https://docs.github.com/copilot/github-copilot-in-the-cli/about-github-copilot-in-the-cli) install and uses your existing Copilot authentication.

`repo-radar` reviews a checked-out repository and writes an evidence-backed code taste report: simplicity, architectural elegance, usability, and newcomer understandability.

It runs as a Copilot CLI-backed workflow. The package embeds the Repo Radar skill, reviewer prompt, calibration corpus, and report contract, then asks Copilot to inspect the target repo with static-review guardrails.

## Quick start

```bash
pip install -e .
repo-radar /path/to/repo --output report.md
```

Static-review safety: this wrapper gives Copilot broad local tool and path permissions so noninteractive static reviews can run without prompts. Run it only against a disposable or trusted local checkout; the prompt still forbids dependency installation, network calls, file mutation, and commits.

Optional runtime controls:

```bash
repo-radar /path/to/repo --output report.md \
  --copilot-bin copilot \
  --model claude-sonnet-4.6 \
  --reasoning-effort high \
  --timeout-seconds 300
```

The command uses your existing Copilot CLI authentication and does not require a separate model API token.

## What it produces

A Repo Radar report includes:

- inferred project values
- scored taste dimensions
- cited strengths and taste smells
- practical recommendations
- calibration comparison
- verification notes and confidence limits

Scores are navigation; the cited evidence and recommendations are the product.

## Runtime artifacts

The public runtime artifacts live at the repository root:

- `skills/repo-radar/SKILL.md` — skill workflow and guardrails
- `agents/repo-radar-reviewer.md` — reviewer subagent prompt
- `templates/repo-radar-report.md` — report shape
- `templates/report-contract.json` — machine-readable report contract
- `calibration/default-corpus.json` — default positive calibration corpus

The package also ships these files under `repo_radar/_artifacts/` so the `repo-radar` command works after a non-editable install.

## Install as a Copilot CLI skill

For computer-wide Copilot CLI installation:

```bash
copilot plugin install gcgarriga/repo-radar
```

The `gcgarriga` owner in this command is the repository owner, not the installing user. If installing from a fork, replace `gcgarriga` with the fork owner.

The installed reviewer subagent is exposed as `repo-radar:repo-radar-reviewer`. For local checkout smoke tests, fallback project-scoped copies, and troubleshooting, see [`docs/install.md`](docs/install.md).

### Runtime artifact source of truth

Root `skills/`, `agents/`, `templates/`, and `calibration/` files are canonical for direct installation and tests. `repo_radar/_artifacts/` is a packaged mirror used by the installed `repo-radar` command through Python package resources.

After changing runtime artifacts, run `python3 scripts/sync_runtime_artifacts.py` to refresh the packaged mirror. Use `python3 scripts/sync_runtime_artifacts.py --check` to verify the mirror has not drifted.

For report contract changes, run `pytest tests/test_prompt_artifacts.py tests/test_runtime_artifact_mirrors.py` to verify the prompt contract and packaged mirror stay aligned.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Developer notes:

- Eval workflow: [`evals/README.md`](evals/README.md)
- Contract and artifact maintenance: [`docs/development.md`](docs/development.md)
