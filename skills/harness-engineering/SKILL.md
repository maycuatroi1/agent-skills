---
name: harness-engineering
description: This skill should be used when the user asks to "build a harness", "harness engineering", "audit my agent setup", "set up AGENTS.md across my repos", "why does Claude keep forgetting how to run this", "my repos keep breaking each other", "multi-repo agent context", "doc gardening", or mentions maintaining agent scaffolding across a CLUSTER of tightly-related repos (multiple repos, one system). A harness is the environment + constraints + feedback loops around a coding agent: AGENTS.md maps, a docs/ system of record, init scripts, acceptance specs, mechanical linters, cross-repo exec-plans, golden principles. Provides scripts to score a cluster against a 12-dimension rubric (audit), detect drift (doctor), turn real session evidence into proposals for what the harness is missing (garden), and track changes that span N repos with an explicit merge order (plan). Use create-exec-plan when the requested outcome is authoring a complete execution plan. Built on Anthropic "Effective harnesses for long-running agents" and OpenAI "Harness engineering".
version: 0.1.2
---

# Harness engineering

A **harness** is everything around the agent that is not the model: the map it reads on arrival, the
script that boots the app, the spec that defines done, the linter that says no, the plan that survives
the context window. Two 2025-2026 articles converged on the same finding - when an agent underperforms,
the environment is usually underspecified, and the fix is almost never "try harder."

This skill applies that to a **cluster**: several repos that belong to one system, where a change to one
routinely forces a change to another. Both source articles are written for a single repo. The cluster
layer - the manifest, the seam registry, the cross-repo exec-plan - is this skill's extension, and the
place where harnesses actually tear.

It does three things and then keeps doing the third:

- **Analyze** - score the cluster against a 12-dimension rubric, report the top gaps.
- **Build** - scaffold what is missing: maps, boot scripts, specs, principles, a seam registry.
- **Maintain** - watch real sessions, and when the agent stumbles, name the artifact that would have
  prevented it. This is the part that makes it a system instead of a template pack.

## When to use

- Several repos, and a change to one keeps forcing a change to another.
- Claude re-derives how to run the app in every session.
- An agent broke a sibling repo because nothing told it the seam existed.
- Long agent sessions drift, declare victory early, or leave the tree broken.
- You keep correcting the agent about the same thing and the correction never sticks anywhere.
- One repo has fifty skills and its siblings have one.

**Skip it when:**

- **One repo.** Use the source articles directly; you do not need a cluster layer.
- **The repos do not actually touch.** Five projects in one folder is not a cluster. If a change to one
  never forces a change to another, this skill only adds ceremony. Say so and stop.
- **The cluster should be a monorepo.** If every change touches all three repos and every plan has the
  same merge order, the repo boundary is a tax, not a boundary. That is the honest finding, and no
  amount of scaffolding fixes it.

## Architecture

```
harness root (a repo of its own, or .harness/ in the workspace)
  harness.yaml           cluster manifest: repos, roles, which are not cloned here
  contracts.yaml         seam registry: what crosses repo boundaries, and what verifies it
  deployments.yaml       deployment registry: where each service runs (environment, host/URLs, tenant)
  CLUSTER.md             the cluster map (~100 lines, a table of contents)
  principles/
    golden-principles.md rules learned the hard way, not yet mechanized
    invariants.md        rules a machine enforces; each names its lint
  plans/active/          cross-repo exec-plans with an explicit merge order
  state/
    scan.json            last snapshot of every repo
    sessions/<id>.json   raw session facts, written by the hook (no model)
  proposals/_pending/    what the harness is missing, awaiting your review
```

The maintain loop, which is the point:

```
SessionEnd hook  ->  state/sessions/<id>.json      cheap, no model, just facts
                          |
                     garden (batched)              the model reads the facts against the taxonomy
                          |
                     proposals/_pending/           cited evidence, one gap each
                          |
                     you review  ->  apply         lands on a branch, never pushed
```

Two decisions worth knowing about, because they are the difference between a loop you trust and one you
learn to ignore:

**The hook does not classify.** It writes down what happened - the commands, the errors, the user turns -
and stops. Deciding "was that a correction?" with a regex is exactly the brittle inference that produces
noise. The model does the interpreting later, in batch, with the taxonomy in front of it.

**Batching is not just a cost trick.** One session where Claude fumbles the boot command is noise. The
same fumble across three sessions is an `init.sh` that does not exist. Most signals only become legible
across sessions.

## Install

Requires Python 3 and PyYAML (`pip install pyyaml`). Works on Windows and POSIX.

```bash
cd <this skill>/scripts
python harness.py init --workspace ~/github --name my-cluster
python harness.py audit
```

`init` discovers the git repos under the workspace, guesses each one's role, writes `harness.yaml`, and
registers the cluster in `~/.claude/harness/registry.json` so every later command resolves the cluster
from any directory inside it.

Filter what it picks up with `--include` / `--exclude` (comma-separated regexes on the repo name).

Repos that belong to the cluster but are **not cloned on this machine** must be added to `harness.yaml`
by hand with `present: false`. That is not a bug: a repo being absent is fine, and a document pretending
it is present is not.

### The maintain loop (optional, adds the hook)

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "powershell -NoProfile -ExecutionPolicy Bypass -File \"<abs path>/skills/harness-engineering/scripts/session-end.ps1\""
      }]
    }]
  }
}
```

On POSIX use `session-end.sh` and `chmod +x` it once.

`SessionEnd`, not `Stop`, on purpose. `continuous-learning` already owns `Stop` and already spends a
`claude -p` there. This hook spends nothing: it parses the transcript and writes a JSON file.

## Quick reference

| Task | Command |
|------|---------|
| Create a harness for a cluster | `python harness.py init --workspace <dir> --name <cluster>` |
| Which cluster am I in? | `python harness.py where` |
| Score the harness, get the top gaps | `python harness.py audit` |
| List & validate the deployment registry | `python harness.py deployments` |
| Find drift | `python harness.py doctor` |
| Snapshot every repo's state | `python harness.py scan` |
| Turn session evidence into proposals | `python harness.py garden` |
| Same, unattended (for cron) | `python harness.py garden --headless` |
| Read what was proposed | `python harness.py review` |
| Apply one, onto a branch | `python harness.py apply <id>` |
| Discard one | `python harness.py reject <id>` |
| Start a cross-repo change | `python harness.py plan create --name <slug> --repos a,b,c` |
| Do the branches match the plan? | `python harness.py plan status` |
| Record why you chose something | `python harness.py plan decide --name <slug> --text "..."` |

## The rubric

Twelve dimensions, scored 0-3. Full detail and the per-dimension checks: **`references/rubric.md`**.

| | Dimension | The question it asks |
|---|---|---|
| 1 | Map | Does an arriving agent know where it is? |
| 2 | System of record | Is the knowledge in the repo, or in someone's head? |
| 3 | Bootability | Can it run the thing without re-deriving how? |
| 4 | Feedback loops | Can it *see* the thing run? |
| 5 | Inter-session memory | What survives the context window? |
| 6 | Mechanical enforcement | Which rules does a machine hold? |
| 7 | Work spec | Is "done" something the agent can quietly redefine? |
| 8 | Entropy control | Is drift paid down, or allowed to compound? |
| 9 | Cluster manifest | Is the set of repos itself legible? |
| 10 | Contract registry | What crosses a boundary, and what checks it still holds? |
| 11 | Cross-repo coordination | Is a change spanning repos planned, or improvised? |
| 12 | Deployment topology | Does the agent know where each service runs, or hardcode it? |

The 2-to-3 jump is the one that matters: score 2 is a document asking nicely, score 3 is a machine
saying no. Prose does not hold a line under agent throughput.

`audit` prints the **top gaps with a next action**, not a scorecard. A rubric that prints eleven numbers
per repo becomes a bureaucracy nobody reads.

## The maintain loop in practice

1. Work normally. The hook accumulates one JSON file per session.
2. After a few sessions: `python harness.py garden`.
   - Default (`--prepare`) writes the batch to `state/garden-batch.md` and hands it to **you** (Claude,
     in-session) to apply the taxonomy. Read it, then save proposals with `harness.py propose --file`.
   - `--headless` shells out to `claude -p` instead. That is the mode for cron.
3. `python harness.py review` - each proposal cites the exact commands, errors, or user turns that
   provoked it.
4. `python harness.py apply <id>` - writes onto a branch in the target repo. **Never pushes, never
   merges.** Read the diff and open the PR yourself.

What the loop watches for, and what it proposes in response, is in **`references/signals.md`**. The short
version: two different commands attempting the same boot means `init.sh` is missing; the same tool error
twice means the error does not teach its fix; a user correction means a rule was never written down; a
grep across repo boundaries means an unregistered seam; edits in two repos with no plan means a
distributed transaction is being improvised.

### The test that decides whether this loop is worth keeping

After the first real `garden`, pick a proposal at random and ask: **does it name a specific thing that
actually happened?**

If yes, the loop works. If it says "consider adding more documentation," the loop is producing slop -
raise `min_occurrences` in `harness.yaml`, or switch the hook off. A maintain loop that trains you to
ignore its output is worse than no maintain loop.

## Cross-repo exec-plans

A change spanning repos is a distributed transaction. Improvised, it fails the way one-shotting fails
inside a single repo: partial application, no record of how far it got, and the next session cannot tell.

Use the `create-exec-plan` skill when the user asks for a complete plan. The command below creates only a
skeleton for manual authoring; an empty `steps` list is not a finished plan.

```bash
python harness.py plan create --name move-specs --repos docs,backend,e2e
# edit plans/active/move-specs.yaml: set the merge order and depends_on
python harness.py plan status
```

Two things earn their keep. **Merge order is explicit** - a consumer merging before its owner leaves the
seam broken in `main` for however long the gap lasts. And **`plan status` reads the real git state and
diffs it against the plan**, which catches the most common drift: the plan says one thing, the branches
say another.

Log decisions as you go. Three sessions later the *what* is still in the diff; the *why* is gone unless
you wrote it down.

### Reading a plan without reconstructing it from YAML

`harness.py` in this skill manages the plan lifecycle - `plan create`, `plan decide`, `plan status`. The
faster way to **read** a plan once it exists is `evo harness` (`pip install evo-cli`), which parses the
same `plans/active/*.yaml` files this skill manages:

```bash
evo harness plans             # one-line progress per plan: steps, debt, open questions
evo harness show <slug>       # full plan in the terminal: repos, steps, depends_on, notes
evo harness graph <slug>      # the plan's DAG as an adjacency list (depth, cycles flagged)
evo harness check <slug>      # diff the plan against real git refs and step states
evo harness serve             # localhost:8788 dashboard - cluster, seams, every plan as a DAG
```

Reach for `serve` when merge order is the question and you would rather see it than read YAML, and for
`graph` when you only need the dependency shape. Both render an adjacency table beside the DAG, because
a node-link diagram conveys nothing to a screen reader and does not paste into a document. The
dashboard is read-only by design; mutations (`step`, `repo`, `debt`, `question`) go through `evo harness`
subcommands that leave a shell-history entry, not through the browser.

## Gotchas

- **The signal loop can degrade into plausible busywork.** This is the real risk, not a hypothetical.
  Mitigations are structural: the hook records facts and never interprets; the model only sees batched
  evidence; every proposal must cite what provoked it; nothing touches a repo without review. Apply the
  test above after the first run and act on the answer.
- **`apply` never pushes and never merges.** It writes onto a branch and refuses outright if the target
  repo has uncommitted changes. Auto-opening PRs across N repos is genuinely dangerous and this skill
  will not do it.
- **`init` only sees repos cloned on this machine.** Everything else has to be added by hand with
  `present: false`. `doctor` will flag a doc that points at a repo that is not there - that is the
  finding, and it is a real one.
- **PyYAML is a hard dependency.** `pip install pyyaml`.
- **The registry goes stale when repos move.** `doctor` checks it, but `init --force` is the fix.
- **Do not stack this on `Stop`.** That slot is `continuous-learning`'s and it already costs a `claude
  -p` per session. Use `SessionEnd`.
- **The rubric can turn into a bureaucracy.** It exists to rank gaps, not to be displayed. If you find
  yourself reporting scores instead of fixing the top three, the tool is being misused.
- **Mechanical checks are wrong in the boring direction.** They see that `AGENTS.md` exists, not that it
  is any good. Dimensions 1, 2, 4, and 10 need a human or an agent to actually read the artifact -
  `references/rubric.md` marks which checks are mechanical and which are judgment.

## Boundaries with the other skills

- **`create-exec-plan`** investigates the requested change, asks decision-bearing questions, and writes
  the complete `plans/active/<slug>.yaml` artifact. This skill owns the surrounding harness and plan
  lifecycle tooling, not interactive plan authoring.
- **`continuous-learning`** learns *skills* and *CLI subcommands* from sessions. This learns *harness
  artifacts*. Same transcripts, different output, different hook event. When a signal is really "this
  shell incantation should be a subcommand," that is the other skill's job - leave it alone.
- **`gitnexus`** is the code graph. Use `gitnexus group impact <group> <symbol>` for blast radius across
  the cluster. This skill deliberately does not reimplement that; its job is to know that a seam exists
  and make sure something verifies it.

## Files in this skill

| File | Purpose |
|------|---------|
| `scripts/harness.py` | Everything: init, scan, audit, doctor, digest, garden, propose, review, apply, reject, plan, where |
| `scripts/_transcript.py` | Session JSONL reader (shares its schema handling with `continuous-learning`) |
| `scripts/session-end.ps1` | SessionEnd hook, Windows. Reads stdin, calls `digest`, exits. No model. |
| `scripts/session-end.sh` | Same, POSIX |
| `templates/` | `harness.yaml`, `contracts.yaml`, `deployments.yaml`, `CLUSTER.md`, `AGENTS.md`, `exec-plan.yaml`, `feature_list.json`, `init.sh`/`init.ps1`, `golden-principles.md`, `invariants.md` |

## Additional resources

- **`references/principles.md`** - the two source articles distilled, with what each actually contributes
  and where they disagree. Read before proposing any harness change.
- **`references/rubric.md`** - all 11 dimensions, the 0-3 scale, and which checks are mechanical versus
  judgment.
- **`references/signals.md`** - the signal taxonomy: what a stumbling session looks like and which
  artifact fixes it. This is what `garden` runs on.
- **`references/cluster-patterns.md`** - what counts as a cluster, where the harness root goes, seam
  types, the hub-and-spoke trap, and when the honest answer is "this should be a monorepo."

Sources:
[Anthropic, *Effective harnesses for long-running agents*](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) -
[OpenAI, *Harness engineering*](https://openai.com/index/harness-engineering/)
