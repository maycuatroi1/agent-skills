---
name: continuous-learning
description: Auto-extract reusable patterns AND repeated command patterns from Claude Code sessions, plus a Curator that maintains the learned-skill library (usage telemetry, stale/archive lifecycle, dedup, backups). Approved skills land at {cwd}/.claude/skills/<name>/ so Claude Code actually discovers them; CLI suggestions go to {cwd}/.claude/cli-suggestions/_pending/. Use when setting up the Stop hook, reviewing or promoting learned skills, running/tuning the curator, tuning thresholds, wiring a project CLI config, or explaining how session-end learning works.
allowed-tools: Bash, Read, Edit, Write
---

# Continuous Learning

Runs at session end (via Stop hook). Analyzes the transcript with `claude -p` and writes artifacts into the **current project's** `.claude/`:

1. **Learned skills** — reusable patterns, gotchas, debugging techniques saved as Agent Skills.
   - Approved/auto-approved → `.claude/skills/<name>/SKILL.md` (frontmatter `learned: true`). This is the ONLY path Claude Code discovers skills from, so they are immediately loadable.
   - Pending (default, `auto_approve=false`) → `.claude/skills/.learned/_pending/<name>/` — intentionally NOT discovered until promoted, so unreviewed skills never auto-activate.
2. **CLI suggestions** → `.claude/cli-suggestions/_pending/` — repeated shell/tool patterns that should become a subcommand of the project's own CLI (e.g. `./lms debug class-info`).

The Curator (`curate.py`) then maintains the learned library: tracks usage, moves unused skills active → stale → archived, optionally consolidates duplicates, and snapshots before every run.

Everything lives inside the project so it syncs across devices via the project's git repo.

## Skill discovery (why the path matters)

Claude Code only discovers skills at depth 1: `.claude/skills/<name>/SKILL.md`. An extra folder level like `.claude/skills/learned/<name>/SKILL.md` is invisible and never loads. That is why approved skills are written directly under `.claude/skills/` and the curator's bookkeeping lives in the hidden `.claude/skills/.learned/` (dot-prefixed dirs are skipped by discovery).

## Why project-local

- Per-project `.claude/` folders sync across devices through GitHub
- Patterns learned in project X are most relevant to project X
- CLI suggestions are intrinsically per-project (each project has its own CLI)
- No global namespace pollution

## Project CLI detection

If `{cwd}/.claude/continuous-learning.json` exists, it's merged over the global config. Use it to tell the extractor about the project's CLI:

```json
{
  "cli": {
    "entrypoint": "./lms",
    "framework": "click (python)",
    "module_dir": "cli/modules/",
    "existing_groups": ["check", "debug", "dokploy"],
    "existing_subcommands": {
      "debug": ["class-info", "activity-info", "course-permission"]
    },
    "notes": "Click-based. Each group is cli/modules/<group>.py. Register in cli/main.py."
  }
}
```

Without explicit config, the extractor auto-detects common shapes (`./lms`, `./cli`, `Makefile`, `package.json` scripts). When no CLI is found, `cli_suggestions` is skipped.

## Files in this skill

| File | Purpose |
|------|---------|
| `evaluate-session.sh` | Stop hook entry point (reads stdin JSON, backgrounds the extractor) |
| `extract_patterns.py` | Loads transcript, scans for learned-skill usage, calls `claude -p` to extract patterns, writes skill files, triggers auto-curate on interval |
| `curate.py` | Curator: usage telemetry, active/stale/archived lifecycle, dedup/consolidate, backups, and the `curator` CLI (status/run/pin/promote/restore/...) |
| `config.json` | Tunable: min session length, extraction threshold, auto-approve, pattern types, and the `curator` block |

## Install (one-time)

Add this to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "/home/binhna/git/agent-skills/skills/continuous-learning/evaluate-session.sh"
      }]
    }]
  }
}
```

Make the hook executable once:

```bash
chmod +x /home/binhna/git/agent-skills/skills/continuous-learning/evaluate-session.sh
```

## How it works

1. Claude Code session ends → Stop hook fires
2. Hook reads JSON from stdin: `{session_id, transcript_path, cwd, stop_hook_active}`
3. Hook backgrounds `extract_patterns.py` and exits 0 (non-blocking)
4. Extractor:
   - Skips if `stop_hook_active=true` (recursion guard)
   - Skips if env `CONTINUOUS_LEARNING_CHILD=1` (child session guard)
   - Skips if transcript has fewer messages than `min_session_length`
   - Skips if `{cwd}/.claude/skills/.learned/.processed/<session_id>` already exists
   - Scans the transcript for references to existing learned skills and bumps their usage telemetry (`.claude/skills/.learned/usage.json`)
   - Builds compact session summary, calls `claude -p` with extraction prompt
   - Writes each approved skill to `{cwd}/.claude/skills/<name>/SKILL.md` (discoverable); pending skills to `{cwd}/.claude/skills/.learned/_pending/<name>/`
   - Writes each CLI suggestion to `{cwd}/.claude/cli-suggestions/_pending/<name>.md`
   - When `auto_approve=false` (default), skills land in `.learned/_pending/` and CLI suggestions in `cli-suggestions/_pending/` for manual review
   - Runs the Curator's deterministic lifecycle pass if `curator.interval_hours` has elapsed since its last run

## CLI suggestion format

Each suggestion is a markdown file with frontmatter and sections:

```md
---
name: debug-query-model
command_path: "./lms debug query-model <MODEL>"
occurrences: 3
framework: "click (python)"
entrypoint: "./lms"
proposed_location: "cli/modules/debug.py"
---

# CLI Suggestion: `./lms debug query-model <MODEL>`

## Why
Ran `python manage.py shell -c "from X.models import Y; ..."` 3 times across different models.

## Observed calls (3x)
- `export ENV_FILE_NAME=.hust.env && python manage.py shell -c "from elearning.models import Course; print(Course.objects.count())"`
- ...

## Proposed location
`cli/modules/debug.py`

## Implementation sketch
```python
@debug.command("query-model")
@click.argument("model")
def query_model(model):
    ...
```
```

Review, then either copy the sketch into the CLI module or delete the suggestion file.

## Config

Edit `config.json`:

```json
{
  "min_session_length": 10,
  "extraction_threshold": "medium",
  "auto_approve": false,
  "claude_model": "claude-haiku-4-5",
  "patterns_to_detect": [
    "error_resolution",
    "user_corrections",
    "workarounds",
    "debugging_techniques",
    "project_specific"
  ],
  "ignore_patterns": [
    "simple_typos",
    "one_time_fixes",
    "external_api_issues"
  ],
  "curator": {
    "enabled": true,
    "interval_hours": 168,
    "stale_after_days": 30,
    "archive_after_days": 90,
    "consolidate": false,
    "auto_consolidate": false,
    "model": "claude-haiku-4-5",
    "backup_keep": 5
  }
}
```

| Field | Effect |
|------|--------|
| `min_session_length` | Sessions shorter than this are skipped |
| `extraction_threshold` | `low` = keep many, `medium` = selective, `high` = only high-value |
| `auto_approve` | `true` writes discoverable to `.claude/skills/<name>/`, `false` writes to `.learned/_pending/` |
| `claude_model` | Model used by `claude -p` for analysis (default Haiku for speed/cost) |
| `patterns_to_detect` | Categories to extract |
| `ignore_patterns` | Noise categories to ignore |
| `curator` | Curator block (see Curator section): `enabled`, `interval_hours`, `stale_after_days`, `archive_after_days`, `consolidate`, `auto_consolidate`, `model`, `backup_keep` |

## Curator

`curate.py` is a background maintenance pass for the learned-skill library, modeled on Hermes Agent's Curator. It never deletes: unused skills move active -> stale -> archived (`.claude/skills/.learned/.archive/`), and every run snapshots `.claude/skills/` first.

Usage telemetry lives in `.claude/skills/.learned/usage.json`. Because Claude Code has no "skill loaded" hook, usage is inferred at session end by scanning the transcript for references to each learned skill (its `SKILL.md` path or `Skill(<name>)` invocation), bumping `use_count` / `last_used_at`. Idle time drives the lifecycle.

The lifecycle pass is deterministic (no LLM) and runs automatically on interval via the Stop hook. The optional consolidate pass (`--consolidate` or `curator.consolidate: true`) uses `claude -p` to find near-duplicate skills and archive the redundant ones into a kept "umbrella" skill.

### Curator CLI

```bash
CUR=/home/binhna/git/agent-skills/skills/continuous-learning/curate.py

python3 $CUR status        --cwd "$PWD"   # last run, per-skill idle/state/use, pinned
python3 $CUR run           --cwd "$PWD"   # deterministic lifecycle now (backs up first)
python3 $CUR run --consolidate --cwd "$PWD"   # add the LLM dedup pass
python3 $CUR run --dry-run --cwd "$PWD"   # preview transitions, no mutations
python3 $CUR pin   <name>  --cwd "$PWD"   # protect from stale/archive
python3 $CUR unpin <name>  --cwd "$PWD"
python3 $CUR promote <name> --cwd "$PWD"  # pending -> active (discoverable)
python3 $CUR promote --all  --cwd "$PWD"
python3 $CUR restore <name> --cwd "$PWD"  # archived -> active
python3 $CUR list-archived  --cwd "$PWD"
python3 $CUR prune --days 90 --cwd "$PWD" # bulk-archive idle skills
python3 $CUR pause --cwd "$PWD"           # stop auto runs (persists)
python3 $CUR resume --cwd "$PWD"
```

Each run writes a report to `.claude/skills/.learned/reports/<ts>/` (`run.json` + `REPORT.md`) and a snapshot to `.claude/skills/.learned/.backups/<ts>/` (last `backup_keep` kept).

## Review pending patterns

```bash
ls .claude/skills/.learned/_pending/
# Promote one (moves it to the discoverable .claude/skills/<name>/ and registers it)
python3 /home/binhna/git/agent-skills/skills/continuous-learning/curate.py promote <name> --cwd "$PWD"
```

## Logs

Each run writes `/tmp/continuous-learning-<session_id>.log`. If no skills appear after a long session, check that log.

## Dry run (manual)

```bash
/home/binhna/git/agent-skills/skills/continuous-learning/extract_patterns.py \
  --transcript ~/.claude/projects/<hash>/<session-id>.jsonl \
  --cwd "$PWD" \
  --session-id manual-test \
  --config /home/binhna/git/agent-skills/skills/continuous-learning/config.json
```

## Limitations

- Stop hook fires at session end only, no mid-session observation (future idea: `PostToolUse` hook + background agent)
- Usage telemetry is inferred from the transcript, not a real "skill loaded" signal, so it can under- or over-count; idle thresholds are deliberately generous to compensate
- Consolidation is conservative and LLM-driven, so it is opt-in and double-checked by the pre-run backup
- Running `claude -p` inside the hook adds 10-60s of background work per session end
