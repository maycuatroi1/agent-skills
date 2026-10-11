# Proposals

A proposal is one change, argued from evidence, that the person accepts, rejects or defers. `curator.py propose`
checks it and files it in the state directory; `decide` records the answer; `outcomes` measures it later.

## Format

Markdown with a front matter of `key: value` lines and `- item` lists:

```markdown
---
title: Move the plan history out of AGENTS.md
lens: context
kind: context
target: AGENTS.md
evidence:
  - code:AGENTS.md:3
  - inventory:files.2.smells
  - figure:context.loaded
metric: file_chars:AGENTS.md
---

## Problem

AGENTS.md is loaded into every session (about 780 tokens). Lines 3 to 23 narrate which plans finished and when,
with dates; none of it is a rule or a pointer.

## Change

Replace the paragraph with two lines that point at `plans/` and `reports/`. Keep the rules section as it is.

## Effect and cost of waiting

About 600 fewer tokens at the start of every session and every subagent. Nothing breaks if it waits.

## Undo

Revert the commit.
```

Required: `title`, `lens`, `kind`, `target`, `evidence` (at least one reference). Optional: `metric`. The script
adds `id`, `state`, `created`, and `baseline` when there is a metric.

**Lenses:** `context`, `cli`, `skills`, `tool_errors`, `environment`, `corrections`, `harness`, `cost`.

**Kinds:** `context` (always-loaded text or its organization), `cli` (a command or script), `skill`, `rule` (a line
in an instruction file), `memory`, `hook`, `permission`, `harness` (init, test or boot scripts, structure), `docs`.

**Target:** the file the change edits (relative to the root, or `~/...` outside it), or the command it adds.

## Evidence references

| Reference | Points at |
|---|---|
| `claude:<session>:<line>`, `codex:<session>:<line>` | a line of a transcript from the last collect; a unique prefix of the session id is enough; subagents are `<session>/<agent>` |
| `code:<path>:<line>` | a line of a file, relative to the root or absolute |
| `figure:<key>.<key>` | a value in figures.json, list items by index (`figure:commands.0`) |
| `inventory:<key>.<key>` | a value in context.json (`inventory:skills.unused`) |

## Metrics

| Metric | Value |
|---|---|
| `startup_tokens[:runtime:kind]` | median startup tokens, default `claude:interactive` |
| `peak_tokens[:runtime:kind]` | median peak tokens |
| `compactions[:runtime:kind]` | share of sessions that compacted |
| `tool_rate:<tool>`, `program_rate:<program>` | failed calls over calls |
| `cause:<cause>` | failures of that cause per 100 sessions |
| `command:<text>` | share of sessions running a repeated command whose normalized form contains the text |
| `file_chars:<path suffix>` | characters of an always-loaded instruction file |
| `listing_chars` | characters of the skill listing |
| `skill:<name>` | sessions that used the skill |
| `corrections` | correction-pattern turns over prompts |
| `big_outputs` | big outputs per 100 calls |
| `rereads` | within-session re-reads per session |

Rates are per session or per call, so windows of different length compare. A metric measures the review window; let
a change be in use for a few days before reading its outcome.

## Lifecycle

`open` -> `accepted` -> `applied` (with `--commit`), or `rejected`, or `deferred`; `reverted` when an applied change
was undone. Every step is a line in `ledger.jsonl` in the state directory. A proposal with the same kind and target
as one that is open, accepted or deferred is refused, and so is one like a proposal rejected in the last 30 days,
unless `--force` is given with stronger evidence.
