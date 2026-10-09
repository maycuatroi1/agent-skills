---
name: update-evo-agents
description: This skill should be used when the user asks to "update evo-agents", "upgrade evo-ak", "nâng evo-agents", "cập nhật evo-agents", "cập nhật harness agent", "auto update evo-agents", "nâng pin CI evo-ak", or when a SessionStart line starts with "evo-agents update:". It checks the evo-agents CLI, the evo-hub and evo-kg Claude Code plugins, the worker daemon and the evo-ak pins in a harness's CI against the latest release, then hands the update to the evo-agents-updater subagent, which upgrades the machine, restarts an idle worker daemon and opens a pull request for each CI pin.
version: 0.1.1
---

# Update evo-agents

One release of evo-agents (PyPI `evo-ak`, command `evo-agents`) reaches a machine and a harness in five
places, and each one moves on its own:

| Component | Where it lives | How it is updated |
|---|---|---|
| CLI | `uv tool` (or pip) | reinstall at the latest version with the same extras |
| Plugins `evo-hub`, `evo-kg` | Claude Code, marketplace `evo-agents` | `claude plugin marketplace update`, then `claude plugin update` |
| Worker daemon | LaunchAgent or systemd user unit | `evo-agents worker service install` again, only while it holds no run |
| CI pin | `.github/workflows/*` of a harness, `evo-ak==X` | a branch and a pull request, never a push to the default branch |
| Hub server | ghcr image on the hub's host | out of scope: a deploy, done by whoever runs the hub |

The pin is deliberate: a schema change in evo-agents must reach a harness through a reviewed bump, so this
skill opens the pull request and stops there.

## 1. Check

```bash
python3 <this skill's directory>/scripts/check.py --json
```

Run it from inside the harness, or pass `--harness <dir>`, once per harness when there are several
(`--harness A --harness B`). Add `--all-harnesses` when the user asks for every harness on the machine.
The report lists `behind`; when it is empty, say everything is on the latest release and stop. When
`latest.error` is set and no cache exists, the release could not be looked up: say so and stop.

## 2. Hand the update to the subagent

The subagent contract lives in `agents/evo-agents-updater.md` next to this file. Spawn with
`subagent_type: "evo-agents-updater"`. When that agent type is missing, link it once:

```bash
mkdir -p ~/.claude/agents && ln -sf <this skill's directory>/agents/evo-agents-updater.md ~/.claude/agents/evo-agents-updater.md
```

Until the runtime has loaded it, spawn a general-purpose subagent whose prompt starts with
`Read <this skill's directory>/agents/evo-agents-updater.md and follow it.`

The prompt carries only:

```
skill_dir: <this skill's directory>
harnesses: <harness directories whose CI pins to bump; default the one around the current directory>
components: <all, or the subset the user asked for, e.g. "ci-pin">
check: <the JSON from step 1>
```

When the user asked, run it in the foreground. When the SessionStart notice triggered this skill, run it
with `run_in_background: true`, tell the user in one line that the update is running, and go on with
their task.

## 3. Relay the report

The subagent returns a table of component, before, after, action and evidence, then what needs the user.
Relay it as is, plus:

- a plugin was updated: Claude Code loads it in the next session;
- the daemon was left alone because it holds runs: name them and give the command for later;
- a pull request was opened: give its link; merging it is the user's call.

## Automatic check at session start

`check.py --notice` prints one line when something is behind and nothing otherwise. It caches the
release lookup for 12 hours, never fails the session (exit 0 on any error), and stays silent inside an
evo-agents worker run (`EVO_RUN_ID`) and when `EVO_AGENTS_UPDATE_NOTICE=0`. Wire it into
`~/.claude/settings.json` once per machine:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "f=\"$HOME/.claude/skills/update-evo-agents/scripts/check.py\"; [ -f \"$f\" ] && python3 \"$f\" --notice || true",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

The line it prints starts with `evo-agents update:`, which is what triggers this skill.

## Boundaries

- No merge, no auto-merge, no push to a default branch, no force push.
- No plan file, no main checkout's working tree: the pin is bumped in a worktree of its own.
- No daemon restart while it holds a run: stopping waits 60 seconds and then kills, and a plan run can
  wait a day for its owner.
- No hub deploy, `hub migrate` or `hub skills publish`.
