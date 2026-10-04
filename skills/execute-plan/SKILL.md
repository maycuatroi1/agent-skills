---
name: execute-plan
description: This skill should be used when the user asks to "execute the plan", "run the plan", "implement plan <slug>", "làm tiếp plan", "thực hiện plan", "chạy plan", "triển khai plan", or names a plan under plans/active and wants it built rather than written. It reads the plan as the only state, computes the ready frontier from depends_on, groups steps into parallel-safe clusters, runs each cluster in subagents so their working context never enters the main session, verifies before claiming anything, writes status back to the plan, and offers to clear context between clusters.
version: 0.3.0
---

# Execute exec-plan

Drive an existing `plans/active/<slug>.yaml` to completion. The plan is the only durable state, so
the main session stays thin: it orchestrates, verifies, and writes state. Subagents do the reading,
editing, and test-running, and their context dies with them.

Do not use this skill to author a plan. That is `create-exec-plan`.

## Why subagents, not one long session

A step like "write the Dokploy client plus its tests" burns tens of thousands of tokens in file
reads, failed edits, and test output. None of that is worth keeping. A subagent absorbs all of it
and returns twenty lines. This is context clearing that needs no hook and no user action, and it is
the single largest token saving available while implementing a plan.

The main session must therefore never read product code, never run the test suite for exploration,
and never open a large file to "check" a subagent. It reads plan state, reads subagent reports, and
runs verify commands.

This workflow is evidence-driven, not ceremony-driven. Do not repeat a command when the same working
tree state already has trustworthy verbatim output from the subagent. Do not run full-repo checks for
targeted steps unless the plan explicitly makes them acceptance criteria or the repository cannot run
the target in isolation.

## 1. Load state cheaply

```
evo harness show <slug>
evo harness step <slug> --no-input     # step board: id, status, blocking, depends_on
```

Use these, not `Read` on the YAML. A mature plan is 25k+ tokens of prose; the board is a few hundred.
Only `Read` a narrow offset when a specific step's `what`/`verify`/`note` text is needed, and read
just that step.

If the slug is ambiguous or missing, `evo harness plans` lists every plan with progress.

Check `harness.yaml` once for a `hub:` key with a `project`. When it has one, this is a hub harness:
the plan lives on the evo-agents hub, and every file under `plans/` is a read-only copy the hub wrote.
Nobody edits that YAML, the main session included; section 5 says how writes go instead. The evo-hub
plugin refreshes the copies at session start. Without the plugin, or when another machine may have
written since, run `evo-agents hub plan export .` from the harness root before computing the frontier.
A harness without the key keeps its plans as plain files in git, and everything below works on them
directly.

## 2. Compute the ready frontier

A step is ready when its `status` is `pending` and every id in its `depends_on` is `done`.

Two hard gates before anything runs:

- A `blocking: true` step that is not `done` stops every step ordered after it. Never route around it.
- A step whose `what` is a checkpoint (verification, baseline comparison) is a barrier by intent even
  when `depends_on` would allow overtaking it.

If the frontier is empty but pending steps remain, report exactly which unmet dependency is holding
the plan and stop. Do not invent work.

## 3. Group the frontier into clusters

A cluster is a set of steps that can run at the same time without corrupting each other. Assume
serial until a rule below proves parallel is safe.

Parallel is safe when:

- The steps are in different repos. Different working trees, no shared index.
- The steps only create new files under disjoint paths, and no subagent commits.

Parallel is NOT safe when:

- Two steps touch the same file. The second edit silently loses the first.
- Two steps in the same repo both need to commit. One working tree has one index; concurrent
  `git add`/`git commit` produce commits containing each other's work. If a plan says "one commit per
  step" (common when working directly on a shared branch), that alone forces serial commits.
- A step's `verify` runs a build or typecheck over the whole repo. It will see another step's
  half-written file and fail for the wrong reason.

When steps must share a repo but are genuinely independent, either run them serially, or give each
subagent `isolation: "worktree"` and merge afterwards. Worktrees cost setup time and a merge, so
only reach for them when the parallel win is real.

State the chosen grouping to the user in one line per cluster before running anything, including why
anything was forced serial.

### Prepare GitNexus without dirtying the worktree

Before delegating edits, check `gitnexus status`. If the index is stale and the repository requires a
fresh index, use pure index mode:

```
gitnexus analyze --index-only --name <repo>-<plan-slug>
```

Use a unique alias for temporary worktrees and pass the worktree path to later `--repo` arguments when
aliases are ambiguous. Never run bare `gitnexus analyze` in an implementation worktree: it injects or
updates `AGENTS.md`, `CLAUDE.md`, and GitNexus skill files, creating unrelated diffs. Run impact before
editing as required by the repository, but run `detect_changes` only once after the intended files are
staged and immediately before commit.

## 4. The subagent contract

Spawn one subagent per step, or per short linear chain of steps that share a file. Give each one:

- The step's `id`, `what`, `verify`, and `note`, quoted verbatim from the plan.
- The repo path and the branch it must stay on.
- The relevant `references:` entries so it does not rediscover them.
- The explicit prohibitions below.

A subagent MUST NOT:

- Edit `plans/active/*.yaml`, or write plan state any other way. Concurrent read-modify-write on one
  YAML file loses updates, and a subagent cannot see whether its verify will survive review. State is
  written once, by the main session, in section 5.
- Commit, unless the cluster is serial and the plan assigns commits to that step. Say which applies.
- Mark its own work done in any form, including in prose.
- Touch files outside its step's scope.

The subagent must inspect its own diff once before returning. Do not spawn a separate review agent by
default. Add an independent review only when per-symbol impact is HIGH or CRITICAL, the step changes an
authorization/secret/destructive-mutation boundary, or the user explicitly requests review.

A subagent MUST return, and nothing more:

```
step: <id>
files: <paths changed or created>
verify_command: <the exact command run>
verify_result: pass | fail
verify_output: <last 15 lines, verbatim, never paraphrased>
notes: <anything the plan got wrong, max 3 lines>
```

Verbatim output matters. A subagent reporting "tests pass" without the run is the failure mode this
whole workflow exists to prevent, and it is the same failure that makes plan state lie.

### Normalize misleading targeted test commands

Before running a verify command such as `npm test -- tests/foo.test.ts`, inspect the package's `test`
script once. If that script already hardcodes a broad glob such as `tests/*.test.ts`, the appended path
does not filter the suite. Replace only that invocation with the repository's underlying runner and the
requested target, for example:

```
node --test --import tsx tests/foo.test.ts
```

Record both the plan command and the effective command in `verify_command`. Do not guess a replacement
for an unfamiliar runner. If equivalence is unclear, run the plan command as written once. Full-suite
test, lint, typecheck, and build belong at an explicit checkpoint or final verification step, not after
every targeted implementation step.

## 5. Write state back, from the main session only

For each returned step, in plan order:

1. Validate that the report contains the exact command, a pass result, and verbatim output for the
   current working tree state. Do not re-run it when no files changed after the subagent's run.
2. Re-run only missing or failed checks, external/manual acceptance the subagent could not perform,
   checks invalidated by later edits, and final checkpoint commands. Never re-run merely to duplicate
   evidence.
3. If verification fails, leave the step `pending` and record what happened. Do not mark `in_progress` as a
   consolation.
4. If it passes, stage only intended files, inspect staged status/diff once, run required secret scan
   and `gitnexus detect-changes --scope staged` once, then commit when the plan assigns commits.
5. After the commit, record the step with evidence that cites the commit hash and the verify result,
   worded like the steps already closed in the same plan:

```
evo harness step <slug> <step-id> done --evidence "<repo>@<sha>: <verify result>"
```

That sets `status`, `done_at` and `evidence` in one write. Where the write lands depends on the harness:

- **Hub harness.** `evo harness step` sends the change with `evo-agents hub plan patch`, retries when
  someone else wrote the plan in between, then runs `evo-agents hub plan export` to rewrite the copy.
  Never edit the YAML, not even to add evidence: a hand edit breaks the copy's digest, and both
  `evo-agents harness validate` and `evo harness check` report it. If the write fails (not signed in,
  no grant, hub down), report the error and leave the step as it is. Do not fall back to editing the
  file.
- **File harness.** `evo harness step` edits the text in place and refuses to save if the reparse does
  not match the expected result, so comments and block scalars survive.

The command above needs evo-cli 0.29.0 or later. Check with `evo --version`, or look for `--evidence` in
`evo harness step --help`. Releases before 0.29.0 know nothing of the hub, have no `--evidence`, and
their `--note` overwrites the step's existing `note:` field, which carries the traps the plan author
found. With an older evo-cli:

- in a hub harness, stop and upgrade (`pip install -U evo-cli`) before writing any state, because the
  old release edits the copy in place;
- in a file harness, run `evo harness step <slug> <step-id> done` without `--note`, then add
  `evidence:` with `Edit`.

From 0.29.0 on, `--note` appends on a line of its own and keeps the existing note, so it is safe for
something the next session must know that is not evidence.

When every step of a repo has landed, move the repo entry with `evo harness repo <slug> <index> <status>`.

Close the loop before moving on:

```
evo harness check <slug>
```

It compares what the plan claims against real git. Report any mismatch immediately rather than
starting the next cluster on top of it.

## 6. Offer to clear between clusters

Nothing in Claude Code lets an agent clear its own context. `/clear` is a built-in command; hooks
cannot trigger it and the model cannot invoke it. So the skill asks, and the user presses the key.

After a substantial cluster, with state written and `check` clean, use `AskUserQuestion`:

- Continue to the next cluster in this session.
- `/clear`, then re-invoke this skill with the same slug.
- Stop here.

Do not interrupt the user after every small serial step. Recommend the clear when the cluster produced
several subagent reports or when their verify output was long. Say plainly what re-entry costs: one
`evo harness show` plus one step board, a few hundred tokens against a session that may be carrying a
hundred thousand.

Tell the user the exact re-entry line, for example `/execute-plan deployments-control-plane`.

## 7. Resuming is the normal case

This skill is idempotent by construction. On entry it derives everything from plan state, so a
cleared session is indistinguishable from a fresh one. Steps already `done` are skipped, the frontier
is recomputed, work continues.

That property only holds if section 5 was honoured. A step finished but left `pending` makes the next
session redo it; a step marked `done` without a passing verify makes the next session build on sand.
Both are worse than a slow session.

## 8. When a step fails

Do not retry the same subagent prompt verbatim, and do not silently narrow the step.

- Verify failed for an environmental reason (missing credential, service down): leave `pending`,
  report the blocker, ask the user.
- The step's premise is wrong (the file it names does not exist, the API shape differs): leave
  `pending`, report the discrepancy against the plan's `references:`, and ask whether to amend the
  plan. Amending a plan mid-execution is the user's call.
- The step is genuinely bigger than written: finish what is actually verifiable, leave the step `pending`
  with `evidence:` saying exactly which part landed, per the harness rule that partial work is never
  `done`. Write it with `evo harness step <slug> <step-id> pending --evidence "..."`, never by hand in a
  hub harness.

## 9. Checklist

- [ ] Plan state loaded via `evo harness show` / `step --no-input`, not a full file read.
- [ ] Frontier computed from `depends_on`, blocking steps and checkpoints respected.
- [ ] Clustering decided and stated, with any forced-serial reason given.
- [ ] A stale GitNexus index was refreshed with `--index-only`, never a bare analyze in the worktree.
- [ ] Every subagent told: no plan edits, no self-marking, verbatim verify output.
- [ ] Targeted test commands were checked for hardcoded broad globs and normalized when equivalent.
- [ ] Main session accepted current verbatim evidence instead of duplicating successful checks.
- [ ] Staged diff, secret scan, and `detect_changes` each ran once immediately before commit.
- [ ] `evo harness step ... done --evidence` cited the commit hash, with evo-cli 0.29.0 or later. In a
      hub harness no YAML was edited by hand; with an older evo-cli in a file harness, no `--note`
      and `evidence:` added with `Edit`.
- [ ] `evo harness check <slug>` clean before the next cluster.
- [ ] User offered the clear after a substantial cluster, with the re-entry command spelled out.
