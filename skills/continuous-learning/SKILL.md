---
name: continuous-learning
description: Auto-extract reusable patterns from Claude Code sessions and save them as learned skills into the current project's .claude/skills/learned/ directory. Use when setting up the Stop hook, reviewing/curating learned skills, tuning extraction thresholds, or explaining how session-end learning works.
allowed-tools: Bash, Read, Edit, Write
---

# Continuous Learning

Runs at session end (via Stop hook). Analyzes the transcript with `claude -p`, extracts reusable patterns, and writes them as Agent Skills into the **current project's** `.claude/skills/learned/` — not `~/.claude/` — so the knowledge syncs across devices via the project's git repo.

## Why project-local learned skills

- User syncs per-project `.claude/` folders across devices through GitHub
- Patterns learned while working on project X are most relevant to project X
- No global namespace pollution

## Files in this skill

| File | Purpose |
|------|---------|
| `evaluate-session.sh` | Stop hook entry point (reads stdin JSON, backgrounds the extractor) |
| `extract_patterns.py` | Loads transcript, calls `claude -p` to extract patterns, writes skill files |
| `config.json` | Tunable: min session length, extraction threshold, auto-approve, pattern types |

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
   - Skips if `{cwd}/.claude/skills/learned/.processed/<session_id>` already exists
   - Builds compact session summary, calls `claude -p` with extraction prompt
   - Writes each pattern to `{cwd}/.claude/skills/learned/<name>/SKILL.md`
   - When `auto_approve=false`, writes to `.../_pending/` for manual review

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
  ]
}
```

| Field | Effect |
|------|--------|
| `min_session_length` | Sessions shorter than this are skipped |
| `extraction_threshold` | `low` = keep many, `medium` = selective, `high` = only high-value |
| `auto_approve` | `true` writes to `learned/`, `false` writes to `learned/_pending/` |
| `claude_model` | Model used by `claude -p` for analysis (default Haiku for speed/cost) |
| `patterns_to_detect` | Categories to extract |
| `ignore_patterns` | Noise categories to ignore |

## Review pending patterns

```bash
ls .claude/skills/learned/_pending/
# Promote one
mv .claude/skills/learned/_pending/<name> .claude/skills/learned/
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

## Limitations (v1)

- Stop hook fires at session end only — no mid-session observation (v2 idea: `PostToolUse` hook + background agent)
- No confidence weighting, no instinct clustering (v2 idea: Homunculus-style atomic instincts with decay)
- Running `claude -p` inside the hook adds 10–60s of background work per session end
