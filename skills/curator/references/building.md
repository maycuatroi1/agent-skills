# Building what a proposal calls for

Pick the lightest artifact that makes the problem stop: a line in the map before a script, a script before a
skill, a hook only when a written rule keeps being broken.

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

**When:** a correction repeats, or the agent needed a fact it could not derive.

**Where:** the narrowest always-loaded file that covers every place the rule applies; check it is not already
written elsewhere. One line, imperative, with the reason when the reason is not obvious.

When the rule already exists and the sessions still break it, a louder rule will not help: propose a hook or a
check.

## A hook

**When:** something must always happen (format after an edit) or must never happen (a command that broke things),
and a written rule did not hold.

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
