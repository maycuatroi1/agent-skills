# agent-skills

Shared skills and companion MCP servers loaded across Claude Code, Codex, OpenCode, and Antigravity sessions. This repo sits upstream of multiple hub clusters (`red-life`, `evo-agents`, `evo-lms`, `fu-teaching`).

## Start here

1. Read `README.md` for skill catalog, Hub publishing (`evo-agents hub skills publish`), and runtime sync.
2. Read `docs/README.md` for harness engineering design notes.
3. Run `make test` to run unit tests and syntax checks before opening a PR.

## Layout

```
skills/                 17 active skills (and retired gitnexus tombstone)
  harness-engineering/  cluster manifest, contracts, deployments, audit, doctor, garden
  curator/              evidence-backed Hub curator workflows and KG operations
  create-exec-plan/     cross-repo execution plan authoring
  execute-plan/         step-by-step plan runner + plan-step subagent
  continuous-learning/  SessionEnd/Stop pattern extraction and curation
  life-cli/             mirror of red-life CLI surface (14 command groups)
  add-tasks/            context-enriched todo creation over life CLI
  credentials-utils/    mirror of evo cred surface (ships no scripts)
  dokploy-cli/          @dokploy/cli installer and reference
  speak/                TTS narration skill paired with mcp/tts/server.py
  stop-slop/            prose anti-slop rules and Vietnamese ERE blacklist
  update-evo-agents/    workstation updater for evo-agents nightly
mcp/tts/server.py       FastMCP wrapper importing evo_cli.tts (PEP 723 inline deps)
install.py              offline skill installer for ~/.claude/skills and ~/.opencode/skills
setup.py                appends global typography rules to ~/.claude/CLAUDE.md
docs/                   methodology references (harness-engineering-methodology.md)
```

## Cross-repo seams

This repo participates in cross-repo contracts verified by sibling harnesses (`~/github/red-life-harness/checks/run_all.py` and `~/github/evo-agents-harness/contracts.yaml`):

- **Producer (`skills-distribution`)**: Installed copies in `~/.claude/skills` and symlinks in `~/.gemini/config/plugins/agent-skills` must match `skills/` on `main`. After merging a change to `skills/`, publish via `evo-agents hub skills publish` and run `evo-agents hub skills sync` (or `python3 install.py`).
- **Producer (`harness-manifest-schema`)**: `skills/harness-engineering/scripts/harness.py` writes `harness.yaml` and `~/.claude/harness/registry.json`, consumed by `evo-cli`.
- **Consumer (`life-cli-surface`, `omelet-credentials`, `tts-engine-api`, `hub-cli-v1`)**: Skills mirror external CLI surfaces (`life`, `evo cred`, `evo-agents hub`) and `mcp/tts/server.py` imports `evo_cli.tts`. Update owners before updating mirrors here.

## Commands

```bash
make test               # run unit tests across skills and compile-check Python scripts
make check              # verify installed ~/.claude/skills matches skills/
make sync               # sync skills/ into local runtimes via install.py
```

## Rules

- Default branch `main` is guarded by a repository ruleset; ship changes through a branch and pull request.
- Do not use em-dashes, smart quotes, or middle-dot separators (`U+00B7`) in authored prose.
- Keep mirror skills (`life-cli`, `credentials-utils`, `execute-plan`, `curator`) aligned with their upstream CLI contracts.
