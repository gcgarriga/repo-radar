from __future__ import annotations

import json
import re

from tests.helpers import ROOT, load_python_module, read_text


def test_install_doc_has_copy_pasteable_copilot_cli_recipe() -> None:
    install_doc = read_text("docs/install.md")

    for required in [
        "Primary supported host: Copilot CLI",
        "copilot plugin install gcgarriga/repo-radar",
        "The `gcgarriga` owner in this command is the repository owner, not the installing user",
        "copilot plugin list",
        "repo-radar@",
        "repo-radar:repo-radar-reviewer",
        "Do not manually edit `~/.copilot/config.json` or `~/.copilot/settings.json`",
        "REPO_RADAR_SOURCE",
        "COPILOT_PROJECT",
        'mkdir -p "$COPILOT_PROJECT/skills/repo-radar"',
        'cp "$REPO_RADAR_SOURCE/skills/repo-radar/SKILL.md"',
        'cp "$REPO_RADAR_SOURCE/agents/repo-radar-reviewer.md"',
        'cp "$REPO_RADAR_SOURCE/templates/report-contract.json"',
    ]:
        assert required in install_doc, required


def test_copilot_plugin_manifest_supports_direct_install() -> None:
    manifest = json.loads(read_text("plugin.json"))

    assert manifest["name"] == "repo-radar"
    assert manifest["version"] == "0.1.0"
    assert "skill" in manifest["description"].lower()
    assert "subagent" in manifest["description"].lower()
    assert manifest["repository"] == "https://github.com/gcgarriga/repo-radar"
    assert manifest["license"] == "MIT"
    assert (ROOT / "skills/repo-radar/SKILL.md").is_file()
    assert (ROOT / "agents/repo-radar-reviewer.md").is_file()
    assert (ROOT / "templates/repo-radar-report.md").is_file()
    assert (ROOT / "templates/report-contract.json").is_file()
    assert (ROOT / "calibration/default-corpus.json").is_file()


def test_install_doc_checklist_covers_runtime_artifacts() -> None:
    install_doc = read_text("docs/install.md")

    for required in [
        "Post-install checklist",
        "Plugin manifest: `plugin.json`",
        "Skill: `skills/repo-radar/SKILL.md`",
        "Subagent: `agents/repo-radar-reviewer.md`",
        "Report template: `templates/repo-radar-report.md`",
        "Report contract: `templates/report-contract.json`",
        "Default calibration corpus: `calibration/default-corpus.json`",
    ]:
        assert required in install_doc, required


def test_readme_documents_user_facing_repo_radar_command() -> None:
    readme = read_text("README.md")
    evals_doc = read_text("evals/README.md")

    for required in [
        "## Quick start",
        "repo-radar /path/to/repo --output report.md",
        (
            "Static-review safety: this wrapper gives Copilot broad local tool and path permissions "
            "so noninteractive static reviews can run without prompts. Run it only against a disposable "
            "or trusted local checkout; the prompt still forbids dependency installation, network calls, "
            "file mutation, and commits."
        ),
        "--timeout-seconds 300",
        "uses your existing Copilot CLI authentication",
        "does not require a separate model API token",
        "copilot plugin install gcgarriga/repo-radar",
        "The `gcgarriga` owner in this command is the repository owner, not the installing user",
        "repo-radar:repo-radar-reviewer",
    ]:
        assert required in readme, required
    assert (
        "`scripts/copilot_reviewer_wrapper.py` is the Copilot CLI adapter for evals"
        in evals_doc
    )


def test_install_docs_use_canonical_repo_owner_with_fork_guidance() -> None:
    combined_install_docs = "\n".join(
        [
            read_text("README.md"),
            read_text("docs/install.md"),
        ]
    )

    assert "copilot plugin install OWNER/repo-radar" not in combined_install_docs
    assert "copilot plugin install gcgarriga/repo-radar" in combined_install_docs
    assert (
        "The `gcgarriga` owner in this command is the repository owner, not the installing user"
        in combined_install_docs
    )
    assert (
        "If installing from a fork, replace `gcgarriga` with the fork owner"
        in combined_install_docs
    )


def test_skill_artifact_has_required_protocol_sections() -> None:
    skill = read_text("skills/repo-radar/SKILL.md")

    assert skill.startswith("---\nname: repo-radar\n")
    assert "dispatch" in skill.lower()
    assert "repo-radar:repo-radar-reviewer" in skill
    for required in [
        "## Review workflow",
        "## Runtime artifacts",
        "## Calibration corpus",
        "## Evidence protocol",
        "## Taste rubric",
        "## Codifiable architectural checks",
        "## Report contract",
        "## Guardrails",
    ]:
        assert required in skill


def test_agent_artifact_has_frontmatter_and_report_contract() -> None:
    agent = read_text("agents/repo-radar-reviewer.md")

    assert agent.startswith("---\nname: repo-radar-reviewer\n")
    assert "model: inherit" in agent
    assert "executor" in agent.lower()
    for required in [
        "## Mission",
        "## Evidence collection",
        "## Judgment rules",
        "## Architectural failure modes",
        "## Output format",
    ]:
        assert required in agent


def test_default_corpus_entries_are_cited_and_explained() -> None:
    corpus = json.loads(read_text("calibration/default-corpus.json"))
    allowed_taste_categories = {
        "agent-native-docs",
        "api-design",
        "correctness-heavy",
        "developer-experience",
        "educational",
        "examples",
        "library-api",
        "minimalism",
        "ml-ai",
        "onboarding",
        "performance",
        "systems",
        "testing",
    }

    assert corpus["version"] == 1
    assert corpus["selection_policy"] == (
        "Small default positive corpus of public repositories with clear onboarding, "
        "focused APIs, readable tests, documented intent, and explicit boundaries; "
        "negative and mixed repositories are held out for evals rather than used as runtime taste anchors. "
        "Entries pin reviewed refs so evidence anchors are stable. "
        "Users may override this corpus."
    )
    assert len(corpus["repos"]) >= 12
    for repo in corpus["repos"]:
        assert re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo["slug"])
        assert repo["repo_url"].startswith("https://")
        assert re.fullmatch(r"[a-f0-9]{40}", repo["pinned_ref"])
        assert repo["why_included"]
        assert len(repo["taste_signals"]) >= 3
        assert len(repo["review_focus"]) >= 2
        assert len(repo["taste_categories"]) >= 2
        assert set(repo["taste_categories"]).issubset(allowed_taste_categories)
        assert all(signal for signal in repo["taste_signals"])
        assert all(focus for focus in repo["review_focus"])
        assert repo["language"]
        assert repo["domain"]
        assert repo["taste_boundary"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", repo["last_reviewed"])
        assert len(repo["evidence_anchors"]) >= 2
        for anchor in repo["evidence_anchors"]:
            assert anchor["path"]
            assert anchor["why"]

    slugs = {repo["slug"] for repo in corpus["repos"]}
    languages = {repo["language"] for repo in corpus["repos"]}
    assert {"Python", "Rust", "Go", "C", "Ruby"}.issubset(languages)
    assert {"scikit-learn/scikit-learn", "karpathy/nanoGPT"}.issubset(slugs)
    assert all(
        "ml-ai" in repo["taste_categories"]
        for repo in corpus["repos"]
        if repo["slug"] in {"scikit-learn/scikit-learn", "karpathy/nanoGPT"}
    )


def test_default_corpus_uses_research_positives_but_not_holdout_negatives() -> None:
    corpus = json.loads(read_text("calibration/default-corpus.json"))
    slugs = {repo["slug"] for repo in corpus["repos"]}

    assert {
        "sqlite/sqlite",
        "redis/redis",
        "pydantic/pydantic",
        "Textualize/rich",
        "minitest/minitest",
    }.issubset(slugs)
    assert (
        not {
            "emilybache/GildedRose-Refactoring-Kata",
            "EnterpriseQualityCoding/FizzBuzzEnterpriseEdition",
            "trekhleb/state-of-the-art-shitcode",
        }
        & slugs
    )


def test_report_template_preserves_evidence_to_judgment_chain() -> None:
    template = read_text("templates/repo-radar-report.md")

    for required in [
        "# Repo Radar Report",
        "## Verdict",
        "## Inferred project values",
        "## Scores",
        "## Strengths",
        "## Taste Smells",
        "## Recommendations",
        "## Calibration Comparison",
        "## Verification and Agent Fit",
        "repo evidence -> taste implication -> recommendation",
    ]:
        assert required in template


def test_required_report_headings_stay_aligned_across_runtime_contracts() -> None:
    run_evals = load_python_module(
        "scripts/run_evals.py", "run_evals_for_contract_drift"
    )
    report_contract = json.loads(read_text("templates/report-contract.json"))
    canonical_headings = report_contract["required_sections"]
    template = read_text("templates/repo-radar-report.md")
    agent = read_text("agents/repo-radar-reviewer.md")
    skill = read_text("skills/repo-radar/SKILL.md")

    def headings(markdown: str) -> list[str]:
        return [
            line.strip() for line in markdown.splitlines() if line.startswith("## ")
        ]

    agent_output_contract_match = re.search(
        r"Return this structure:\n\n```markdown\n(?P<contract>.*?)\n```",
        agent,
        flags=re.DOTALL,
    )
    assert agent_output_contract_match
    skill_report_contract = skill.split("## Report contract", 1)[1].split(
        "## Guardrails", 1
    )[0]

    assert report_contract["version"] == 1
    assert report_contract["finding_fields"] == [
        "Evidence",
        "Taste implication",
        "Recommendation",
        "Confidence",
    ]
    assert headings(template) == canonical_headings
    assert headings(agent_output_contract_match.group("contract")) == canonical_headings
    assert run_evals.REQUIRED_REPORT_SECTIONS == canonical_headings
    for heading in canonical_headings:
        assert heading.removeprefix("## ").lower() in skill_report_contract.lower()


def test_project_values_lens_is_structured_across_prompt_surfaces() -> None:
    combined = "\n".join(
        [
            read_text("skills/repo-radar/SKILL.md"),
            read_text("agents/repo-radar-reviewer.md"),
            read_text("templates/repo-radar-report.md"),
        ]
    ).lower()
    template = read_text("templates/repo-radar-report.md")

    for required in [
        "inferred project values",
        "engineering values",
        "correctness",
        "resiliency",
        "speed",
        "scalability",
        "readability",
        "flexibility",
        "portability",
        "dev-speed",
        "cost",
        "security",
        "violates an invariant",
        "conflicts with an inferred project value",
        "tradeoff",
    ]:
        assert required in combined

    assert "| Value | Evidence | Confidence |" in template
    assert "Aligned value(s)" in template


def test_taste_smell_contract_allows_invariant_or_value_conflict() -> None:
    reviewer = read_text("agents/repo-radar-reviewer.md")
    template = read_text("templates/repo-radar-report.md")

    assert (
        "violates an invariant the code depends on or conflicts with an inferred project value"
        in reviewer
    )
    assert "violated invariant or conflicts with an inferred project value" in template
    for required in [
        "- Evidence:",
        "- Taste implication:",
        "- Recommendation:",
        "- Confidence:",
    ]:
        assert required in reviewer
        assert required in template


def test_codifiable_taste_rules_are_preserved() -> None:
    combined = "\n".join(
        [
            read_text("skills/repo-radar/SKILL.md"),
            read_text("agents/repo-radar-reviewer.md"),
            read_text("templates/repo-radar-report.md"),
        ]
    )

    for required in [
        "persistent user IDs",
        "mutable identifiers",
        "statistically common",
        "structural efficiency",
        "collapse the stack",
        "agent-native documentation",
        "verifiable specs",
        "representation",
        "special cases",
        "encode invariants",
    ]:
        if required == "representation":
            assert required in combined.lower()
        else:
            assert required in combined


def test_representation_rule_is_in_each_prompt_surface() -> None:
    expected = "Representation fit"
    for relative_path in [
        "skills/repo-radar/SKILL.md",
        "agents/repo-radar-reviewer.md",
        "templates/repo-radar-report.md",
    ]:
        assert expected in read_text(relative_path), relative_path


def test_prompt_artifacts_are_complete() -> None:
    artifact_paths = [
        "README.md",
        "LICENSE",
        "docs/install.md",
        "docs/development.md",
        "evals/README.md",
        "skills/repo-radar/SKILL.md",
        "agents/repo-radar-reviewer.md",
        "templates/repo-radar-report.md",
        "evals/repo-radar-eval-cases.md",
        "evals/evals.json",
        "evals/repo-holdouts.json",
    ]
    forbidden_terms = [
        "T" + "BD",
        "TO" + "DO",
        "FIX" + "ME",
        "place" + "holder",
        "fill" + " in later",
    ]

    for relative_path in artifact_paths:
        artifact = read_text(relative_path).lower()
        for term in forbidden_terms:
            assert term.lower() not in artifact, relative_path


def test_v1_defers_command_interface() -> None:
    combined = "\n".join(
        [
            read_text("skills/repo-radar/SKILL.md"),
            read_text("agents/repo-radar-reviewer.md"),
        ]
    ).lower()

    assert "standalone cli" in combined
    assert "thin wrapper" in combined


def test_install_doc_explains_installation_shape() -> None:
    install_doc = read_text("docs/install.md").lower()

    for required in [
        "install",
        "skill",
        "subagent",
        "plugin.json",
        "copilot plugin install",
        "repo-radar:repo-radar-reviewer",
        "skills/repo-radar/skill.md",
        "agents/repo-radar-reviewer.md",
        "templates/repo-radar-report.md",
    ]:
        assert required in install_doc, required


def test_install_doc_explains_installation_verification() -> None:
    install_doc = read_text("docs/install.md").lower()

    for required in [
        "verify installation",
        "minimal review prompt",
        "copilot plugin list",
        "copilot --plugin-dir",
        "agent load",
        "missing skill",
        "missing subagent",
        "missing plugin manifest",
        "manual config edits",
        "manifest search paths",
        "reachable by your github auth",
        "default-corpus.json",
    ]:
        assert required in install_doc, required


def test_install_doc_gives_host_layout_examples() -> None:
    install_doc = read_text("docs/install.md")

    for required in [
        "Known host layout examples",
        "Copilot CLI",
        "Claude Code",
        "configured skill root",
        "configured agent root",
    ]:
        assert required in install_doc, required


def test_evals_doc_places_wrapper_safety_near_copyable_wrapper_usage() -> None:
    evals_doc = read_text("evals/README.md")
    wrapper_section_start = evals_doc.index(
        "`scripts/copilot_reviewer_wrapper.py` is the Copilot CLI adapter"
    )
    wrapper_section = evals_doc[
        wrapper_section_start : evals_doc.index(
            "External holdouts live", wrapper_section_start
        )
    ]

    for required in [
        "Static-review safety",
        "broad local tool and path permissions",
        "disposable or trusted local checkout",
    ]:
        assert required in wrapper_section, required


def test_development_and_evals_docs_cover_contract_changes_and_holdout_scratch() -> (
    None
):
    development_doc = read_text("docs/development.md")
    evals_doc = read_text("evals/README.md")

    assert "Report contract changes" in development_doc
    for required in [
        "templates/report-contract.json",
        "skills/repo-radar/SKILL.md",
        "agents/repo-radar-reviewer.md",
        "templates/repo-radar-report.md",
        "scripts/run_evals.py",
        "tests/test_prompt_artifacts.py",
        "tests/test_run_evals.py",
    ]:
        assert required in development_doc, required
    assert "tests/test_artifacts.py" not in development_doc
    assert "The `/tmp/` paths below are replaceable host scratch paths" in evals_doc


def test_evals_doc_documents_copilot_eval_wrapper() -> None:
    evals_doc = read_text("evals/README.md")

    assert "scripts/copilot_reviewer_wrapper.py" in evals_doc
    assert "REPO_RADAR_COPILOT_MODEL" in evals_doc
    assert "REPO_RADAR_COPILOT_REASONING_EFFORT" in evals_doc


def test_skill_passes_calibration_content_to_reviewer() -> None:
    skill = read_text("skills/repo-radar/SKILL.md").lower()
    reviewer = read_text("agents/repo-radar-reviewer.md").lower()

    assert "load the contents of `calibration/default-corpus.json`" in skill
    assert "calibration corpus content" in skill
    assert "full calibration content" in skill
    assert "full calibration corpus content passed by the repo-radar skill" in reviewer
