---
name: repo-radar
description: Use Repo Radar when a user asks whether a repository has good code taste, wants a taste review, asks how simple/elegant/usable/understandable a repo is, or wants an evidence-backed repo quality report focused on architecture and newcomer comprehension.
---

# Repo Radar Review

Use this skill to produce an evidence-backed taste report for a checked-out repository.

## Runtime artifacts

Use the runtime artifacts bundled with this skill install, not same-named files from the target repository under review:

- `calibration/default-corpus.json`
- `templates/repo-radar-report.md`
- `templates/report-contract.json`

When installed as a Copilot CLI plugin, the reviewer subagent is exposed as `repo-radar:repo-radar-reviewer`. In project-scoped or non-plugin hosts, `repo-radar-reviewer` may also be available as the unqualified fallback name.

## Review workflow

1. Confirm the target repo path.
2. Confirm whether to use `calibration/default-corpus.json` or user-provided reference repos.
3. If using default calibration, load the contents of `calibration/default-corpus.json`. If using user-provided reference repos, prepare those references as the calibration corpus content.
4. Dispatch the `repo-radar:repo-radar-reviewer` subagent with the target path, calibration corpus content, evidence protocol, project-values lens, taste rubric, guardrails, and report contract. If the host does not support plugin namespaces, retry with `repo-radar-reviewer`.
5. Review the returned report for uncited claims, missing inferred project values, missing confidence limits, and recommendations that are broader than the evidence supports.
6. Return the report to the user and invite focused follow-up questions or deeper subsystem review.

## Calibration corpus

Use calibration repos to ground taste judgments. The default corpus is positive-only: it should teach what good taste looks like, not supply a list of repos to shame. Negative, satirical, and mixed examples belong in eval holdouts, not in the runtime calibration context. Do not treat the corpus as a popularity contest. Extract observable patterns that make the repos simple, elegant, usable, or easy to understand. In the report's calibration comparison, name corpus entries with their literal `slug` values so evals can tell whether a real comparison happened.

If the user provides reference repos, prefer them over the default corpus and state that the rubric is user-calibrated. Pass the full calibration content to the reviewer so the reviewer does not depend on host-specific relative paths.

## Evidence protocol

Every meaningful judgment needs evidence. Use file paths, symbols, docs, test names, commands, or missing artifacts. Preserve this chain:

```text
repo evidence -> taste implication -> recommendation
```

Prefer representative sampling over exhaustive reading. For large repos, sample by subsystem and state confidence limits.

Before scoring, infer the 2-3 engineering values the project most plausibly optimizes for. Use repo evidence such as README goals, user workflows, deployment/runtime constraints, tests, dependencies, and operational docs. Choose values from this vocabulary: correctness, resiliency, speed, scalability, readability, flexibility, portability, dev-speed, cost, security. If evidence is thin, infer fewer values and mark confidence low.

## Taste rubric

Evaluate four dimensions:

- Simplicity: the common path is obvious and accidental complexity is low.
- Architectural elegance: boundaries are coherent, dependencies are predictable, and abstractions earn their keep.
- Usability: public interfaces, commands, examples, and errors help users succeed.
- Newcomer understandability: an experienced engineer new to the repo can form an accurate mental model quickly.

Use the inferred project values as the lens for these scores. Do not add a separate score for context fit; instead, explain which inferred values each score is aligned with or in tension with.

## Codifiable architectural checks

Check these specific taste rules:

- Simplicity and minimization: flag bloat, copy-paste, awkward abstractions, and unnecessary services.
- Fundamental correctness over statistical likelihood: reject statistically common approaches that violate system invariants.
- Identity management: durable cross-provider joins must use persistent user IDs, not mutable identifiers such as email addresses.
- Structural efficiency: inspect whether the code respects memory layout, data movement, storage, network, tensor, database, and serialization costs.
- Representation fit: prefer data shapes and public interfaces that encode invariants once and avoid scattered special cases across the codebase.
- Project values fit: judge whether design tradeoffs fit the current project instead of applying universal best practice claims. A recommendation must either fix something that violates an invariant the code depends on, or address something that conflicts with an inferred project value.
- Minimalist infrastructure: ask whether one intelligent call, library, or local workflow can collapse the stack.
- Agent-native documentation: prefer docs, commands, examples, sensors, and actuators that an LLM agent can read, copy, execute, and verify.
- Verification-driven architecture: prefer verifiable specs, tests, checks, and observable outcomes before adding new architectural layers.

## Calibration edge cases

Apply these holdout-calibrated distinctions before scoring:

- Educational positives: mark a checklist item out of scope when calibration boundaries and inferred project values make it intentionally irrelevant. Do not penalize pedagogical minimalism for missing production infrastructure, tensor-scale efficiency, packaging ceremony, or operational machinery.
- Katas and teaching negatives: educational intent changes tone, not the taste signal. Preserve stated constraints such as a public-interface constraint, then recommend characterization tests and the smallest practical small internal seam instead of broad dependency-injection rewrites or public API changes.
- Parody and satire: recognize parody, but do not treat abstraction count, enterprise vocabulary, or extensibility claims as quality evidence by themselves. If the code were used seriously, recommend collapse ceremony rather than adding more process, layers, or governance.
- Large mature frameworks: a half-half answer is often right when public conventions, docs, and tests are strong but historical compatibility layers make local reasoning harder. Name sampled subsystems, treat historical compatibility as a tradeoff, keep confidence bounded, and make recommendations subsystem-specific.

## Report contract

The report must include these sections: Verdict, Inferred project values, Scores, Strengths, Taste Smells, Recommendations, Calibration Comparison, Verification and Agent Fit, and Confidence Limits.

Scores are navigation aids, not the product. The recommendations and cited evidence are the product.

## Guardrails

- Do not make uncited taste claims.
- Do not equate size with bad taste without context.
- Do not replace security, dependency, lint, or performance tools.
- Do not recommend broad rewrites when a smaller boundary, example, naming, or documentation change would improve taste.
- Do not recommend a practice just because it is commonly considered best practice. If a recommendation would move the repo away from an inferred project value, label it as a tradeoff and state what is gained and lost.
- Separate objective observations from subjective taste judgments.
- Downgrade confidence when evidence is shallow, tests cannot run, docs are absent, or the repo is outside familiar languages.
- Do not implement a standalone CLI or command-first path in v1; future command support should be a thin wrapper around this skill and the `repo-radar:repo-radar-reviewer` subagent.
