---
name: hub-inbox
description: Clear what waits on the person on the evo-agents hub, across every hub and project, with `evo-agents hub inbox`: open decisions, credential requests, runs to approve, failed, lost or stuck runs, notices. Use for "check inbox", "check and solve/help me solve .../inbox", "inbox?decision=N", "check and answer decision", "check and give this credential: Decision #N", "cấp credential cho run", "run N treo à", "sao run này failed", "check and fix .../runs/N", or a hub link to a run or a decision. Also the playbook of the Orchestrator of a project's default system in an ops thread ("Ops: <slug>" chat).
version: 0.2.0
---

# Hub inbox

The person sends a hub link or says "check inbox" and expects every item that waits on them handled, with only the
real choices handed back. One CLI call reads it all; this skill says what to do with each item.

The Orchestrator of a project's default system, mentioned in a thread of the chat "Ops: <slug>", reads section 4
first: it works one batch, with fewer rights than a person.

## 1. Read

```bash
evo-agents hub inbox --json                    # every hub this machine is signed in to, every project you read
evo-agents hub inbox --show <link or id>       # one item whole: 582, d582, r1092, #1092, .../inbox?decision=582, .../runs/948
```

- `--show` finds the project and the hub itself. Do not add `--project` by guess, and do not open the Inbox in a
  browser to read it.
- Each item has `next`: the command that acts on it, already prefixed with `EVO_HUB_HOME=...` when it is on a second
  hub. Run it as given; do not rebuild it.
- `hub inbox` an invalid choice: the CLI predates it. Update it with the `update-evo-agents` skill, or fall back to
  `evo-agents hub notifications --unread` and `evo-agents hub decision show ID --project P`.
- Before acting, read the person's standing rules once: `evo-agents hub autonomy show --project P` and the memory index
  of the harness. A rule there answers most questions agents ask.

## 2. Act, item by item

| Item | What to do |
| --- | --- |
| `credential` (a decision with a credential request) | The value never goes into words: not the decision text, chat, a commit, a file or the transcript. If the person keeps it in `evo cred`, pipe it: `evo cred get KEY \| evo-agents hub decision answer ID --project P --secret`. If a hub secret already holds it, answer `--option as_me` (the run leases the owner's secrets) and say its name in `--text`. Otherwise list it for the person. |
| `decision` that asks for a token, key, ssh, login or access in prose | Treat it as a credential. Put the value on the hub as a secret bound to the project, `evo cred get KEY \| evo-agents hub secret set NAME --kind env --env-var VAR --project P`, then answer naming the variable and telling the run to read its leases again. Say in the answer that the next ask should be `evo-agents worker ask --env-var VAR`. |
| `decision` the standing rules already answer: merge, deploy, release mechanics, installing a missing tool, rerunning elsewhere, waiting | Answer with the option the rules give (usually the recommended one) and cite the rule in `--text` in one line, so the agent stops asking. |
| `decision` that needs the person's judgment: product scope, spend over budget, a message to people, an act that cannot be undone without a backup | Do not answer. List it for the person with the question, the options and the agent's recommendation. |
| `review` | Read `evo-agents hub run show ID --project P`: verify passed and the diff matches the step, then `evo-agents hub run approve ID --project P`. |
| `failed`, `lost` | `--show r<ID>` gives the cause. `credentials`: fix the secret or the GitHub access, then rerun. `missing_tool`: install it on that worker (daemon PATH), then rerun. `rate_limit`: `evo-agents hub run rerun ID --project P --account NAME` with another account. Lease lost or worker offline: `evo-agents hub run rerun ID --project P` (a fit worker takes it). `branch_mismatch`, `push_conflict`: rerun; it gets a fresh worktree. A line with "and N more alike" is one root cause: fix it once, then rerun the newest. |
| `stale` (running, no event for a while) | Read the last events in `--show`. Worker offline (`evo-agents worker list`): cancel with `evo-agents hub run cancel ID --project P` and rerun. Agent inside a long command or a background wait: leave it and say so. |
| `notice`, `proposal` | Do what it asks (review a baseline, answer a mention, look at a paused breaker), then `evo-agents hub notifications --read ID`. |
| asked of someone else | Their decision. Mention it only if it blocks one of the person's runs. |

Rules that hold for every item:

- Anything you would ask the person and the standing rules already decide, decide.
- A failure the same cause keeps producing is a fix to the harness or the hub, not one more rerun: name it in the
  report as a follow-up.
- Never print a credential's value; check presence with `[ -n "$VAR" ]` or a length.

## 3. Report

One table: the item, what you did (with the command), what is left for the person and why. Then run
`evo-agents hub inbox` again and say what it still lists.

## 4. In an ops thread of the default system

A project whose default system turns `ops` on gets one thread a batch in the chat "Ops: <slug>". The hub mentions
the system's Orchestrator there with a summary of the batch: each item, its cause, a short diagnosis and the
`evo-agents hub inbox --show ID` command for it. You work that batch and nothing else.

Read:

- The summary is your inbox. Do not run `evo-agents hub inbox` for the whole hub; open one item with its
  `--show` command when the diagnosis is too short to act on.
- `evo-agents hub system ops show SLUG --project P` gives the pause, the budget and what the threads spent;
  `evo-agents hub system ops batches SLUG --project P` lists earlier batches, to see whether a cause came back.
- `evo-agents worker list` says which workers are online, their free disk and the runtimes logged in.

Act on a worker with `evo-agents worker ops ...`, or with the tool `ops_action` on the hub runtime. Each command
takes `--reason TEXT`, which becomes the `Decision:` line, and works only on items of this batch.

| Item | What to do |
| --- | --- |
| `run.ended`, cause of the machine (`checkout`, `worker_stopped`, `lease_lost`, `network`, `hub_5xx`, `account_auth`) | Tier 0 already handed it again once. If the worker is still unhealthy, `evo-agents worker ops redeliver RUN --reason TEXT` gives it to a healthy worker; a 409 means none is, so fix the worker first. |
| `run.ended`, another cause | Fix what the cause names, then `evo-agents worker ops rerun RUN --reason TEXT`. It takes chat and task runs only: a run of a step, plan or author has its own triage, so list it in the report. |
| `decision.opened`, category `wait`, stuck | `evo-agents worker ops answer-wait DECISION --text TEXT --reason TEXT`, with what the run waits for. A decision of another category is the owner's: the hub refuses it, and you put it in your report. |
| `curator.paused` | `evo-agents hub curator status --project P` gives the reason and its class. Fix the cause (the tool, the login, the disk, the secret), run one command that failed before and now passes, then `evo-agents worker ops curator-resume --reason TEXT`, the ops form of `evo-agents hub curator resume`: it resumes only the schedules the breaker paused, never one a person paused. A breaker that trips again the same night is `recurring`. |
| `worker.health` | Disk low: remove worktrees of runs that ended and caches on that worker. A runtime not logged in: log it in if the owner's standing rules allow, else ask. |
| a notice whose work is done | `evo-agents worker ops read NOTICE --reason TEXT`. |
| marked `recurring` | Do not run it again. Write the fix down: `evo-agents worker ops finding --lens LENS --severity low\|medium\|high --title TEXT --body TEXT --reason TEXT` for the Curator, or `evo-agents hub task create --project P --title TEXT --description MARKDOWN` when it is code to change. |
| work an agent of the system should do | `evo-agents worker triage reassign HANDLE --note TEXT --reason TEXT`. |

Limits of an ops thread:

- No question in prose. When only the owner can decide, ask one decision for the whole batch:
  `evo-agents worker triage ask-owner --question TEXT --option KEY=LABEL ... --reason TEXT`. A second one is
  refused, so put every open choice of the batch in it. `triage answer` is refused in an ops thread.
- The owner's choices stay theirs: a credential of someone else's run, product scope, spend over the cap, anything
  that cannot be undone without a backup. Name them in the report and the daily `ops_digest` carries them.
- ssh only into the workers of the project's owner: the person who opened the thread, whose login prefixes the
  worker's name in `evo-agents worker list`. Before you overwrite a file on a worker, copy it next to itself with a
  dated suffix.
- Never print a credential's value. Check presence with `[ -n "$VAR" ]` or a length, and pipe a value from
  `evo cred get KEY` straight into the command that needs it.
- Name only commands the CLI has. `evo-agents hub contract check skills/hub-inbox/SKILL.md` lists the ones it lacks.

End with one message in the thread: each item, the command you ran, what is left for the owner and why.
