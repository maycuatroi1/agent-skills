---
name: execute-plan
description: This skill should be used when the user asks to "execute the plan", "run the plan", "implement plan <slug>", "làm tiếp plan", "thực hiện plan", "chạy plan", "triển khai plan", or names a plan under plans/active and wants it built rather than written. It reads the plan as the only state, computes the ready frontier from depends_on, groups steps into parallel-safe clusters, runs each step in a plan-step subagent that implements, verifies and commits it, writes status back from the main session, and keeps going until the plan is done or needs the user. It also drives the agent of an evo-agents worker plan run (EVO_RUN_KIND=plan), reporting through evo-agents worker instead of evo harness.
version: 0.5.0
---

# Execute exec-plan

Drive an existing `plans/active/<slug>.yaml` to completion. The plan is the only durable state, so
the main session stays thin: it orchestrates, checks reports, and writes state. Subagents read, edit,
test and commit, and their context dies with them.

Do not use this skill to author a plan. That is `create-exec-plan`.

## Why subagents, not one long session

A step like "write the Dokploy client plus its tests" burns tens of thousands of tokens in file
reads, failed edits, and test output. None of that is worth keeping. A subagent absorbs all of it
and returns twenty lines. This is context clearing that needs no hook and no user action, and it is
the single largest token saving available while implementing a plan.

Every main-session turn re-reads the whole conversation, so its cost grows with the session. On one
measured run with about 230k tokens of context, closing a single step took 7 main-session turns and
1.6M cache-read tokens, and 3 of those turns were the main session reading product code. Count
main-session turns per step and keep them near two: one spawn, one combined check-and-record call.

The main session therefore never reads product code, never runs tests for exploration, never opens a
file to "check" a subagent, and never stages or commits product changes. When a report raises a
question about the code, the next subagent answers it, or the user does.

This workflow is evidence-driven, not ceremony-driven. Do not repeat a command when the same working
tree state already has trustworthy verbatim output from the subagent. Do not run full-repo checks for
targeted steps unless the plan explicitly makes them acceptance criteria or the repository cannot run
the target in isolation.

## 1. Load state cheaply

First check `echo "${EVO_RUN_KIND:-}"`. `plan` means this session is the agent of an evo-agents worker plan run:
there is no harness checkout and no `evo harness`, and section 9 says what replaces them. `step` means a run of one
step, whose prompt, not this skill, says what to do. Empty means an ordinary session; read on.

```
evo harness show <slug>
evo harness step <slug> --no-input     # step board: id, status, blocking, depends_on
```

Use these, not `Read` on the YAML. A mature plan is 25k+ tokens of prose; the board is a few hundred.
The main session rarely needs a step's full text, since the subagent reads its own step.

If the slug is ambiguous or missing, `evo harness plans` lists every plan with progress.

Check `harness.yaml` once for a `hub:` key with a `project`. When it has one, this is a hub harness:
the plan lives on the evo-agents hub, and every file under `plans/` is a read-only copy the hub wrote.
Nobody edits that YAML, the main session included; section 5 says how writes go instead. The evo-hub
plugin refreshes the copies at session start. Without the plugin, or when another machine may have
written since, run `evo-agents hub plan export .` from the harness root before computing the frontier.
A harness without the key keeps its plans as plain files in git, and everything below works on them
directly.

## 2. Compute the ready frontier

A step is ready when its `status` is `pending` and every id in its `depends_on` is `done`. That is the
whole rule, and it is the rule `ready_steps` in `evo_agents/hub/runs.py` applies to hub runs.

`blocking` does not hold back steps that do not depend on it. Plan templates put `blocking: true` on
nearly every step, and reading it as "nothing ordered after this may start" turned a 22-step plan whose
`depends_on` allowed 14 levels into 22 serial steps. `blocking: true` marks a step the plan cannot
finish without; `blocking: false` marks one whose failure the user may accept. Section 8 uses it.

One barrier remains. A step whose `what` is a checkpoint (full-suite verification, baseline
comparison, release, deploy) starts only after every step ordered before it is `done`, and no step
ordered after it starts until it is `done`, even when `depends_on` would allow it.

If the frontier is empty but pending steps remain, report exactly which unmet dependency is holding
the plan and stop. Do not invent work.

## 3. Group the frontier into clusters

A cluster is the set of ready steps that run at the same time. Each subagent commits, so two of them
never share a working tree.

- A single ready step, or a short linear chain that shares files, runs serially in the repo's main
  checkout on the plan branch.
- Ready steps in different repos run in parallel, each in its repo's checkout on the plan branch.
- Ready steps in the same repo run in parallel, each in its own git worktree on its own branch. Run
  them serially instead when they will certainly conflict on merge: both add a migration or bump a
  schema version, both register in the same router, index or `__init__`, or both edit a file the plan
  names for each.

A step whose `verify` builds or typechecks the whole repo is safe in a worktree, since it sees only its
own tree. Create the worktrees for a cluster in one call from the main session:

```
git -C <repo> worktree add ../<repo>-wt/<slug>-<id> -b <plan-branch>-step-<id> <plan-branch>
```

The Agent tool's `isolation: "worktree"` makes a worktree of the session's own repository. In a harness
session that is the harness, not the code repo, so do not use it for code steps.

State the grouping to the user in one line per cluster, with the reason anything runs serially.

### Prepare GitNexus without dirtying the worktree

Before delegating edits, check `gitnexus status`. If the index is stale and the repository requires a
fresh index, use pure index mode:

```
gitnexus analyze --index-only --name <repo>-<plan-slug>
```

Use a unique alias for temporary worktrees and pass the worktree path to later `--repo` arguments when
aliases are ambiguous. Never run bare `gitnexus analyze` in an implementation worktree: it injects or
updates `AGENTS.md`, `CLAUDE.md`, and GitNexus skill files, creating unrelated diffs.

## 4. Spawn a plan-step subagent

The subagent contract lives in `agents/plan-step.md` next to this file: what the subagent may and must
not do, how it verifies and commits, and the exact report it returns. The main session does not
restate it per step. Spawn with `subagent_type: "plan-step"`. When that agent type is missing, link it
once:

```
mkdir -p ~/.claude/agents && ln -sf <this skill's directory>/agents/plan-step.md ~/.claude/agents/plan-step.md
```

Until the runtime has loaded it, and in runtimes without agent types, spawn a general-purpose subagent
whose prompt starts with `Read <this skill's directory>/agents/plan-step.md and follow it.`

The prompt carries only what the contract and the plan cannot:

```
plan: <slug>
harness: <harness directory>
step: <id>, or a chain such as 7,8
repo: <main checkout or worktree path>
branch: <branch it commits on>
mode: serial | parallel
commit: yes | no
context: <at most 10 lines the plan does not say: decisions taken earlier in this run, the sha a
dependency landed in, a trap an earlier report found>
```

The subagent reads the step's `what`, `verify`, `note` and the plan's `references` itself. Do not paste
them: quoting a step costs the main session output tokens and adds nothing. Set `commit: no` only when
the plan assigns the commit to a later step or checkpoint.

Do not spawn a separate review agent by default. Add an independent review only when per-symbol impact
is HIGH or CRITICAL, the step changes an authorization, secret or destructive-mutation boundary, or the
user asks for review.

## 5. Write state back, from the main session only

Subagents never write plan state. The main session writes it once per step, after reading the report.
For each report, in plan order:

1. Check that it has the exact command, `result: pass`, verbatim output, and a commit sha when
   `commit: yes`. Do not re-run a check the report already shows passing on that commit.
2. Re-run only what is missing or failed, external or manual acceptance the subagent could not do, and
   checks a later merge invalidated.
3. After a parallel same-repo cluster, merge each step branch into the plan branch in step order with
   `git -C <repo> merge --no-ff <plan-branch>-step-<id>`, then run the merged steps' verify commands
   once, together in one call. On a merge conflict, abort the merge, leave that step `pending`, and run
   it again serially on the merged branch. Remove merged worktrees and their branches.
4. Check the commit and record the step in one call:

   ```
   git -C <repo> show --stat --format='%h %s' <sha> && \
   evo harness step <slug> <step-id> done --evidence "<repo>@<sha>: <verify result>"
   ```

   Word the evidence like the steps already closed in the same plan. Compare the `--stat` list with the
   report's `files` and `outside_scope`; a file you did not expect is a reason to question the report,
   not to read the code.
5. When verification fails, leave the step `pending` and record what happened with
   `evo harness step <slug> <step-id> pending --evidence "..."`. Do not mark `in_progress` as a
   consolation.

`evo harness step` sets `status`, `done_at` and `evidence` in one write. Where the write lands depends
on the harness:

- **Hub harness.** `evo harness step` sends the change with `evo-agents hub plan patch`, retries when
  someone else wrote the plan in between, then runs `evo-agents hub plan export` to rewrite the copy.
  Never edit the YAML, not even to add evidence: a hand edit breaks the copy's digest, and both
  `evo-agents harness validate` and `evo harness check` report it. If the write fails (not signed in,
  no grant, hub down), report the error and leave the step as it is. Do not fall back to editing the
  file. When the copies are tracked in git, commit them once per cluster, not once per step:
  `evo-agents hub plan export . --commit`.
- **File harness.** `evo harness step` edits the text in place and refuses to save if the reparse does
  not match the expected result, so comments and block scalars survive.

This needs evo-cli 0.29.0 or later (`evo --version`, or `--evidence` in `evo harness step --help`).
Older releases know nothing of the hub, have no `--evidence`, and their `--note` overwrites the step's
existing `note:`. With an older evo-cli, stop and upgrade (`pip install -U evo-cli`) in a hub harness;
in a file harness, run `evo harness step <slug> <step-id> done` without `--note`, then add `evidence:`
with `Edit`. From 0.29.0 on, `--note` appends on a line of its own, so it is safe for something the next
session must know that is not evidence.

When every step of a repo has landed, move the repo entry with `evo harness repo <slug> <index> <status>`.

Close the loop after each cluster with `evo harness check <slug>`, which compares what the plan claims
against real git. Report a mismatch immediately rather than starting the next cluster on top of it.

## 6. Run to the end

Keep going, cluster after cluster, until the frontier is empty. Do not ask between clusters and do not
offer `/clear` as a question. After each cluster, write one status line: the steps closed with their
shas, and the next cluster.

Stop and ask only when:

- the next step is outward-facing or hard to reverse: a push to a shared branch, a merge to the default
  branch, a release or publish, a deploy, creating or rotating credentials, changing a production
  database, or sending a message on someone's behalf;
- the plan text says the user decides or confirms;
- a step failed or its premise is wrong (section 8) and no other step is ready.

Nothing lets an agent clear its own context. When the session passes about half its window, say so
once in the status line together with the re-entry command, for example
`/execute-plan deployments-control-plane`, and keep going; whether to clear is the user's call.
Re-entry costs one `evo harness show` plus one step board.

## 7. Resuming is the normal case

This skill is idempotent by construction. On entry it derives everything from plan state, so a
cleared session is indistinguishable from a fresh one. Steps already `done` are skipped, the frontier
is recomputed, work continues.

That property only holds if section 5 was honoured. A step finished but left `pending` makes the next
session redo it; a step marked `done` without a passing verify makes the next session build on sand.
Both are worse than a slow session.

## 8. When a step fails

Do not retry the same subagent prompt verbatim, and do not silently narrow the step. Leave the failed
step `pending` with evidence of what happened, keep running ready steps that do not depend on it, and
ask the user once nothing else is ready.

- Verify failed for an environmental reason (missing credential, service down): report the blocker.
- The step's premise is wrong (the file it names does not exist, the API shape differs): report the
  discrepancy against the plan's `references:` and ask whether to amend the plan. Amending a plan
  mid-execution is the user's call.
- The step is genuinely bigger than written: keep what is actually verifiable and record with
  `evo harness step <slug> <step-id> pending --evidence "..."` exactly which part landed, per the
  harness rule that partial work is never `done`.

A subagent whose verify failed in the main checkout stashes its changes and reports the stash, so the
next serial step starts clean. Put the stash name in the step's evidence.

A failed `blocking: true` step means the plan cannot finish without it; say so in the final report. A
failed `blocking: false` step can be left behind if the user accepts it.

## 9. Inside a worker plan run

An evo-agents worker can take a whole plan as one run. Its daemon starts the agent in a run directory that holds a
worktree of each repo of the plan, on the branch the plan names for that repo, and `.evo-run/plan.yaml`, the plan as
the run was claimed. The environment has `EVO_RUN_KIND=plan`, `EVO_RUN_ID` and `EVO_WORKER_HOME`. The owner who
dispatched the run is not watching, and the hub keeps the plan. The agent reaches the hub only through four commands
that use the worker's token and refuse to run outside the run: `evo-agents worker plan`, `evo-agents worker step`,
`evo-agents worker ask` and `evo-agents worker notify`. They come with the evo-agents that runs the worker (0.4.0 or
later). Where this section differs from sections 1 to 8, it wins.

**Read the plan.** Before each cluster, read the plan as the hub holds it now; the owner may have edited it since the
run was claimed. A step board costs a few hundred tokens:

```
evo-agents worker plan --json | python3 -c 'import sys, json; b = json.load(sys.stdin)["body"]; [print(s["id"], s.get("status", "pending"), s.get("repo", "-"), s.get("depends_on", []), s.get("title", "")) for s in b["steps"]]'
```

`.evo-run/plan.yaml` holds each step's full text as claimed. Compute the frontier as section 2 says. Checkpoint steps
stay barriers, and they are the agent's to do.

**Clusters.** Steps in different repos may run in parallel, each in its repo's worktree. Steps in the same repo run
one after another in that worktree: `evo-agents worker step <id> done` commits whatever the worktree holds, so a
second step in flight would land in the first one's commit. Never switch a worktree's branch; the worker refuses to
commit or push from any branch but the run's.

**Subagents.** Spawn plan-step subagents as section 4 says, with `plan_file` in place of `harness`:

```
plan: <plan id>
plan_file: <run directory>/.evo-run/plan.yaml
step: <id>
repo: <that repo's worktree, as the run's prompt lists it>
branch: <the branch that worktree is on>
mode: serial
commit: yes
context: <as in section 4>
```

`mode` is always `serial` here, so a subagent whose verify failed stashes its changes and the next step's `done`
does not commit them.

**Record each step.** Subagents never report to the hub. The main session marks a step when it spawns the subagent
and records it after reading the report:

```
evo-agents worker step <id> in_progress --repo <repo>
evo-agents worker step <id> done --repo <repo> --evidence "<text>" --verify "<command>"
evo-agents worker step <id> pending --repo <repo> --evidence "<what landed, what failed, the stash>"
```

`done` runs each `--verify` command again with `/bin/sh` in the repo's worktree (repeat `--verify` once per command)
and refuses the step when one exits non-zero. Otherwise it commits what is left in the worktree, pushes the run's
branch to the branch the plan names (never forced), and records the commit with the step. Take the commands from the
report's `verify_command`, the effective one when it differs, as they run from the worktree root: a plan `verify` that
starts with `cd ~/github/<repo>` points at a developer's checkout, not at this worktree. The hub writes the run,
`repo@commit` and each verify command's exit code into the evidence itself, so `--evidence` says what was done, plus
the `Decision:` lines below. Never use `evo harness step`, `evo-agents hub plan` or the hub's `plan_step` tool here:
the hub writes the step from the worker's report, as the member who dispatched the run.

**Ask only what the owner must decide.** Use `evo-agents worker ask` only for a decision of one of the categories the
run's prompt lists:

- `deploy`: deploying or releasing anything to any environment, a checkpoint step that deploys included;
- `delete_data`: deleting data that is not the run's own scratch: database rows, files, buckets, other people's
  branches;
- `live_migration`: a migration, backfill or bulk change on real data rather than a test database;
- `external_send`: sending anything to a service outside the machine and the repos' own remotes: mail, chat, issues,
  third-party APIs;
- `spend_money`: anything that costs money beyond the runtime's own usage: paid APIs, cloud resources, purchases;
- `architecture`: an architectural choice the plan leaves open;
- `scope`: a question of scope the plan leaves open: adding, dropping or reshaping a step or what it delivers.

```
evo-agents worker ask --category deploy --question "<one or two sentences>" --context-file <notes.md> --option "go=Deploy now" --option "hold=Wait:Deploy after the owner checks staging" --recommended hold --step <id>
```

It takes 2 to 6 options and prints the decision's id. Go on with the steps that do not depend on the answer; when none
is left, end the turn. The run waits for the owner, the waiting time does not count toward its timeout, and the answer
comes back in this session as a message naming the decision. Read the plan again, then go on; section 7 holds.

Decide everything else yourself, and write each such choice with its reason in the step's evidence, on a line that
starts with `Decision:`. Section 6's stops and section 8's questions to the user become either a decision of a listed
category or a `Decision:` line. A wrong premise, or a step bigger than written, is a `scope` decision; hand the step
back with `pending` and go on with other ready steps meanwhile.

**Checkpoints.** A checkpoint step (full-suite verification, review, release, deploy) is the agent's: do it like any
step. When it includes a deploy or a release, or anything else in the list above, ask first with `--step <id>`, do the
parts that do not depend on the answer, and end the turn.

**Push and merge.** The agent may push, and merge into, the branch the plan names for a repo, even when it is the
repo's default branch. It never pushes or merges into a branch the plan does not name for that repo, never
force-pushes, and never rewrites history it pushed. A step that needs more, such as merging a feature branch the plan
names into `main`, is a `scope` decision. `evo-agents worker step <id> done` sends its own notice for its pushes; after
a push or merge into a default branch the agent makes itself, it runs:

```
evo-agents worker notify --kind merge_default_branch --title "<one line>" --body "<what and why>" --repo <repo> --branch <branch> --commit <sha>
```

with `--kind push_default_branch` for a push, and `--commit` once per commit.

**Stop.** When the frontier is empty and no decision is open, write `.evo-run/result.json` in the run directory, not
in a repo, and end the turn:

```json
{"summary": "Done: 1, 2, 4. Decided: ... Left: 3 pending (why), 5 waits on 3."}
```

The summary says which steps finished, what the agent decided itself, and what is left and why. Write the file only
when stopping for good, never when ending a turn to wait for an answer: the worker reads it as the run's final
summary, and the Claude Code adapter takes it as the sign that the agent has finished. Keep `.evo-run/` out of every
commit. The worker then commits what is left in each worktree and pushes each plan branch whose commits origin
lacks; it runs no verify command at the end, since `evo-agents worker step` ran each step's.

## 10. Checklist

- [ ] Plan state loaded via `evo harness show` / `step --no-input`, not a full file read.
- [ ] Frontier computed from `depends_on` alone; checkpoint steps kept as barriers.
- [ ] Clustering stated, with any forced-serial reason; same-repo parallel steps in their own worktrees.
- [ ] A stale GitNexus index was refreshed with `--index-only`, never a bare analyze in the worktree.
- [ ] Subagents spawned as `plan-step` (or told to read `agents/plan-step.md`), with a short prompt and
      no pasted step text.
- [ ] Main session read no product code and accepted current verbatim evidence instead of re-running it.
- [ ] Commit checked and step recorded in one call, the evidence citing the commit hash, with evo-cli
      0.29.0 or later. In a hub harness no YAML was edited by hand.
- [ ] `evo harness check <slug>` clean after each cluster.
- [ ] No question between clusters; stopped only at outward-facing steps, user decisions, or when a
      failure left nothing else ready.
- [ ] In a worker plan run (`EVO_RUN_KIND=plan`): plan read with `evo-agents worker plan` before each
      cluster, same-repo steps serial in the run's worktree, steps recorded only with
      `evo-agents worker step` and runnable `--verify` commands, the owner asked only in the listed
      categories, a `Decision:` line for every other choice, a notice after each push or merge into a
      default branch, and `.evo-run/result.json` written once, at the end.
