from __future__ import annotations

# Compatibility wrapper: implementation has moved to repo_radar.grading.
# This module re-exports the public API so existing dev/eval CLI workflows continue to work.
from repo_radar.grading import (  # noqa: F401
    LEGACY_RULE_MARKERS,
    FILE_TOKEN_PATTERN,
    REPORT_CONTRACT,
    REQUIRED_REPORT_SECTIONS,
    SUPPORTED_RULE_IDS,
    ExpectationResult,
    ExpectationSpec,
    ReportView,
    cited_expected_paths,
    contains_term,
    default_calibration_slugs,
    evidence_path_matches,
    expectation_paths,
    expectation_result,
    expected_path_exists,
    grade_expectation,
    grade_report,
    legacy_rule_id,
    missing_groups_result,
    normalize_expectation,
    parse_report,
    section_text,
)
