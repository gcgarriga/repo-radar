# Contributing to repo-radar

`repo-radar` is a small alpha project. Bug reports and small PRs are welcome.

## Dev setup

```bash
pip install -e ".[dev]"
pytest
ruff check . && ruff format .
```

Python 3.11+.

## Notes

- Use conventional-commit prefixes: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.
- If you edit anything under `skills/`, `agents/`, `templates/`, or `calibration/`, regenerate the packaged mirror with `python3 scripts/sync_runtime_artifacts.py`. CI will fail otherwise. See [`docs/development.md`](docs/development.md) for the source-of-truth rules.
- For security issues, see [`SECURITY.md`](SECURITY.md) — do not open a public issue.
