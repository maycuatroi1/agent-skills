# Findings and proposals

A finding says what happened, with evidence; a proposal is one change argued from findings and evidence, with a draft
plan. Both go to the hub from the session with `evo-agents hub curator finding|propose`, into the session's local run,
next to the night's review runs. The hub checks them, keeps them, and every answer adds a line to the proposal's
ledger (`evo-agents hub curator proposal show ID`).

## Evidence

| Spec | Points at |
|---|---|
| `session:ID[:FIELD:INDEX]` | a session of the project, and an entry of a list of its facet or digest (`errors`, `corrections`, `commands`...) |
| `transcript:ID[:FILE]:LINE` | a line of a session's transcript the hub holds, of its own file unless FILE names a subagent's |
| `run:ID:SEQ` | an event of a run of the project |
| `code:REPO:PATH[:LINE]` | a line of a file of a repo of the project (checked against this machine's checkout when there is one) |
| `memory:ID:REV` | a memory of the project at a revision |

The figures' entries carry their evidence ready to cite. The hub resolves every piece before it stores anything and
refuses with the first it cannot find. At most 50 pieces per finding or proposal.

## A finding

```bash
evo-agents hub curator finding --lens LENS --severity low|medium|high --title "one line" \
  --evidence SPEC [--evidence SPEC...] [--body-file finding.md]
```

The body is markdown, at most 16 KiB. A finding like a closed one of an earlier night, citing evidence that one
cited already, is refused: read `evo-agents hub curator earlier` first.

## A proposal

```bash
evo-agents hub curator propose --lens LENS --kind KIND --title "the change, in one line" \
  --path REPO:PATH --finding ID --evidence SPEC \
  --summary-file summary.md --plan-file draft.yaml [--probe-file probe.yaml]
```

- `--path` (repeat it): each file it would edit, in a repo of the project. The paths and what the knowledge graph says they reach
  set the tier.
- `--finding` and `--evidence`: what it rests on, at least one.
- `--summary-file`: the problem, the change, the expected effect and what waiting costs, and how to undo it.
- `--plan-file`: the draft plan, YAML or JSON, in outcome steps, as the night shift will build it:

```yaml
id: curator-fix-sleep
title: Stop the harness from blocking sleep and tail
goal: Agents wait on background work without a blocked command.
steps:
  - id: 1
    title: Wait helper
    repo: evo-agents
    what: A helper that waits on a file without sleep and tail.
    verify: python -m pytest -q tests/test_wait.py
    acceptance:
      - no session of the next week has a blocked sleep followed by tail
```

  Each step has `what`, a `verify` that is one shell command line, and a non-empty `acceptance` list. Kind `memory`
  may give `--promote-file` (target and body of a shared memory) in place of a plan.
- `--probe-file`, required when the evidence cites a correction of the figures and a path is an AGENTS.md, a
  CLAUDE.md, a skill or `.claude` settings or hooks: `repo`, `commit` (when the base is not the default branch),
  `task` (what an agent is asked to do) and `verify` (one line that exits 0 when the agent does not repeat the
  mistake). Run the task yourself on the harness as it is: when the mistake no longer happens, there is nothing to
  guard.

## A change in several repos

A proposal whose paths name files in several repos of the project becomes one plan in them all, on one branch name
(`curator/<proposal>-<slug>`): the hub opens a pull request in each repo, judges each on its own, and merges a
consumer's pull request only after its owner's merged. Write the draft so that order holds:

- Give `--path` once for each file in each repo; the repos of the plan are the repos of the paths.
- Put `repo` on every step; a step in a repo no path names is refused.
- Order the steps owner before consumer, as the seams of the harness's `contracts.yaml` run (`owner` first, then each
  of its `consumers`). Read the seam the change crosses before writing: when it changes a CLI, an API or a schema
  that another repo calls, the owner's steps come first and the consumer's steps adapt to what the owner's step
  shipped. The hub orders the repos by the seams of the project's graph; without a seam between two repos it keeps
  the order of the draft, so the draft's order is the order of the merges.
- Give each repo's steps a `verify` that runs in that repo, and name the seam's own `verify` in the consumer's last
  step when the seam has one.

```yaml
id: curator-hub-cli-flag
title: Rename the --wait flag of hub run logs and its callers
goal: One flag name across the CLI and the skills that call it.
steps:
  - id: 1
    repo: evo-agents            # owner of seam hub-cli-v1
    what: The CLI takes --follow; --wait stays as an alias for a release.
    verify: uv run pytest -q tests/hub/test_contract.py
    acceptance:
      - the contract golden lists --follow
  - id: 2
    repo: agent-skills          # a consumer of hub-cli-v1
    what: The skills call --follow.
    verify: evo-agents hub contract check skills/execute-plan/SKILL.md
    acceptance:
      - no skill names --wait
```

## Kinds and tiers

The kind sets the first tier: `docs`, `memory`, `test_add`, `kg_source`, `fix`, `refactor`, `lint`, `skill`, `cli`,
`release_prep`, `revert`, `feature`, `api_change`, `schema_change`, `global_config`, `dependency_major`, `operation`,
and the kinds always at tier 3: `test_loosen`, `verify_change`, `ci_change`, `credentials`, `curator_rules`.

The hub computes the tier, never the agent: from the kind, the paths (a protected glob of the charter or CI, lint and
test configuration: tier 3; a migration or schema: at least 2; any code: at least 1), and what the knowledge graph says
the paths reach. The answer says the tier and why.

What the paths reach (`kg_impact`) raises the tier by the API a protected file uses, not by the import alone:

- Before the pull request, a protected file (or one of `HARD_PATHS`) that a path reaches counts at most tier 2, so the
  Builder can still build the branch whose diff decides.
- Once the pull request is open, the hub reads what the diff does to the top-level names and signatures of each
  Python file it edits. A reached protected file raises the change to tier 3 only when the diff removes or changes a
  name that file imports or calls; one the diff breaks nothing of keeps the tier the other rules give.
- Editing a protected file directly is still tier 3, except a harness file the charter's `evolve.evolvable_paths`
  names: a change that edits a harness alone, whose Judge passed and whose holdout replays won, merges at tier 0.

So run `kg_impact` on the paths before proposing, and keep a public name's signature when the change does not need to
break it: an added parameter with a default reaches nothing protected, a renamed one does.

| Tier | After accepting |
|---|---|
| 0 | the night shift builds it, the Judge checks it, the hub merges it when the charter's `auto_merge` lets it |
| 1 | built and judged the same; its pull request waits for the owner to merge |
| 2 | as 1; a night's tier 2 proposal also reaches the owner's Inbox |
| 3 | the night shift builds nothing; it is built by hand, in a session, through a pull request |

The charter's `planned_tiers` may plan other tiers, 3 included.

## Repeats and caps

A proposal with the kind and paths (or the kind and title) of one rejected in the last 30 days is stored `dropped`,
unless its evidence is at least twice the rejected one's. A run, the session's local run included, records at most 200
findings and 50 proposals. A fix proposal (`--fix-of`) is the night's alone.

## Evolving the change

A proposal of a harness file (kind `docs`, `skill` or `global_config` on a path `evolve.evolvable_paths` names) can be
evolved once accepted, instead of built as one edit: `evo-agents hub curator evolve run --repo REPO --path PATH
--proposal ID` (`SKILL.md`, "Evolving a harness"). The best candidate takes the branch of that proposal's change. Say in
the summary when an evolution is the better route: the file is long, the tasks that measure it exist, and one edit
would not settle it.

## Answers

`evo-agents hub curator proposal accept|reject|defer ID [--note TEXT] [--days N]`, an admin of the project only, while
it is open or deferred. A deferred one opens again after its days. With the charter's `answer_by: agent`, each
proposal recorded open gets a thread in the project's triage chat, where the project's agent answers it.
