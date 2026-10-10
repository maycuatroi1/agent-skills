---
name: execute-plan
description: This skill should be used when the user asks to "execute the plan", "run the plan", "implement plan <slug>", "làm tiếp plan", "thực hiện plan", "chạy plan", "triển khai plan", or names a plan under plans/active and wants it built rather than written. It reads the plan as the only state, computes the ready frontier from depends_on, groups steps into parallel-safe clusters, runs each step in a plan-step subagent that implements, verifies and commits it, writes status back from the main session, waits in the background for the required CI checks of a pull request it opened, and keeps going until the plan is done or needs the user. It also drives the agent of an evo-agents worker plan run (EVO_RUN_KIND=plan), reporting through evo-agents worker instead of evo harness.
version: 0.7.0
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

The subagent reads the step's `what`, `verify`, `note` and `acceptance`, and the plan's `acceptance`,
`non_goals` and `references`, itself. Do not paste them: quoting a step costs the main session output
tokens and adds nothing. Set `commit: no` only when the plan assigns the commit to a later step or
checkpoint. An outcome step may come back with several commits.

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

Stop and ask only when:

- the next step is outward-facing or hard to reverse: a push to a shared branch, a merge to the default
  branch, a release or publish, a deploy, creating or rotating credentials, changing a production
  database, or sending a message on someone's behalf;
- the plan text says the user decides or confirms;
- going on would change the contract: an acceptance criterion, an invariant, a non-goal, the seam order
  or the rollback;
- a step failed (section 8) and no other step is ready;
- the CI a step waits on gave no result in 90 minutes (below).

Everything else, a wrong file name in a step, an API shaped differently than the plan assumed, a better
order, an extra file to touch, is decided by the subagent or by you and recorded as a `Decision:` line.

### Wait for CI in the background

A step's verify, or a merge the plan asks for, may need the CI of a pull request: the verify calls
`gh pr checks` or checks that the PR is merged, or the plan says the checks must pass before the merge.
After the main session pushes such a branch or opens such a PR, it waits for the PR's required checks
itself, in the background. It never runs `sleep` in the foreground and never asks the user to say when
CI is done. On one plan, a red CI went unnoticed for almost four hours because the session stopped to
wait and only the user's message woke it. Plan-step subagents keep their rules (no push, no pull
request, no rebase), so the wait belongs to the main session.

Start the watch as a background command. In Claude Code that is Bash with `run_in_background: true`,
which wakes the session when the command exits; another runtime uses its own way to wait on a command.

```sh
end=$(( $(date +%s) + 5400 ))
gh pr checks <pr> --repo <owner/repo> --watch --required --fail-fast --interval 60 & w=$!
while kill -0 $w 2>/dev/null; do
  [ "$(date +%s)" -lt "$end" ] || { kill $w; echo "ci-wait: no result after 90 minutes"; exit 124; }
  sleep 10
done
wait $w
```

While it runs, go on with ready steps that do not depend on it, and end the turn when none is left.
When the command ends, read only the last lines of its output and act on its exit status:

- `0`: every required check passed. Do what was waiting: run the step's verify and record it as section
  5 says, or go on to the merge, which still needs the user's agreement when the first list above says
  so.
- `1`, printing `no checks reported` or `no required checks reported` at once: CI has not registered the
  push yet, or the PR has no required check. `gh run list --repo <owner/repo> --commit <sha>` tells
  which. Start the watch again, without `--required` when the PR has checks but none is required. When
  no workflow runs on the commit there is no CI to wait for; say so in the status line instead of
  inventing a check.
- `1` otherwise: a required check failed. Read the failed log of its whole workflow run, not only its
  job: a required check is often a summary job whose log says only that another job failed. The run id
  is the number after `/actions/runs/` in the link.

  ```
  gh pr checks <pr> --repo <owner/repo> --required --json name,bucket,link -q '.[] | select(.bucket=="fail") | .link'
  gh run view <run-id> --repo <owner/repo> --log-failed > "${TMPDIR:-/tmp}/ci-<run-id>.log"; tail -n 80 "${TMPDIR:-/tmp}/ci-<run-id>.log"
  ```

  Spawn a plan-step subagent on the step whose verify or merge waits on this CI, with the PR, the failed
  job, the log file and its failing lines as `context`; the step stays `pending`. Push the subagent's
  commits to the same branch, never forced (the user already agreed to push that branch), and start the
  watch again. When the log shows nothing from the repo's own commands (a lost runner, a cancelled run, a
  download that timed out), rerun the failed jobs once with
  `gh run rerun <run-id> --repo <owner/repo> --failed` instead of spawning a fix. When the same check is
  still red after two fix rounds, treat the step as failed (section 8).
- `124`: no result after 90 minutes. Ask the user, naming the PR and the checks still pending
  (`gh pr checks <pr> --repo <owner/repo> --required`), whether to wait longer or stop there.

A push with no pull request, straight to a branch the plan names, has no PR checks. Wait on the
workflow runs of the pushed commit instead: one wrapper as above for each id that
`gh run list --repo <owner/repo> --commit <sha> --json databaseId -q '.[].databaseId'` prints, with
`gh run watch <run-id> --repo <owner/repo> --exit-status --interval 60` in place of the `gh pr checks`
line. An empty list right after the push means CI has not started, not that it passed.

A `gh` that is missing or not signed in is an environmental blocker (section 8).

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
category or a `Decision:` line. The route of an outcome step is left open on purpose, so choosing it is not an
`architecture` decision: ask under `architecture` only for a choice that would change a contract the plan fixes (a
schema, an API, a CLI surface, a seam) or be hard to reverse. A wrong premise is a `Decision:` line, as section 8 says;
it becomes a `scope` decision only when no route reaches the step's outcome without changing an acceptance criterion,
an invariant or a non-goal. A step bigger than one subagent's context is not a decision: record what landed with
`pending` and spawn the next subagent on it.

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

**CI.** Section 6's wait for CI holds here, with the same watch, the same exit statuses and the same fix
subagents. `evo-agents worker step <id> done` runs `--verify` before it pushes, so a step whose verify
needs CI of a commit not yet on the remote is pushed by the agent first, as the paragraph above allows,
then recorded with `done` once the wait ends green. With Claude Code, the worker keeps the session open
at most 30 minutes after a turn ends while a background command runs, so put `1500` in place of `5400`
and start the watch again each time it ends with `124`, until 90 minutes have passed since the push. The
agent pushes fix commits to the run's branch itself, never forced, with the notice above when that is a
default branch. After 90 minutes without a result, ask the owner and end the turn:

```
evo-agents worker ask --category scope --question "CI of <PR or commit> gave no result in 90 minutes. Wait longer?" --option "wait=Wait 90 more minutes" --option "pending=Leave step <id> pending" --recommended wait --step <id>
```

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
      no pasted step text; one subagent per step, an outcome step included, and a few-call step done
      by the main session itself.
- [ ] Main session read no product code and accepted current verbatim evidence instead of re-running it.
- [ ] Commits checked and step recorded in one call, the evidence citing the last commit hash and every
      `Decision:` line of the report, with evo-cli 0.29.0 or later. In a hub harness no YAML was edited
      by hand.
- [ ] `evo harness check <slug>` clean after each cluster.
- [ ] No question between clusters; stopped only at outward-facing steps, user decisions, changes to
      the contract, or when a failure left nothing else ready. A wrong premise became a `Decision:`
      line, not a question.
- [ ] Every claim in a status line checked against a report or command output of this session.
- [ ] After a push or pull request whose CI a step's verify or a merge needs: required checks watched in
      the background with a 90-minute limit, no foreground `sleep`, no request that the user report CI;
      a red check's run read with `gh run view --log-failed` and handed to a fix subagent; the user asked
      only when 90 minutes passed without a result.
- [ ] In a worker plan run (`EVO_RUN_KIND=plan`): plan read with `evo-agents worker plan` before each
      cluster, same-repo steps serial in the run's worktree, steps recorded only with
      `evo-agents worker step` and runnable `--verify` commands, the owner asked only in the listed
      categories, a `Decision:` line for every other choice, a notice after each push or merge into a
      default branch, and `.evo-run/result.json` written once, at the end.
