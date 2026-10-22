# Inside a worker plan run

Part of the execute-plan skill: read it when `EVO_RUN_KIND` is `plan` (section 1). Section numbers here are those
of the skill's `SKILL.md`, and `agents/plan-step.md` sits next to it.

An evo-agents worker can take a whole plan as one run. Its daemon starts the agent in a run directory that holds a
worktree of each repo of the plan, on the branch the plan names for that repo, and `.evo-run/plan.yaml`, the plan as
the run was claimed. The environment has `EVO_RUN_KIND=plan`, `EVO_RUN_ID` and `EVO_WORKER_HOME`. The owner who
dispatched the run is not watching, and the hub keeps the plan. The agent reaches the hub only through four commands
that use the worker's token and refuse to run outside the run: `evo-agents worker plan`, `evo-agents worker step`,
`evo-agents worker ask` and `evo-agents worker notify`. They come with the evo-agents that runs the worker (0.4.0 or
later). Where this file differs from sections 1 to 8, it wins.

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
does not commit them. Each subagent starts fresh and reads the handoff for its step, as section 4 says; the
worker's own note to the agent asks the same. `EVO_RUN_PLAN` and `EVO_RUN_PROJECT` name the plan and the project
for `evo-agents hub plan handoff`, which needs this machine to be signed in to the hub. When it is not, the
subagent reads the evidence of the steps its step depends on from `evo-agents worker plan --json`.

**Record each step.** Subagents never report to the hub. The main session marks a step when it spawns the subagent
and records it after reading the report:

```
evo-agents worker step <id> in_progress --repo <repo>
evo-agents worker step <id> done --repo <repo> --evidence "<text>" --verify "<command>"
evo-agents worker step <id> pending --repo <repo> --evidence "<what landed, what failed, the stash>"
```

`done` checks the step with its `--verify` commands, run with `/bin/sh` in the repo's worktree (repeat `--verify` once
per command), and refuses the step when one exits non-zero. Otherwise it commits what is left in the worktree, pushes
the run's branch to the branch the plan names (never forced), and records the commit with the step.

The verify runs once per step, as a job of the worker: the subagent ran it with `evo-agents worker step <id> verify
--repo <repo> --verify "<command>"` (`agents/plan-step.md`), and `done` with the same commands takes that pass while
the worktree is unchanged, runs nothing again, and ends the evidence with a line naming the job it reused. When the
tree or the commands differ, or the pass is missing, `done` runs the job itself, so pass the report's `effective`
command verbatim: one that differs by a character is another verify. Both commands wait up to 540 seconds
(`--wait`): give the call a timeout of 10 minutes, and when one exits 124 the job still runs, so run the same command
again to wait on it. Never run the verify in your own shell first, never wait with `sleep` loops or `setsid nohup`, and
leave the worktree alone between the subagent's report and `done`. A replay onto a default branch the remote moved on
runs the verify again on the new tree, as it must. Take the commands from the
report's `verify_command`, the effective one when it differs, as they run from the worktree root: a plan `verify` that
starts with `cd ~/github/<repo>` points at a developer's checkout, not at this worktree. The hub writes the run,
`repo@commit` and each verify command's exit code into the evidence itself, so `--evidence` says what was done, plus
the `Decision:` lines below. When the pull request's CI ran some of the verify's suites green on the commit being
recorded, pass the rest of the verify and `gh pr checks <pr> --repo <owner/repo>` to `--verify` in their place, and
name the CI run in `--evidence`. Never use `evo harness step`, `evo-agents hub plan` or the hub's `plan_step` tool here:
the hub writes the step from the worker's report, as the member who dispatched the run.

**Ask only what the owner must decide.** Use `evo-agents worker ask` only for a decision of one of the categories the
run's prompt lists. Merging, deploying and releasing are yours: never ask under `deploy`, even when an older prompt lists
it.

- `delete_data`: deleting data that is not the run's own scratch: database rows, files, buckets, other people's
  branches;
- `live_migration`: a migration, backfill or bulk change on real data rather than a test database;
- `external_send`: sending anything to a service outside the machine and the repos' own remotes: mail, chat, issues,
  third-party APIs;
- `spend_money`: anything that costs money beyond the runtime's own usage: paid APIs, cloud resources, purchases;
- `architecture`: an architectural choice the plan leaves open;
- `scope`: a question of scope the plan leaves open: adding, dropping or reshaping a step or what it delivers.

```
evo-agents worker ask --category live_migration --question "<one or two sentences>" --context-file <notes.md> --option "go=Backfill now" --option "hold=Wait:Backfill after the owner checks a sample" --recommended hold --step <id>
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

**Checkpoints.** A checkpoint step (full-suite verification, review, merge, release, deploy) is the agent's: do it like
any step, with no question. When it includes anything in the list above, ask first with `--step <id>`, do the parts that
do not depend on the answer, and end the turn.

**Push and merge.** The agent may push, and merge into, the branch the plan names for a repo, even when it is the
repo's default branch. It never pushes or merges into a branch the plan does not name for that repo, never
force-pushes, and never rewrites history it pushed. A step that needs more, such as merging a feature branch the plan
names into `main`, is a `scope` decision. `evo-agents worker step <id> done` sends its own notice for its pushes; after
a push or merge into a default branch the agent makes itself, it runs:

```
evo-agents worker notify --kind merge_default_branch --title "<one line>" --body "<what and why>" --repo <repo> --branch <branch> --commit <sha>
```

with `--kind push_default_branch` for a push, and `--commit` once per commit.

**CI.** The wait for CI of `ci-wait.md`, next to this file, holds here, with the same watch, the same exit
statuses and the same fix subagents. `evo-agents worker step <id> done` runs `--verify` before it pushes, so a step whose verify
needs CI of a commit not yet on the remote is pushed by the agent first, as the paragraph above allows,
then recorded with `done` once the wait ends green. With Claude Code, the worker keeps the session open
at most 30 minutes after a turn ends while a background command runs, so put `1500` in place of `5400`
and start the watch again each time it ends with `124`, until 90 minutes have passed since the push. The
agent pushes fix commits to the run's branch itself, never forced, with the notice above when that is a
default branch. A merge that needs the owner's consent and waits on CI is asked with
`evo-agents worker ask` as soon as the PR is open, worded "merge PR <n> once its required checks pass?",
with the watch started in the same turn; on `0` with a yes, merge without asking again.
After 90 minutes without a result, ask the owner and end the turn:

```
evo-agents worker ask --category scope --question "CI of <PR or commit> gave no result in 90 minutes. Wait longer?" --option "wait=Wait 90 more minutes" --option "pending=Leave step <id> pending" --recommended wait --step <id>
```

**Blocked is not done.** A frontier emptied by a block is not a stop. When what blocks the steps left is something
only the owner can change (a permission of the GitHub App, a credential, an account, access to a service, a push the
remote refuses), ask a `scope` decision that names what the owner must do, with a way around the block among the
options when there is one, and end the turn. When the answer did not lift the block (the push is still refused, the
access still missing), ask again with what you found and the options left; never end the run on it. A turn that ends
with no decision open ends the run: the worker pushes what is committed and lets the session go.

**Stop.** When every step is done, or the owner's answer says to stop, and no decision is open, write
`.evo-run/result.json` in the run directory, not in a repo, and end the turn:

```json
{"summary": "Done: 1, 2, 4. Decided: ... Left: 3 pending (why), 5 waits on 3."}
```

The summary says which steps finished, what the agent decided itself, and what is left and why. Write the file only
when stopping for good, never when ending a turn to wait for an answer: the worker reads it as the run's final
summary, and the Claude Code adapter takes it as the sign that the agent has finished. Keep `.evo-run/` out of every
commit. The worker then commits what is left in each worktree and pushes each plan branch whose commits origin
lacks; it runs no verify command at the end, since `evo-agents worker step` ran each step's.

**A session per step.** A plan run dispatched with `evo-agents hub run plan <plan> --session-per-step`, or with the
switch in the hub's Run plan box, gives each step not done yet a new agent session of its own, in the order
`depends_on` allows. That session's prompt starts `You are running step <key> of the plan <id>`, says the session
runs `in an agent session of its own`, tells it to do that step and nothing else, holds the step's what, verify and
note, and ends with the handoff of the plan for the step. `EVO_RUN_KIND` is `plan` there too and `EVO_RUN_STEP` is
empty, so the prompt is how to tell. In such a session this skill does not drive the plan: no frontier, no clusters,
no other step, and no subagent for a step the prompt does not name. Do the named step in this session as its prompt
says; its rules for `evo-agents worker step`, `evo-agents worker ask` and `.evo-run/result.json` win over the rest of
this file. The Work and Commit sections of `agents/plan-step.md` still hold for the edits, the verify and the
commits; recording the step is this session's own job, with the commands its prompt gives. The handoff is already in
the prompt: read the plan with `evo-agents worker plan` only for what it left out. When one part of the step would
crowd this session's context, hand that part to a fresh subagent as section 4 says. The daemon starts the next step's
session after this one ends.

## Checklist

- [ ] In a worker plan run (`EVO_RUN_KIND=plan`): plan read with `evo-agents worker plan` before each
      cluster, same-repo steps serial in the run's worktree, steps recorded only with
      `evo-agents worker step` and runnable `--verify` commands, each step's whole verify run once through
      `evo-agents worker step <id> verify` and reused by `done`, the owner asked only in the listed
      categories, a `Decision:` line for every other choice, a notice after each push or merge into a
      default branch, and `.evo-run/result.json` written once, at the end.
- [ ] In a plan run with a session per step (the prompt says `in an agent session of its own`): only
      the named step done, recorded with the commands its prompt gives, no frontier and no other step.
