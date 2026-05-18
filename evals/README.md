# Repo Radar Evals

`evals/` is the offline bench for the skill and reviewer prompt. The runner reads `evals/evals.json`, writes one directory per case, and grades reports against the expectations.

## Local evals

```bash
# Dry run: write prompts and metadata only.
python3 scripts/run_evals.py

# Grade reports you generated manually.
python3 scripts/run_evals.py --reports-dir path/to/reports

# Generate reports through a wrapper command.
python3 scripts/run_evals.py --report-command python3 scripts/copilot_reviewer_wrapper.py
```

`scripts/copilot_reviewer_wrapper.py` is the Copilot CLI adapter for evals. It builds the prompt from the local skill, reviewer, calibration corpus, and template; runs `copilot -p` against the target repo; validates the report shape; and writes `report.md`.

Static-review safety: the wrapper enables broad local tool and path permissions so noninteractive evals can inspect checked-out repositories. Run it only against a disposable or trusted local checkout; the generated prompt still forbids dependency installation, network calls, file mutation, and commits.

Pick the model with `REPO_RADAR_COPILOT_MODEL` and reasoning effort with `REPO_RADAR_COPILOT_REASONING_EFFORT`, or pass `--model` / `--reasoning-effort` directly. Each run also keeps `copilot-output.json` and `copilot-session.md` for inspection.

## Holdout evals

External holdouts live in `evals/repo-holdouts.json`. They stay disjoint from the runtime corpus so reports can be tested on repos the reviewer has not been calibrated on. The runner can dry-run remote evals and can grade pre-generated reports via `--reports-dir`.

To exercise a remote holdout with the Copilot wrapper, generate the prompts first, then clone the pinned repo and write a report into the shape `--reports-dir` expects.

The `/tmp/` paths below are replaceable host scratch paths; use any disposable directory your environment preserves for the duration of the run.

```bash
mkdir -p /tmp/repo-radar-holdout-repos /tmp/repo-radar-holdout-reports/eval-100
python3 scripts/run_evals.py --evals evals/repo-holdouts.json --output /tmp/repo-radar-holdouts
git clone https://github.com/postgres/postgres /tmp/repo-radar-holdout-repos/postgres
git -C /tmp/repo-radar-holdout-repos/postgres checkout 422e54e3092afd09997d27cc7c99598f91075b0d
python3 scripts/copilot_reviewer_wrapper.py \
  --eval-id 100 \
  --target-repo /tmp/repo-radar-holdout-repos/postgres \
  --prompt-file /tmp/repo-radar-holdouts/eval-100/prompt.md \
  --output-report /tmp/repo-radar-holdout-reports/eval-100/report.md \
  --timeout-seconds 300
python3 scripts/run_evals.py --evals evals/repo-holdouts.json --reports-dir /tmp/repo-radar-holdout-reports
```
