# Repo Radar Report

## Verdict

State whether the repo demonstrates strong, mixed, or weak code taste. Include confidence and the main reason in two sentences or fewer.

## Inferred project values

Infer 2-3 engineering values from repo evidence before scoring. Choose from: correctness, resiliency, speed, scalability, readability, flexibility, portability, dev-speed, cost, security. Infer fewer values when evidence is thin.

| Value | Evidence | Confidence |
| --- | --- | --- |

## Scores

| Dimension | Score | Confidence | Aligned value(s) | Why |
| --- | --- | --- | --- | --- |
| Simplicity | 1-5 | Low/Medium/High | Inferred value(s) | Evidence-backed reason |
| Architectural elegance | 1-5 | Low/Medium/High | Inferred value(s) | Evidence-backed reason |
| Usability | 1-5 | Low/Medium/High | Inferred value(s) | Evidence-backed reason |
| Newcomer understandability | 1-5 | Low/Medium/High | Inferred value(s) | Evidence-backed reason |

## Strengths

List cited strengths. Each item must name the file or artifact that supports it.

## Taste Smells

For each finding, preserve this chain:

```text
repo evidence -> taste implication -> recommendation
```

Use this shape:

```markdown
### Finding title

- Evidence: `path/to/file`: concrete observation.
- Taste implication: why this affects simplicity, elegance, usability, or newcomer understandability, and whether it fixes a violated invariant or conflicts with an inferred project value.
- Recommendation: the smallest practical improvement. If it shifts away from an inferred value, label it as a tradeoff and state what is gained and lost.
- Confidence: Low/Medium/High.
```

## Recommendations

Prioritize the smallest changes that improve taste. Separate quick wins from larger architectural work. Recommend a practice only when it fixes something that violates an invariant the code depends on or something that conflicts with an inferred project value; do not cite best practice as a reason by itself.

## Calibration Comparison

Name which calibration patterns the repo matches or violates. Cite the calibration corpus entry by its literal `slug` value, such as `encode/httpx`, and cite the target repo evidence.

## Verification and Agent Fit

Report whether the architecture exposes verifiable specs, tests, commands, sensors, and actuators that an agent can use. Include identity, structural efficiency, and stack minimization concerns when they appear:

- Project values: inferred engineering values match the repo's domain, user workflows, and operating constraints.
- Identity: durable cross-provider joins use persistent user IDs, not mutable identifiers such as email addresses.
- Correctness: the design is fundamentally correct, not merely statistically common.
- Structural efficiency: the design avoids hidden copying or avoidable storage, network, tensor, database, or serialization costs.
- Representation fit: data shapes and public interfaces encode invariants once and avoid scattered special cases across the codebase.
- Stack minimization: the repo collapses the stack when one intelligent call, library, or local workflow can replace a multi-service pipeline.
- Agent-native documentation: docs and commands are easy for an LLM agent to read, copy, execute, and verify.

## Confidence Limits

State what was not inspected and how that limits the verdict.
