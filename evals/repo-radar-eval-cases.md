# Repo Radar Evaluation Cases

Use these cases to calibrate whether the skill and subagent produce useful reports.

## Case 1: Tasteful calibration repo

Run the reviewer against one default calibration repo. Expected behavior:

- Verdict is positive but not uncritical.
- Report infers the repo's project values from concrete evidence before scoring.
- Report identifies concrete taste patterns with citations.
- Recommendations are minor and practical.
- Calibration comparison explains why the repo belongs in the corpus.

## Case 2: Intentionally messy repo

Run the reviewer against a small repo with unclear entry points, missing docs, tangled modules, and weak tests. Expected behavior:

- Verdict identifies weak taste with medium or high confidence.
- Taste smells cite specific files or missing artifacts.
- Report ties recommendations to inferred project values or violated invariants instead of generic best practices.
- Recommendations are small first steps, not a rewrite demand.
- Confidence limits state which areas were sampled.

## Case 3: Mixed-quality real repo

Run the reviewer against a normal active repo with some good boundaries and some confusing areas. Expected behavior:

- Verdict is nuanced.
- Strengths and weaknesses both appear.
- The report explains tradeoffs when a recommendation would shift away from an inferred project value.
- Findings preserve `repo evidence -> taste implication -> recommendation`.
- The report helps a repo owner decide what to improve first.

## Case 4: Agent-prone architectural traps

Run the reviewer against examples that include an email-based cross-provider join, a full-stack pipeline that a single multimodal prompt could replace, inefficient data copying, and docs with hidden manual UI steps. Expected behavior:

- Report rejects mutable identifiers for durable joins and recommends persistent user IDs.
- Report identifies when a statistically common pattern is architecturally wrong.
- Report flags structural efficiency problems even when behavior technically works.
- Report recommends collapsing the stack when a smaller model-native or local workflow is enough.
- Report asks for agent-native documentation and verifiable specs.

## Case 5: Misapplied best-practice trap

Run the reviewer against a small project where a generic best practice would be actively unhelpful: for example, a throwaway one-shot script that should optimize for readability and dev-speed rather than scalability, or a safety-critical path that should optimize for correctness and resiliency over delivery speed. Expected behavior:

- Report infers the relevant engineering values from the repo's stated purpose, docs, tests, and runtime constraints.
- Report does not recommend scalability, microservices, formal methods, or framework adoption unless those choices serve an inferred value or fix a violated invariant.
- If the report recommends a value-shifting change, it labels the recommendation as a tradeoff and states what is gained and lost.

## Case 6: External repo holdouts

Run the reviewer against pinned external repos from `evals/repo-holdouts.json`. These are not part of the runtime default calibration corpus. Expected behavior:

- Positive holdouts receive positive but not uncritical verdicts based on concrete repo evidence rather than reputation.
- Negative holdouts are intentionally educational or satirical examples, so reports identify weak taste without shaming maintainers.
- Mixed holdouts receive nuanced verdicts with scoped confidence, not blanket good/bad labels.
- Reports compare against calibration patterns but do not copy one language or domain's style as universal law.
- Large-repo reviews name sampled subsystems and downgrade confidence when coverage is partial.
