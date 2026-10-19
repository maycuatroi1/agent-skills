---
name: update-evo-agents
description: Bring evo-agents up to date on this machine (CLI, worker daemon, evo-hub and evo-kg plugins and their evo-ak, skills) and report which harnesses lock their CI to a release. Use for "update evo-agents", "upgrade evo-ak", "nâng evo-agents", "cập nhật evo-agents", "pin CI evo-ak", "update CLI, skill, plugin", "cập nhật máy", "sync skills", "update local" (this machine only), or a SessionStart line starting "evo-agents update:".
version: 0.4.0
---

# Update evo-agents

evo-agents (PyPI `evo-ak`, command `evo-agents`) reaches a machine and a harness in several places, and each
one moves on its own. Team machines and harness CI follow main: a workflow of evo-agents moves the git tag
`nightly` every night to the newest commit of main whose `ci` push run passed, and the CLI, the daemon and a
harness's `harness validate` run that commit.

| Component | Follows | Where it lives | How it is updated |
|---|---|---|---|
| CLI | tag `nightly`, unless this machine's worker is locked | `uv tool` (or pip) | reinstall from `git+https://github.com/maycuatroi1/evo-agents@nightly` with the same extras |
| Plugins `evo-hub`, `evo-kg` | main | Claude Code, marketplace `evo-agents` | `claude plugin marketplace update`, then `claude plugin update` |
| Plugin runtime | the plugin's pin | uv's cache, `evo-ak==X` in the plugin's `hooks/hooks.json` and `.mcp.json` | `uvx --from evo-ak==X evo-agents --version`: the hooks run `uvx --offline`, so an X not cached makes them silent no-ops |
| Worker daemon | tag `nightly`, unless locked | LaunchAgent or systemd user unit | itself, once idle (`worker.self_update`); a daemon that cannot: `evo-agents worker service install` again, only while it holds no run |
| Skills | the hub | `~/.claude/skills` and the other runtimes, `.claude/skills` of each harness | `evo-agents hub skills sync`, never `--adopt` unasked |
| Harness CI | tag `nightly`, unless locked | `.github/workflows/*` of a harness: `evo-ak @ git+https://github.com/maycuatroi1/evo-agents@nightly`, or a lock `evo-ak==X` | never from here: nightly is current, and a lock is reported as "locked at X" |
| Hub server | | ghcr image on the hub's host | reported (`/v1/health`), never updated: a deploy, done by whoever runs the hub |

Two locks keep a version where it is, and this skill moves neither:

- **A harness's lock.** A harness whose CI installs `evo-ak==X` instead of the nightly line has locked itself
  at X. The report says "locked at X" and counts it as nothing behind; moving it, to another X or back to
  nightly, is an edit of that workflow by whoever owns the harness. No branch, no pull request from here.
- **A worker's lock.** The owner of a worker locks its version with the Lock version switch on the worker's
  page of the hub (`version_locked` in `GET /v1/workers/{id}`). Its daemon then stays on the evo-agents it runs,
  and so does the CLI of this machine, which is the same `uv tool` install: `cli.held` names the lock, and the
  CLI is reinstalled only when the user says to do it anyway.

A daemon that updates itself to nightly (`worker.self_updating`: it reports `self_update` with state
`current`, `waiting` or `updating`, and the hub says its worker is not locked) is never restarted from here. It reinstalls nightly when it and every
daemon of its install are idle, and restarts on an install a person changed once it holds no run.

## 1. Check

```bash
python3 <this skill's directory>/scripts/check.py --json
```

Run it from inside the harness, or pass `--harness <dir>`, once per harness when there are several
(`--harness A --harness B`). Add `--all-harnesses` when the user asks for every harness on the machine.
For this machine alone ("cập nhật máy", "update local", "CLI, skill, plugin"), run `check.py --json --local`:
no harness is read. The report lists `behind`; when it is empty, say everything is up to date (the CLI at
`nightly.commit`, the hub's version, the skills left unmanaged, the daemon's `worker.self_update` and the
harnesses locked at a release) and stop. When `latest.error` is set and no cache exists, the release could
not be looked up: the plugins and the hub are not compared, so say so and go on. When `nightly.commit` is
null, the tag is missing or could not be looked up (`nightly.error`): the CLI and the daemon are not
compared, so say so and go on with the rest. A CLI whose `cli.source` is `local` (an editable or local
install) is left alone.

Fields the report adds for the locks and the daemon:

- `cli.held`: why the CLI is not reinstalled although `cli.action` is set, namely this machine's worker is
  locked on the hub, or its daemon is installing nightly right now.
- `worker.version_locked` (`null` when a hub before schema 0048 says nothing) and `worker.lock_source`
  (`hub`, or `config.json` when the hub could not be read and the daemon's last copy is used).
- `worker.self_update`: `state`, `reason`, `nightly_commit`, `checked_at`, `since`, `error` and `error_at`
  as the daemon last reported them; `worker.self_updating` is true when the daemon keeps itself at nightly.
- `harnesses[].installs` (each line installing evo-ak, `kind` `nightly`, `git` at another ref, or
  `locked`), `harnesses[].nightly` and `harnesses[].locked_at`.

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
harnesses: <harness directories whose CI to report; default the one around the current directory>
components: <all; local (this machine only, no harness); or a subset of cli, plugins, plugin-runtime, worker, skills, ci>
override_lock: <yes only when the user said to reinstall the CLI although this machine's worker is locked; else no>
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
- the daemon updates itself: give its `self_update` state and reason, and its error when there is one; a
  state `waiting` for 12 hours or more, or an error, is worth the user's look (the worker's page shows it too);
- the CLI was held by the worker's lock: say so, and that the user may ask for it anyway, or unlock the worker
  on its page;
- harnesses locked at a release: name each with its X and the latest release; moving one is an edit of its
  workflow, by the harness's owner.

## Automatic check at session start

`check.py --notice` prints one line when something is behind and nothing otherwise. It caches the
release and nightly lookups for 12 hours, takes the worker's lock from the daemon's `config.json` (the lock
the hub sent last) rather than asking the hub, reads no harness, never fails the session (exit 0 on any
error), and stays silent inside an evo-agents worker run (`EVO_RUN_ID`) and when
`EVO_AGENTS_UPDATE_NOTICE=0`. Wire it into `~/.claude/settings.json` once per machine:

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

- No branch, commit or pull request in a harness: its CI follows nightly, or its lock stays as its owner set it.
- No CLI reinstall while this machine's worker is locked on the hub, unless the user says so; no change of the
  lock itself, which is the owner's switch on the hub.
- No daemon restart while it holds a run: stopping waits 60 seconds and then kills, and a plan run can
  wait a day for its owner. No restart of a daemon that updates itself or is locked.
- No hub deploy, `hub migrate` or `hub skills publish`, and no `hub skills sync --adopt` unasked.
