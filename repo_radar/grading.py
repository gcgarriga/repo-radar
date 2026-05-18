from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from repo_radar.copilot_cli import (
    DEFAULT_CALIBRATION_ARTIFACT,
    load_report_contract,
    read_required_artifact,
)

FILE_TOKEN_PATTERN = re.compile(
    r"[\w./*-]+(?:\.(?:md|py|toml|txt|rst|rdoc|html|go|c|h|java|cs|json|yaml|yml|rs|rb|in)|/)"
)
REPORT_CONTRACT = load_report_contract()
REQUIRED_REPORT_SECTIONS = list(REPORT_CONTRACT["required_sections"])


@dataclass(frozen=True)
class ExpectationResult:
    text: str
    passed: bool
    evidence: str
    rule_id: str


@dataclass(frozen=True)
class ExpectationSpec:
    rule_id: str
    text: str
    params: dict[str, Any]


@dataclass(frozen=True)
class ReportView:
    sections: dict[str, str]
    evidence_paths: frozenset[str]


SUPPORTED_RULE_IDS = frozenset(
    {
        "required_sections",
        "cites_repo_evidence",
        "positive_but_not_uncritical",
        "practical_improvement",
        "calibration_comparison",
        "weak_taste",
        "mixed_or_nuanced_verdict",
        "confidence_limits",
        "messy_service_smells",
        "small_first_steps",
        "mutable_email_identifier",
        "manual_ui_or_spreadsheet",
        "structural_efficiency",
        "readability_or_dev_speed_values",
        "avoid_generic_best_practices",
        "small_local_recommendations",
        "text_in_report",
    }
)
LEGACY_RULE_MARKERS = [
    ("required repo-radar sections", "required_sections"),
    ("cites concrete repo evidence", "cites_repo_evidence"),
    ("positive but not uncritical", "positive_but_not_uncritical"),
    ("practical improvement", "practical_improvement"),
    ("calibration comparison", "calibration_comparison"),
    ("weak taste", "weak_taste"),
    ("mixed or nuanced verdict", "mixed_or_nuanced_verdict"),
    ("confidence limits", "confidence_limits"),
    ("unclear entry points", "messy_service_smells"),
    ("small first steps", "small_first_steps"),
    ("email-based matching", "mutable_email_identifier"),
    ("manual ui/spreadsheet", "manual_ui_or_spreadsheet"),
    ("structural efficiency", "structural_efficiency"),
    ("readability or dev-speed", "readability_or_dev_speed_values"),
    ("generic best-practice", "avoid_generic_best_practices"),
    ("small and local", "small_local_recommendations"),
]


def grade_report(case: Any, report: str) -> list[ExpectationResult]:
    return [
        grade_expectation(case, report, expectation)
        for expectation in case.expectations
    ]


def legacy_rule_id(expectation: str) -> str:
    expectation_lower = expectation.lower()
    for marker, rule_id in LEGACY_RULE_MARKERS:
        if marker in expectation_lower:
            return rule_id
    return "text_in_report"


def normalize_expectation(expectation: Any) -> ExpectationSpec:
    if isinstance(expectation, str):
        return ExpectationSpec(
            rule_id=legacy_rule_id(expectation),
            text=expectation,
            params={},
        )
    if not isinstance(expectation, dict):
        raise TypeError(
            f"expectation must be a string or object, got {type(expectation).__name__}"
        )

    rule_id = expectation.get("rule_id")
    if not isinstance(rule_id, str) or not rule_id:
        raise ValueError("structured expectation must include non-empty rule_id")
    if rule_id not in SUPPORTED_RULE_IDS:
        raise ValueError(f"unknown expectation rule_id: {rule_id}")

    text = expectation.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"expectation {rule_id} must include non-empty text")

    params = {
        key: value
        for key, value in expectation.items()
        if key not in {"rule_id", "text"}
    }
    return ExpectationSpec(rule_id=rule_id, text=text, params=params)


def expectation_paths(spec: ExpectationSpec) -> list[str]:
    raw_paths = spec.params.get("paths")
    if raw_paths is None:
        return FILE_TOKEN_PATTERN.findall(spec.text)
    if not isinstance(raw_paths, list) or not all(
        isinstance(path, str) and path for path in raw_paths
    ):
        raise ValueError(
            f"expectation {spec.rule_id} paths must be a list of non-empty strings"
        )
    return raw_paths


def section_text(report: str, heading: str) -> str:
    pattern = re.compile(rf"(?ims)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)")
    match = pattern.search(report)
    return match.group(1).strip() if match else ""


def contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def parse_report(report: str) -> ReportView:
    sections = {
        heading.removeprefix("## "): section_text(report, heading.removeprefix("## "))
        for heading in REQUIRED_REPORT_SECTIONS
    }
    evidence_paths: set[str] = set()
    for line in report.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("-", "*", "|")):
            evidence_paths.update(FILE_TOKEN_PATTERN.findall(line))
    return ReportView(sections=sections, evidence_paths=frozenset(evidence_paths))


def expected_path_exists(target_repo: Path | None, expected_path: str) -> bool:
    if target_repo is None:
        return True
    if "*" in expected_path:
        return any(target_repo.glob(expected_path))
    if expected_path.endswith("/"):
        return (target_repo / expected_path).is_dir()
    return (target_repo / expected_path).is_file()


def evidence_path_matches(cited_path: str, expected_path: str) -> bool:
    if "*" in expected_path:
        return PurePosixPath(cited_path).match(expected_path)
    if expected_path.endswith("/"):
        return cited_path.startswith(expected_path) and cited_path != expected_path
    return cited_path == expected_path


def cited_expected_paths(
    report_view: ReportView, expected_paths: list[str]
) -> list[str]:
    return [
        expected_path
        for expected_path in expected_paths
        if any(
            evidence_path_matches(cited_path, expected_path)
            for cited_path in report_view.evidence_paths
        )
    ]


def default_calibration_slugs() -> list[str]:
    corpus = json.loads(read_required_artifact(DEFAULT_CALIBRATION_ARTIFACT))
    return [repo["slug"].lower() for repo in corpus["repos"]]


def grade_expectation(case: Any, report: str, expectation: Any) -> ExpectationResult:
    spec = normalize_expectation(expectation)
    report_lower = report.lower()
    report_view = parse_report(report)

    if spec.rule_id == "required_sections":
        missing_sections = [
            section for section in REQUIRED_REPORT_SECTIONS if section not in report
        ]
        if missing_sections:
            return expectation_result(
                spec, False, f"missing sections: {', '.join(missing_sections)}"
            )
        return expectation_result(
            spec, True, "all required report sections are present"
        )

    if spec.rule_id == "cites_repo_evidence":
        expected_paths = expectation_paths(spec)
        existing_expected_paths = [
            path
            for path in expected_paths
            if expected_path_exists(case.target_repo, path)
        ]
        if not existing_expected_paths:
            return ExpectationResult(
                spec.text,
                False,
                f"expected evidence paths do not exist under target repo: {', '.join(expected_paths)}",
                spec.rule_id,
            )
        cited_paths = cited_expected_paths(report_view, existing_expected_paths)
        if cited_paths:
            return expectation_result(spec, True, f"cites: {', '.join(cited_paths)}")
        return ExpectationResult(
            spec.text,
            False,
            f"no expected evidence path cited from: {existing_expected_paths}",
            spec.rule_id,
        )

    if spec.rule_id == "positive_but_not_uncritical":
        verdict = section_text(report, "Verdict").lower()
        negative_terms = [
            "not positive",
            "not strong",
            "weak",
            "poor",
            "messy",
            "negative",
            "low taste",
        ]
        positive_terms = ["positive", "strong", "clean", "tasteful", "good"]
        positive = any(
            contains_term(verdict, term) for term in positive_terms
        ) and not any(contains_term(verdict, term) for term in negative_terms)
        bounded = any(
            term in report_lower for term in ["not uncritical", "improvement", "small"]
        )
        return expectation_result(
            spec,
            positive and bounded,
            "Verdict is positive (no negation) and the report bounds it with improvement language",
        )

    if spec.rule_id == "practical_improvement":
        has_improvement = any(
            term in report_lower for term in ["improvement", "recommendation", "small"]
        )
        has_topic = any(
            term in report_lower
            for term in ["example", "cli", "error handling", "tests"]
        )
        return expectation_result(
            spec, has_improvement and has_topic, "mentions practical improvement topics"
        )

    if spec.rule_id == "calibration_comparison":
        calibration_section = section_text(report, "Calibration Comparison").lower()
        cited_slugs = [
            slug for slug in default_calibration_slugs() if slug in calibration_section
        ]
        return expectation_result(
            spec,
            bool(cited_slugs),
            f"cites calibration repos: {', '.join(cited_slugs)}"
            if cited_slugs
            else "missing named calibration repo slug in Calibration Comparison",
        )

    if spec.rule_id == "weak_taste":
        verdict = section_text(report, "Verdict").lower()
        weak_in_verdict = any(
            term in verdict for term in ["weak", "messy", "low taste", "critical"]
        )
        # Confidence must be Medium/High in the Verdict itself, not just any "Medium" in Scores.
        verdict_is_low_confidence = "low confidence" in verdict
        verdict_is_confident = any(
            term in verdict for term in ["medium confidence", "high confidence"]
        )
        no_explicit_confidence = (
            not verdict_is_low_confidence and not verdict_is_confident
        )
        has_confident_signal = verdict_is_confident or no_explicit_confidence
        return expectation_result(
            spec,
            weak_in_verdict and has_confident_signal,
            "Verdict states weak taste and is not labelled low confidence",
        )

    if spec.rule_id == "mixed_or_nuanced_verdict":
        verdict = section_text(report, "Verdict").lower()
        explicit_mixed = any(term in verdict for term in ["mixed", "nuanced"])
        strength_terms = ["positive", "strong", "strength", "mature", "clear", "good"]
        weakness_terms = [
            "weakness",
            "smell",
            "risk",
            "tradeoff",
            "trade-off",
            "but",
            "however",
            "bounded",
        ]
        balanced_verdict = any(term in verdict for term in strength_terms) and any(
            term in verdict for term in weakness_terms
        )
        return expectation_result(
            spec,
            explicit_mixed or balanced_verdict,
            "Verdict section contains explicit mixed/nuanced language or balanced strength/weakness signals",
        )

    if spec.rule_id == "confidence_limits":
        passed = "## confidence limits" in report_lower and any(
            term in report_lower
            for term in [
                "sample",
                "sampling",
                "large",
                "subsystem",
                "only",
                "not inspected",
            ]
        )
        return expectation_result(spec, passed, "states scoped confidence limits")

    if spec.rule_id == "messy_service_smells":
        required_groups = [
            (
                "entry/API clarity",
                [
                    "unclear entry",
                    "no clear entry",
                    "no entry point",
                    "missing entry",
                    "cryptic",
                    "implicit",
                    "no readme",
                    "infer the entry",
                    "infer entry",
                ],
            ),
            (
                "tangled responsibilities",
                [
                    "tangled",
                    "too many responsibilities",
                    "one function owns",
                    "mixes",
                    "coupled",
                    "couples",
                    "unrelated concerns",
                    "concerns into",
                ],
            ),
            (
                "hidden globals or side effects",
                [
                    "hidden global",
                    "global state",
                    "process-global",
                    "side effect",
                    "network",
                ],
            ),
            (
                "missing tests/docs",
                [
                    "missing tests",
                    "no tests",
                    "missing docs",
                    "no readme",
                    "no automated spec",
                ],
            ),
            (
                "manual setup or recovery",
                ["manual", "sqlite browser", "delete out.json", "human-only"],
            ),
        ]
        return missing_groups_result(spec, report_lower, required_groups)

    if spec.rule_id == "small_first_steps":
        small_step_terms = [
            "small first steps",
            "quick win",
            "small refactor",
            "focused",
            "incremental",
            "minimal",
            "tiny",
            "small tests",
        ]
        rewrite_demand_terms = [
            "rewrite everything",
            "rewrite the repo",
            "full rewrite",
            "broad rewrite required",
        ]
        has_small_steps = any(term in report_lower for term in small_step_terms)
        avoids_rewrite_demand = not any(
            term in report_lower for term in rewrite_demand_terms
        )
        return expectation_result(
            spec,
            has_small_steps and avoids_rewrite_demand,
            "recommends small first steps, quick wins, or small refactors without demanding a broad rewrite",
        )

    if spec.rule_id == "mutable_email_identifier":
        required_groups = [
            ("email matching", ["email"]),
            ("mutable identity", ["mutable"]),
            ("stable identity recommendation", ["persistent", "stable", "durable"]),
            (
                "user or provider IDs",
                ["user id", "user ids", "provider id", "provider ids", "provider"],
            ),
        ]
        return missing_groups_result(spec, report_lower, required_groups)

    if spec.rule_id == "manual_ui_or_spreadsheet":
        taste_smells = section_text(report, "Taste Smells").lower()
        passed = any(
            term in taste_smells for term in ["ui-runbook", "spreadsheet", "manual ui"]
        ) or (
            "manual" in taste_smells
            and any(term in taste_smells for term in [".md", "docs/"])
        )
        return expectation_result(
            spec,
            passed,
            "Taste Smells cites manual UI, spreadsheet, or runbook evidence",
        )

    if spec.rule_id == "structural_efficiency":
        structural_signal = any(
            term in report_lower
            for term in [
                "structural efficiency",
                "serialization",
                "serialize",
                "copying",
                "copies",
                "intermediate artifact",
                "intermediate data",
                "i/o cost",
                "avoidable i/o",
            ]
        )
        improvement = any(
            term in report_lower
            for term in [
                "smaller",
                "scripted",
                "remove",
                "justify",
                "audit",
                "in-memory",
                "single pass",
            ]
        )
        return expectation_result(
            spec,
            structural_signal and improvement,
            "mentions copying/serialization cost with explicit word-form and a smaller, removed, justified, or audited workflow",
        )

    if spec.rule_id == "readability_or_dev_speed_values":
        value_signal = any(
            term in report_lower
            for term in ["readability", "dev-speed", "development speed"]
        )
        evidence_signal = any(
            path in report
            for path in [
                "README.md",
                "cleanup_export.py",
                "tests/test_cleanup_export.py",
            ]
        )
        return expectation_result(
            spec,
            value_signal and evidence_signal,
            "infers readability or dev-speed from fixture evidence",
        )

    if spec.rule_id == "avoid_generic_best_practices":
        unjustified_recommendations = [
            "recommend framework adoption",
            "recommend adopting a framework",
            "adopt a framework",
            "add a framework",
            "recommend microservices",
            "adopt microservices",
            "add microservices",
            "recommend formal methods",
            "adopt formal methods",
            "recommend scalability",
            "future scalability",
            "scalability work",
        ]
        exception_terms = [
            "avoid",
            "not recommend",
            "do not",
            "unless",
            "tradeoff",
            "trade-off",
        ]
        bad_matches = [
            term for term in unjustified_recommendations if term in report_lower
        ]
        if not bad_matches:
            return expectation_result(
                spec,
                True,
                "no unjustified scalability/framework/formal-methods recommendations found",
            )
        every_match_is_framed_as_tradeoff = True
        for term in bad_matches:
            start = 0
            while True:
                index = report_lower.find(term, start)
                if index == -1:
                    break
                window = report_lower[max(0, index - 200) : index + len(term) + 200]
                if not any(exc in window for exc in exception_terms):
                    every_match_is_framed_as_tradeoff = False
                    break
                start = index + len(term)
            if not every_match_is_framed_as_tradeoff:
                break
        return expectation_result(
            spec,
            every_match_is_framed_as_tradeoff,
            "each best-practice recommendation is framed as a tradeoff within nearby context"
            if every_match_is_framed_as_tradeoff
            else "found unjustified best-practice recommendation without nearby tradeoff context",
        )

    if spec.rule_id == "small_local_recommendations":
        small_signal = any(
            term in report_lower
            for term in ["small", "local", "single-file", "focused"]
        )
        topic_signal = any(
            term in report_lower
            for term in [
                "readability",
                "test",
                "docs",
                "script",
                "ergonomics",
                "example",
            ]
        )
        return expectation_result(
            spec,
            small_signal and topic_signal,
            "keeps improvements small and local to docs, tests, readability, or script ergonomics",
        )

    if spec.rule_id == "text_in_report":
        return expectation_result(
            spec, spec.text.lower() in report_lower, "fallback exact expectation match"
        )

    raise ValueError(f"unknown expectation rule_id: {spec.rule_id}")


def expectation_result(
    spec: ExpectationSpec, passed: bool, evidence: str
) -> ExpectationResult:
    return ExpectationResult(spec.text, passed, evidence, spec.rule_id)


def missing_groups_result(
    spec: ExpectationSpec,
    report_lower: str,
    required_groups: list[tuple[str, list[str]]],
) -> ExpectationResult:
    missing_groups = [
        label
        for label, terms in required_groups
        if not any(term in report_lower for term in terms)
    ]
    if missing_groups:
        return ExpectationResult(
            spec.text,
            False,
            f"missing concept groups: {', '.join(missing_groups)}",
            spec.rule_id,
        )
    return expectation_result(spec, True, "all required concept groups are present")
