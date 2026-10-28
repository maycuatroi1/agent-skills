---
name: hub-inbox
description: Clear what waits on the person on the evo-agents hub, across every hub and project, with `evo-agents hub inbox`: open decisions, credential requests, runs to approve, failed, lost or stuck runs, notices. Use for "check inbox", "check and solve/help me solve .../inbox", "inbox?decision=N", "check and answer decision", "check and give this credential: Decision #N", "cấp credential cho run", "run N treo à", "sao run này failed", "check and fix .../runs/N", or a hub link to a run or a decision.
version: 0.1.0
---

# Hub inbox

The person sends a hub link or says "check inbox" and expects every item that waits on them handled, with only the
real choices handed back. One CLI call reads it all; this skill says what to do with each item.

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
