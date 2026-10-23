---
name: execute-plan
description: Run an existing exec-plan to completion. Use when the user asks to "execute the plan", "run the plan", "implement plan <slug>", "làm tiếp plan", "thực hiện plan", "chạy plan", "triển khai plan", or names a plan under plans/active to build rather than write. Each step runs in a fresh plan-step subagent; the main session writes status and waits on CI. Works in Claude Code and Codex, and drives an evo-agents worker plan run (EVO_RUN_KIND=plan).
version: 0.14.0
---

# Execute exec-plan

Drive an existing `plans/active/<slug>.yaml` to completion. The plan is the only durable state, so
the main session stays thin: it orchestrates, checks reports, and writes state. Subagents read, edit,
test and commit, and their context dies with them.

The plan fixes the contract: goal, acceptance criteria, invariants, non-goals, seam order, checkpoints.
Inside that contract the agent doing the work chooses the route. A step with an `acceptance` list is an
outcome step: it says what must become true, and the files, the order and the commits are the
subagent's to choose. A step without one is prescribed: its `what` fixes the operations, because a wrong
route there cannot be undone. Either way, a choice the plan did not make is made by whoever holds the
code in context, and written down as a `Decision:` line, not sent to the user.

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

The saving holds only when each subagent starts with a fresh context. A forked subagent (Claude Code's
`fork` subagent type, or Codex's `spawn_agent` with `fork_turns` left at its default `"all"`) starts with
a copy of the main session's history: it pays for every turn before it and gains nothing the step needs.
Spawn every subagent fresh, as section 4 says, and let it read the plan's handoff instead of any history.
`evo-agents hub plan handoff <slug> --step <id>`, or the evo-hub MCP tool `plan_handoff` with the same
plan and step, returns the same text: the plan's goal, each step done with its title, commits and
`Decision:` lines verbatim, the evidence of the steps this one depends on first, and the steps not done
with their status and `depends_on`, within a token budget (`--budget-tokens`, 1000 to 8000, default
4000). A note at its end names what the budget left out; `plan_show` has the plan whole. The hub builds
the handoff from the plan it holds, so it is as current as the main session's writes of section 5.

One subagent owns one step, an outcome step included, however many files and commits it takes: its
writes stay in one thread and its choices stay consistent. Do not split a step into smaller subagent
tasks from the main session, and do not run a separate subagent to re-verify one that reported a pass.
The exception is a step small enough to finish in a few tool calls, such as a version bump or one line
of documentation: spawning costs more than the work, so the main session does it, following
`agents/plan-step.md` for the verify, the commit and the report it would have received.

This workflow is evidence-driven, not ceremony-driven. Do not repeat a command when the same working
tree state already has trustworthy verbatim output from the subagent. Do not run full-repo checks for
targeted steps unless the plan explicitly makes them acceptance criteria or the repository cannot run
the target in isolation.

Test less, and lean toward the broad check at the end. No baseline run of a verify before the work
starts, unless there is reason to think the branch already fails it; no rerun on a tree that has not
changed since a passing run; no whole suite "for regressions" in a step whose verify does not ask for
one. The plan's late step and the pull request's CI carry the broad check. This is a default, not a
rule: a subagent may test wider when its change is risky or touches code many others depend on, and
writes why as a `Decision:` line.

## 1. Load state cheaply

First check `echo "${EVO_RUN_KIND:-}"`. `plan` means this session is the agent of an evo-agents worker plan run:
there is no harness checkout and no `evo harness`; read `references/worker-plan-run.md` next to this file now, since
it says what replaces them (section 9). When the run's prompt starts `You are running step <key> of the plan <id>`
and says the session is `in an agent session of its own`, the run gives each step a session of its own
(`EVO_RUN_KIND` is still `plan` and `EVO_RUN_STEP` is empty): do only that step, as that file ends by saying.
`step` means a run of one step, whose prompt, not this skill, says what to do.
Empty means an ordinary session; read on.

```
evo harness show <slug>
evo harness step <slug> --no-input     # step board: id, repo, status, depends_on
evo harness show <slug> --step <id>    # one step in full (evo-cli 0.30.0 or later)
```

Use these, not `Read` on the YAML. A mature plan is 25k+ tokens of prose; the board is a few hundred.
The main session rarely needs a step's full text, since the subagent reads its own step; when it does
(a checkpoint, a clustering question), `--step` prints it instead of a script on the YAML.

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

In Claude Code, the Agent tool's `isolation: "worktree"` makes a worktree of the session's own repository.
In a harness session that is the harness, not the code repo, so do not use it for code steps. Codex has no
such option; the `git worktree add` above serves both runtimes.

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

## 4. Spawn a fresh plan-step subagent

The subagent contract lives in `agents/plan-step.md` next to this file: what the subagent may and must
not do, how it reads the plan and its handoff, how it verifies and commits, and the exact report it
returns. The main session does not restate it per step.

Every subagent starts with a fresh context: never a fork of this session, and never an earlier subagent
resumed for another step or another fix round. How to spawn one depends on the runtime:

- **Claude Code.** The Agent tool with `subagent_type: "plan-step"`. Never `subagent_type: "fork"`, and
  never send a new step to a finished subagent with SendMessage: both carry history the step does not
  need. When the `plan-step` agent type is missing, link it once:

  ```
  mkdir -p ~/.claude/agents && ln -sf <this skill's directory>/agents/plan-step.md ~/.claude/agents/plan-step.md
  ```

  Until the runtime has loaded it, spawn a `general-purpose` subagent whose prompt starts with
  `Read <this skill's directory>/agents/plan-step.md and follow it.` The `plan-step` type asks for a
  one-hour prompt cache (`experimental.cacheTtl: 1h` in its frontmatter, Claude Code v2.1.248 or later),
  since a step often waits longer than five minutes on a test; that fallback and other subagents keep
  the default.
- **Codex.** `spawn_agent` with `fork_turns: "none"`. Its default, `"all"`, copies every turn of this
  session into the subagent; `fork_context` is deprecated, so do not use it either. Codex has no
  `plan-step` agent type, so leave `agent_type` out and start `message` with
  `Read <this skill's directory>/agents/plan-step.md and follow it.`, followed by the prompt below. Name
  the task after the step (`task_name: "step_7"`). Spawn every step of a cluster before waiting, then call
  `wait_agent` (with the agents' ids where the tool takes them; some Codex versions take only
  `timeout_ms`) until each subagent's final answer, its report, has come back. It also returns on another
  message or on its timeout, so call it again until every report is in.
- **Other runtimes.** Their way to start a subagent with an empty context, with the same first line.

The prompt carries only what the contract, the plan and its handoff cannot:

```
plan: <slug>
harness: <harness directory>
step: <id>, or a chain such as 7,8
repo: <main checkout or worktree path>
branch: <branch it commits on>
mode: serial | parallel
commit: yes | no
context: <at most 10 lines that neither the plan nor its handoff holds: what the user said in this
session, a trap an earlier report found that its evidence does not name, a commit of this run not
recorded yet>
```

The subagent reads the step's `what`, `verify`, `note` and `acceptance`, and the plan's `acceptance`,
`non_goals` and `references`, itself, then the handoff for its step, as the Inputs of
`agents/plan-step.md` say: the commits and `Decision:` lines of the steps it depends on come from there.
Do not paste any of it, and do not retell earlier reports or this session's history: quoting costs the
main session output tokens, and the handoff holds the recorded `Decision:` lines verbatim. A harness
without a hub has no handoff; there the subagent reads the `evidence` of the steps its step depends on
in the plan file. Set `commit: no` only when the plan assigns the commit to a later step or checkpoint.
An outcome step may come back with several commits.

Do not spawn a separate review agent by default. Add an independent review only when per-symbol impact
is HIGH or CRITICAL, the step changes an authorization, secret or destructive-mutation boundary, or the
user asks for review.

## 5. Write state back, from the main session only

Subagents never write plan state. The main session writes it once per step, after reading the report.
For each report, in plan order:

1. Check that it has the exact command, `result: pass`, verbatim output, and at least one commit sha
   when `commit: yes`. Do not re-run a check the report already shows passing on its last commit.
2. Re-run only what is missing or failed, external or manual acceptance the subagent could not do, and
   checks a later merge invalidated. A verify that needs CI runs once the wait of section 6 ends green.
3. After a parallel same-repo cluster, merge each step branch into the plan branch in step order with
   `git -C <repo> merge --no-ff <plan-branch>-step-<id>`, then run the merged steps' verify commands
   once, together in one call. On a merge conflict, abort the merge, leave that step `pending`, and run
   it again serially on the merged branch. Remove merged worktrees and their branches.
4. Check the commits and record the step in one call:

   ```
   git -C <repo> log --stat --format='%h %s' <first-sha>^..<last-sha> && \
   evo harness step <slug> <step-id> done --evidence "<repo>@<last-sha>: <verify result>
   Decision: <one line per entry of the report's decisions>"
   ```

   Word the evidence like the steps already closed in the same plan, and carry every `Decision:` line of
   the report into it unchanged: they are how the user and later steps learn what the plan did not say.
   Compare the `--stat` list with the report's `files` and `outside_scope`; a file you did not expect is
   a reason to question the report, not to read the code.
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
shas, and the next cluster. Before writing it, check each claim in it against a report or command output
of this session; say "not verified" for anything you cannot point to.

Pushing a branch, opening a pull request, merging it into the default branch, deploying and tagging a
release are yours to do without asking (in a worker plan run, only when the run's autonomy card shows merge and
deploy as auto or notify: `references/worker-plan-run.md`). Before the merge, test locally the cases the change puts at
risk; the broad run is the full CI of a release tag, not a wait on pull-request CI.

Stop and ask only when:

- the next step destroys what cannot be rebuilt: a force-push to the default branch, deleting a branch,
  a repository or data someone else uses, or changing a production database outside a migration the
  deploy backs up;
- the next step creates or rotates credentials, spends money, or sends a message on someone's behalf;
- the plan text says the user decides or confirms;
- going on would change the contract: an acceptance criterion, an invariant, a non-goal, the seam order
  or the rollback;
- a step failed (section 8) and no other step is ready;
- the CI a step waits on gave no result in 90 minutes (`references/ci-wait.md`).

When the repository runs required checks on the pull request, start the background watch below as soon
as the PR is open and merge when it ends with `0`. A red check leaves the PR open and is handled as
`references/ci-wait.md` says.

Everything else, a wrong file name in a step, an API shaped differently than the plan assumed, a better
order, an extra file to touch, is decided by the subagent or by you and recorded as a `Decision:` line.

Nothing lets an agent clear its own context. When the session passes about half its window, say so
once in the status line together with the re-entry command, for example
`/execute-plan deployments-control-plane` in Claude Code, and keep going; whether to clear is the user's
call. Re-entry costs one `evo harness show` plus one step board: the subagents read what earlier steps
decided from the handoff, so the new session needs none of this one's history.

### Wait for CI in the background

When a step's verify or a merge needs the CI of a pull request (the verify calls `gh pr checks` or checks
that the PR is merged, or the plan says the checks must pass before the merge), the main session waits
for the PR's required checks itself, in the background. It never runs `sleep` in the foreground, never
asks the user to say when CI is done, and never ends a turn while a step waits for CI unless a background
watch for that PR or run is still running. Plan-step subagents never push or open a pull request, so the
wait is the main session's. Before pushing such a branch or opening such a PR, read
`references/ci-wait.md` next to this file: the watch command, its 90-minute limit, and what to do on each
exit status, a red check and a push without a PR included.

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
- The step's premise is wrong (the file it names does not exist, the API shape differs): that is a
  route problem, not a failure. The subagent finds the way to the step's outcome and reports the choice
  as a `Decision:` line. Ask the user only when no route reaches the outcome without changing the
  contract (section 6), and then name the criterion, invariant or non-goal that would change.
- The step is bigger than one subagent's context: keep what is verifiable, record with
  `evo harness step <slug> <step-id> pending --evidence "..."` exactly which part landed (partial work is
  never `done`), and spawn the next subagent on the same step with that evidence as its `context`.
  Do not split the step in the plan to make it fit.

A subagent whose verify failed in the main checkout stashes its changes and reports the stash, so the
next serial step starts clean. Put the stash name in the step's evidence.

A failed `blocking: true` step means the plan cannot finish without it; say so in the final report. A
failed `blocking: false` step can be left behind if the user accepts it.

## 9. Inside a worker plan run

When `EVO_RUN_KIND` is `plan`, the rules are in `references/worker-plan-run.md` next to this file: reading
the plan with `evo-agents worker plan`, the clusters and subagents of a run, recording steps with
`evo-agents worker step`, the autonomy card at the head of the prompt (what to do, ask or leave), asking the
owner with `evo-agents worker ask`, pushes and their notices, CI,
blocks, `.evo-run/result.json`, and a run with a session per step. Read it before the first cluster;
where it differs from sections 1 to 8, it wins.

## 10. Checklist

- [ ] Plan state loaded via `evo harness show` / `step --no-input`, not a full file read.
- [ ] Frontier computed from `depends_on` alone; checkpoint steps kept as barriers.
- [ ] Clustering stated, with any forced-serial reason; same-repo parallel steps in their own worktrees.
- [ ] A stale GitNexus index was refreshed with `--index-only`, never a bare analyze in the worktree.
- [ ] Subagents spawned as `plan-step` (or told to read `agents/plan-step.md`), with a short prompt and
      no pasted step text; one subagent per step, an outcome step included, and a few-call step done
      by the main session itself.
- [ ] Every subagent started with a fresh context, never a fork or a resumed one (Claude Code: no
      `fork` subagent type; Codex: `spawn_agent` with `fork_turns: "none"`), and read the plan's
      handoff (`evo-agents hub plan handoff`, or the evo-hub tool `plan_handoff`) instead of this
      session's history.
- [ ] Main session read no product code and accepted current verbatim evidence instead of re-running it.
- [ ] No baseline run, no rerun on an unchanged tree, and no whole suite a step's verify did not ask for,
      unless a `Decision:` line says why; suites the CI ran green on the recorded commit cited, not rerun.
- [ ] Commits checked and step recorded in one call, the evidence citing the last commit hash and every
      `Decision:` line of the report, with evo-cli 0.29.0 or later. In a hub harness no YAML was edited
      by hand.
- [ ] `evo harness check <slug>` clean after each cluster.
- [ ] No question between clusters; stopped only at the stop list of section 6, user decisions, changes to
      the contract, or when a failure left nothing else ready. A wrong premise became a `Decision:`
      line, not a question.
- [ ] Every claim in a status line checked against a report or command output of this session.
- [ ] After a push or pull request whose CI a step's verify or a merge needs: `references/ci-wait.md`
      read, required checks watched in the background, and its checklist met.
- [ ] In a worker plan run (`EVO_RUN_KIND=plan`): `references/worker-plan-run.md` read before the first
      cluster, and its checklist met.
