# Development Notes

## Source of truth for artifacts

The root artifact directories are the human-editable source:

- `skills/repo-radar/SKILL.md`
- `agents/repo-radar-reviewer.md`
- `templates/repo-radar-report.md`
- `templates/report-contract.json`
- `calibration/default-corpus.json`

The packaged copies under `repo_radar/_artifacts/` must stay byte-for-byte aligned with those root files. The tests compare those surfaces because installed packages read from `repo_radar/_artifacts/`, while direct agent installs read from the root artifact directories.

## Report contract changes

When changing the report shape, update every runtime contract surface in one patch:

- `templates/report-contract.json`
- `skills/repo-radar/SKILL.md`
- `agents/repo-radar-reviewer.md`
- `templates/repo-radar-report.md`
- `repo_radar/_artifacts/templates/report-contract.json`
- `repo_radar/_artifacts/skills/repo-radar/SKILL.md`
- `repo_radar/_artifacts/agents/repo-radar-reviewer.md`
- `repo_radar/_artifacts/templates/repo-radar-report.md`
- `scripts/run_evals.py`
- `tests/test_prompt_artifacts.py`
- `tests/test_run_evals.py`

`templates/report-contract.json` is the machine-readable source for runtime required sections. The prompt artifacts stay self-contained so installed agents do not depend on hidden code. The contract-drift tests should fail if a required heading changes in one place but not the others.

## Development commands

```bash
pip install -e ".[dev]"
pytest
```
