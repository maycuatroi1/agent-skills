---
name: update-evo-agents
description: Bring evo-agents up to date on this machine and in a harness's CI, namely the CLI and worker daemon, the evo-hub and evo-kg plugins and their evo-ak, the skills, and the evo-ak pins in CI. Use for "update evo-agents", "upgrade evo-ak", "nâng evo-agents", "cập nhật evo-agents", "nâng pin CI evo-ak", "update CLI, skill, plugin", "cập nhật máy", "sync skills", "update local" (this machine only), or a SessionStart line starting "evo-agents update:".
version: 0.3.1
---

# Update evo-agents

evo-agents (PyPI `evo-ak`, command `evo-agents`) reaches a machine and a harness in five places, and each
one moves on its own. Team machines follow main: a workflow of evo-agents moves the git tag `nightly` every
night to the newest commit of main whose `ci` push run passed, and the CLI and the daemon run that commit.
CI pins follow PyPI releases.

| Component | Follows | Where it lives | How it is updated |
|---|---|---|---|
| CLI | tag `nightly` | `uv tool` (or pip) | reinstall from `git+https://github.com/maycuatroi1/evo-agents@nightly` with the same extras |
| Plugins `evo-hub`, `evo-kg` | main | Claude Code, marketplace `evo-agents` | `claude plugin marketplace update`, then `claude plugin update` |
| Plugin runtime | the plugin's pin | uv's cache, `evo-ak==X` in the plugin's `hooks/hooks.json` and `.mcp.json` | `uvx --from evo-ak==X evo-agents --version`: the hooks run `uvx --offline`, so an X not cached makes them silent no-ops |
| Worker daemon | the CLI | LaunchAgent or systemd user unit | `evo-agents worker service install` again, only while it holds no run |
| Skills | the hub | `~/.claude/skills` and the other runtimes, `.claude/skills` of each harness | `evo-agents hub skills sync`, never `--adopt` unasked |
| CI pin | PyPI release | `.github/workflows/*` of a harness, `evo-ak==X` | a branch and a pull request, never a push to the default branch |
| Hub server | | ghcr image on the hub's host | reported (`/v1/health`), never updated: a deploy, done by whoever runs the hub |

The pin is deliberate: a schema change in evo-agents must reach a harness through a reviewed bump, so this
skill opens the pull request and stops there.

## 1. Check

```bash
python3 <this skill's directory>/scripts/check.py --json
```

Run it from inside the harness, or pass `--harness <dir>`, once per harness when there are several
(`--harness A --harness B`). Add `--all-harnesses` when the user asks for every harness on the machine.
For this machine alone ("cập nhật máy", "update local", "CLI, skill, plugin"), run `check.py --json --local`:
no harness is read and no CI pin is touched. The report lists `behind`; when it is empty, say everything
is up to date (the CLI at `nightly.commit`, the CI pins at `latest["evo-ak"]`, the hub's version and the
skills left unmanaged) and stop. When `latest.error` is set and no cache exists, the release
could not be looked up: say so and stop. When `nightly.commit` is null, the tag is missing or could not be
looked up (`nightly.error`): the CLI and the daemon are not compared, so say so and go on with the rest. A
CLI whose `cli.source` is `local` (an editable or local install) is left alone.

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
components: <all; local (this machine only, no CI pin); or a subset of cli, plugins, plugin-runtime, worker, skills, ci-pin>
check: <the JSON from step 1>
```

When the user asked, run it in the foreground. When the SessionStart notice triggered this skill, run it
with `run_in_background: true`, tell the user in one line that the update is running, and go on with
their task.

## 3. Relay the report

The subagent returns a table of component, before, after, action and evidence, then what needs the user.
Relay it as is, plus:

- a plugin was updated: open sessions pick up its hooks, its MCP servers and skills come with the next session;
- skills left unmanaged: name them; `evo-agents hub skills sync --adopt` replaces them after a backup, on the user's word;
- the hub is older than the release, or newer than the CLI: say so; the hub is deployed by whoever runs it;
- the daemon was left alone because it holds runs: name them and give the command for later;
- a pull request was opened: give its link; merging it is the user's call.

## Automatic check at session start

`check.py --notice` prints one line when something is behind and nothing otherwise. It caches the
release and nightly lookups for 12 hours, never fails the session (exit 0 on any error), and stays
silent inside an evo-agents worker run (`EVO_RUN_ID`) and when `EVO_AGENTS_UPDATE_NOTICE=0`. Wire it
into `~/.claude/settings.json` once per machine:

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
- No hub deploy, `hub migrate` or `hub skills publish`, and no `hub skills sync --adopt` unasked.
