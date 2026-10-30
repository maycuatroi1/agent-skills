# Building what a proposal calls for

For work the sessions repeat, pick the lightest artifact that does the job: a line in the map before a script, a
script before a skill. For a failure that must stop, climb the guard ladder instead.

## The guard ladder

A guard that a machine enforces holds on the first session; a written rule holds only when it is read and obeyed.
Take the highest rung that can work, strongest first:

1. `remove`: take the wrong path away. Delete the flag, the command or the code path that let it happen; make the
   wrong call impossible (a wrapper that only offers the right one, a default that is right).
2. `type`: a type, a schema or a parser that rejects the wrong shape before anything runs.
3. `lint`: a lint rule, a pre-commit check, or a guard at run time (a PreToolUse hook, a check in the CLI) that
   refuses the wrong action with a message naming the right one.
4. `test`: a behaviour test that fails on the wrong behaviour, run where the change lands.
5. `prose`: a rule, a line of context, a document. Last, for what no machine can check (a judgment, a fact the
   agent needs).

The proposal names its rung in `guard`. Below `remove`, its `## Why not higher` section says, rung by rung, why the
higher ones cannot work here ("the wrong command is how other repos call it, so it cannot be removed; nothing
types a shell line; a hook can match it"). "A rule is cheaper" is not a reason.

A proposal for a correction carries the failure it guards against as it happened: `failing_ref`, the transcript
line or hub run event where it went wrong; `failing_input`, the concrete input of that time, quoted from there;
`failing_probe`, the command or probe that shows it still goes wrong on the harness today. Run the probe before
proposing; when it no longer fails, the harness already changed and there is nothing to guard. Never write an
example of your own: `curator.py propose` refuses an input the cited line does not contain. The probe is also how
the guard is verified once applied: it must now be refused or pass.

Real examples:

- Sessions ran `pip install foo` in a uv project and the person said "không, dùng uv thay vì pip" twice. Prose would
  be a line "use uv, not pip" in AGENTS.md. Higher: `lint`, a PreToolUse hook on Bash that refuses `pip install`
  with "use `uv add`" (`remove` is out: pip is on the image for other tools). Failing example: `failing_input: pip
  install foo`, `failing_probe: echo '{"tool_input":{"command":"pip install foo"}}' | .claude/hooks/no-pip.sh`,
  which exits 0 today.
- An agent of a worker run wrote outside its run directory with Edit, and only Bash was checked. A rule "edit only
  inside the run" was already in the prompt and broken. Higher: `lint`, the PreToolUse guard checks Edit and Write
  too; with a behaviour `test` that feeds it a path outside the directory.
- A plan step kept an invalid `status: complete` the hub refused at import. Higher than a note in the skill:
  `type`, the plan schema lists the statuses and the writer validates before saving.

## A CLI command

**When:** the same command line, inline script or short sequence runs in three or more sessions; a command keeps
failing on how it is called; `--help` of the same tool is read in many sessions.

**Where:** first the entry point the project already has: `package.json` scripts, a `Makefile` or `justfile`
target, `[project.scripts]` in `pyproject.toml`, a `./<name>` dispatcher, `scripts/` or `bin/`. Read how its
existing commands are written and follow that. Only without one, a file in `scripts/` named for the job
(`scripts/test-hub.sh`). A tool shared by several harnesses belongs in the team's shared CLI; propose it there
rather than copying a script into each repo.

**Design for an agent caller:**

- One job per command, named by a verb and a noun.
- No prompts. A destructive action needs `--yes`; without it, say what would happen and exit non-zero.
- Quiet by default: print what the next step needs, with counts instead of lists past a limit
  (`12 more, --all to show`). `--json` with stable keys for anything a script will read.
- Idempotent: running it twice is safe and says it had nothing to do.
- On failure, exit non-zero with a message that names the fix ("no venv at .venv: run `uv sync`").
- Configuration from the repo, secrets from the environment or the credential store, never from arguments.
- `--help` with one real example.

**Register it:** one line in the map, in the place agents look for commands, and replace the old incantation
wherever a doc or skill spells it out. A command nobody is told about is not used.

**Verify:** run it on the case that produced the evidence; compare its output size with what the sessions printed.

## A skill

**When:** the same multi-step workflow appears in three or more sessions, and the agent re-derives the steps or
makes the same mistakes each time. A single command is a CLI; a single rule is a line in the map.

**Where:** where the harness keeps its own skills when only it needs the skill; the team's skills repo, through its
normal publishing, when several harnesses do. Check that no installed skill already covers it; extending one is
better than a near-duplicate with overlapping triggers.

**Shape:**

```markdown
---
name: kebab-case-name
description: What it does and when to use it, with the phrases people typed in the sessions. A few hundred characters.
---

# Title

What it is for, in two or three sentences.

## When to use / when to skip
## Steps            (commands that run as written, each with what to check)
## Gotchas          (the failures from the evidence, each with its fix)
## Files            (scripts/ and references/ and what each holds)
```

Keep the body short enough to read in one go (a few hundred lines at most); move detail into `references/` and
deterministic work into `scripts/`, so the agent runs a script instead of re-deriving logic. Take trigger phrases
and gotchas from the evidence: what people asked for and what went wrong.

**Verify:** start a fresh session with a request the sessions contained and check the skill is picked and its
steps work.

**Retiring a skill:** never delete. Scope it down to the harness that uses it, or disable it, after checking a
window long enough to catch occasional use. Say where it went.

## A rule

**When:** the agent needed a fact it could not derive, or a correction repeats and no rung above `prose` can guard
it (the proposal says why in `## Why not higher`).

**Where:** the narrowest always-loaded file that covers every place the rule applies; check it is not already
written elsewhere. One line, imperative, with the reason when the reason is not obvious.

A rule that exists and is still broken shows a guard was due from the start; a louder rule will not help.

## A hook

**When:** something must always happen (format after an edit) or must never happen (a command that broke things),
and no higher rung (removing the path, a type or schema) can do it. Do not wait for a written rule to fail first.

Keep hooks fast and silent on success. A SessionStart hook's output is loaded into every session; measure it
(`hook_context` in the loaded components) and keep it to a line or two. Settings files outside the repo change
every session on the machine; propose them as such.

## A permission

**When:** the person approves the same read-only command again and again, or a denial shows up for a command that
is safe.

Add only commands that read or that are confined to the repo, in the project's settings, not the user's. Never
allow a pattern that matches a destructive command.

## A memory

**When:** a fact about the person or the project that cannot be derived from the code or its history, and that
sessions needed.

One fact per memory, with why it matters and how to apply it; one line in the index. Update or remove a memory that
turned out wrong rather than adding a second one.
