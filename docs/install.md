# Installing Repo Radar as an Agent Skill

Repo Radar can run through the packaged `repo-radar` command, or as an installed Copilot CLI skill/subagent plugin.

## Primary supported host: Copilot CLI

Use Copilot CLI's plugin installer for a computer-wide install:

```bash
copilot plugin install gcgarriga/repo-radar
copilot plugin list
```

The `gcgarriga` owner in this command is the repository owner, not the installing user. If installing from a fork, replace `gcgarriga` with the fork owner.

The GitHub repository must be reachable by your GitHub auth. If you are developing from a local checkout before publishing or pushing changes, smoke-test the checkout without installing it permanently:

```bash
copilot --plugin-dir "$(pwd)" \
  --agent repo-radar:repo-radar-reviewer \
  -p "Return only READY." \
  --allow-all-tools \
  --silent
```

After installation, Copilot CLI exposes:

- Skill: `repo-radar`
- Subagent: `repo-radar:repo-radar-reviewer`
- Plugin entry: `repo-radar@...`

Do not manually edit `~/.copilot/config.json` or `~/.copilot/settings.json`. The plugin installer should register and enable the plugin. Manual config edits are a troubleshooting smell, not the supported path.

## Why this install shape matters

The common failure modes are avoidable:

- Missing plugin manifest: if `copilot plugin install` reports missing manifest search paths, first confirm this repo ships `plugin.json` at the root. The root manifest is the supported direct-install path.
- Missing subagent: plugin-loaded agents are namespaced, so use `repo-radar:repo-radar-reviewer` rather than only `repo-radar-reviewer`.
- Missing runtime artifacts: the skill, reviewer, templates, report contract, and default calibration corpus must travel together. Copying only `skills/` is incomplete.
- Manual config edits: editing Copilot's user config can make one machine work while leaving no reproducible install path for the next human or agent.

## Fallback: project-scoped copy

Use this only when plugin installation is unavailable in the host. From this `repo-radar` checkout, set `COPILOT_PROJECT` to the project where Copilot CLI should discover the skill:

```bash
REPO_RADAR_SOURCE="$(pwd)"
COPILOT_PROJECT="/absolute/path/to/copilot-cli-project"

mkdir -p "$COPILOT_PROJECT/skills/repo-radar"
mkdir -p "$COPILOT_PROJECT/agents"
mkdir -p "$COPILOT_PROJECT/templates"
mkdir -p "$COPILOT_PROJECT/calibration"

cp "$REPO_RADAR_SOURCE/skills/repo-radar/SKILL.md" \
  "$COPILOT_PROJECT/skills/repo-radar/SKILL.md"
cp "$REPO_RADAR_SOURCE/agents/repo-radar-reviewer.md" \
  "$COPILOT_PROJECT/agents/repo-radar-reviewer.md"
cp "$REPO_RADAR_SOURCE/templates/repo-radar-report.md" \
  "$COPILOT_PROJECT/templates/repo-radar-report.md"
cp "$REPO_RADAR_SOURCE/templates/report-contract.json" \
  "$COPILOT_PROJECT/templates/report-contract.json"
cp "$REPO_RADAR_SOURCE/calibration/default-corpus.json" \
  "$COPILOT_PROJECT/calibration/default-corpus.json"
```

## Post-install checklist

- Plugin manifest: `plugin.json`
- Skill: `skills/repo-radar/SKILL.md`
- Subagent: `agents/repo-radar-reviewer.md`
- Report template: `templates/repo-radar-report.md`
- Report contract: `templates/report-contract.json`
- Default calibration corpus: `calibration/default-corpus.json`

You can copy-paste this verification command after setting `COPILOT_PROJECT` for the fallback install:

```bash
test -f "$COPILOT_PROJECT/skills/repo-radar/SKILL.md" &&
test -f "$COPILOT_PROJECT/agents/repo-radar-reviewer.md" &&
test -f "$COPILOT_PROJECT/templates/repo-radar-report.md" &&
test -f "$COPILOT_PROJECT/templates/report-contract.json" &&
test -f "$COPILOT_PROJECT/calibration/default-corpus.json"
```

After copying files, restart or reload Copilot CLI if your host does not rescan skills automatically.

## Known host layout examples

Use these as layout examples, not universal paths; host versions may store skills elsewhere.

| Host | Skill file | Agent file | Runtime artifacts |
| --- | --- | --- | --- |
| Copilot CLI plugin | `skills/repo-radar/SKILL.md` inside the installed plugin | `agents/repo-radar-reviewer.md` exposed as `repo-radar:repo-radar-reviewer` | Keep `templates/repo-radar-report.md`, `templates/report-contract.json`, and `calibration/default-corpus.json` in the same plugin. |
| Copilot CLI project copy | `<configured skill root>/repo-radar/SKILL.md` | `<configured agent root>/repo-radar-reviewer.md` | Keep `templates/repo-radar-report.md`, `templates/report-contract.json`, and `calibration/default-corpus.json` reachable from the skill for the fallback path. |
| Claude Code | `<configured skill root>/repo-radar/SKILL.md` | `<configured agent root>/repo-radar-reviewer.md` | Keep `templates/repo-radar-report.md`, `templates/report-contract.json`, and `calibration/default-corpus.json` reachable from the skill for the default install path. |

## Verify installation

Confirm the plugin is registered:

```bash
copilot plugin list
```

Confirm agent load:

```bash
copilot --agent repo-radar:repo-radar-reviewer \
  -p "Return only READY." \
  --allow-all-tools \
  --silent
```

Use this minimal review prompt in a new Copilot CLI session:

```text
Run the repo-radar skill on this repository with the default calibration corpus.
Return the Repo Radar Report and cite the calibration slugs you used.
```

Expected result: the agent discovers the `repo-radar` skill, dispatches the `repo-radar:repo-radar-reviewer` subagent, inspects the target repo, and returns a report with Verdict, Inferred project values, Scores, Strengths, Taste Smells, Recommendations, Calibration Comparison, Verification and Agent Fit, and Confidence Limits.

Troubleshooting:

- **Missing plugin manifest:** confirm `plugin.json` exists at the repository root before running `copilot plugin install`.
- **Missing skill:** confirm `copilot plugin list` includes `repo-radar@...` and restart or reload sessions started before installation.
- **Missing subagent:** use the plugin-qualified agent name `repo-radar:repo-radar-reviewer`; unqualified `repo-radar-reviewer` may not exist in plugin mode.
- **Missing runtime artifacts:** keep `templates/repo-radar-report.md` and `templates/report-contract.json` reachable by the skill. Keep `calibration/default-corpus.json` reachable for the default install path, or provide your own reference repos at runtime and adjust the verification prompt accordingly.
- **Manual config edits:** if installation only works after editing `~/.copilot/config.json` or `~/.copilot/settings.json`, treat that as a bug in the install path and prefer `copilot plugin install` or `copilot --plugin-dir` for local validation.
