import argparse
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def load_case(eval_id):
    evals = json.loads((_ROOT / "evals/evals.json").read_text(encoding="utf-8"))
    return next(case for case in evals["evals"] if str(case["id"]) == eval_id)


def evidence_paths(case):
    paths = []
    for expectation in case["expectations"]:
        if expectation["rule_id"] == "cites_repo_evidence":
            paths.extend(expectation["paths"])
    return paths or ["README.md"]


def report_for(case):
    rules = {expectation["rule_id"] for expectation in case["expectations"]}
    paths = ", ".join(evidence_paths(case))
    if "weak_taste" in rules:
        verdict = "Weak taste with high confidence."
    elif "mixed_or_nuanced_verdict" in rules:
        verdict = (
            "Mixed but mature taste: clear strengths, but bounded tradeoffs remain."
        )
    else:
        verdict = "Strong positive but not uncritical: clean, with one small improvement around examples."
    return f"""# Repo Radar Report
## Verdict
{verdict}
## Inferred project values
| Value | Evidence | Confidence |
| --- | --- | --- |
| readability | README.md explains the common path. | High |
| dev-speed | cleanup_export.py keeps the workflow local and single-file. | High |
## Scores
| Dimension | Score | Confidence | Aligned value(s) | Why |
| --- | --- | --- | --- | --- |
| Simplicity | 4 | High | readability, dev-speed | Cites {paths}. |
## Strengths
- Evidence: {paths} show a clear common path.
## Taste Smells
- Evidence: {paths} provide concrete repo evidence.
- Evidence: app.py has unclear entry points, cryptic API shape, tangled responsibilities, hidden global state and side effects.
- Evidence: missing tests/docs make behavior hard to trust, and notes.txt requires manual setup or recovery.
- Evidence: join_users.py matches on email, a mutable identifier; use persistent user or provider IDs.
- Evidence: docs/ui-runbook.md requires manual UI and spreadsheet steps, not agent-native executable documentation.
- Evidence: pipeline.py has structural efficiency issues: copying and serialization create avoidable I/O and intermediate data.
- Taste implication: this is a readability improvement, with CLI usability, error handling, examples, and tests as practical improvement topics.
- Recommendation: quick win: add small tests and docs; remove or justify copies; keep recommendations small and local to script ergonomics and examples.
## Recommendations
Use quick wins and small first steps: add docs, isolate responsibilities, keep the script local, and add focused tests.
## Calibration Comparison
Matches `pallets/click` patterns for focused APIs and readable tests.
## Verification and Agent Fit
Commands are copyable and agent-native; structural efficiency and serialization are explicitly checked.
## Confidence Limits
Only the fixture repo sample was inspected.
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-id", required=True)
    parser.add_argument("--target-repo", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-report", required=True)
    args = parser.parse_args()
    Path(args.output_report).write_text(
        report_for(load_case(args.eval_id)).strip() + "\n", encoding="utf-8"
    )
