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

## Kinds and tiers

The kind sets the first tier: `docs`, `memory`, `test_add`, `kg_source`, `fix`, `refactor`, `lint`, `skill`, `cli`,
`release_prep`, `revert`, `feature`, `api_change`, `schema_change`, `global_config`, `dependency_major`, `operation`,
and the kinds always at tier 3: `test_loosen`, `verify_change`, `ci_change`, `credentials`, `curator_rules`.

The hub computes the tier, never the agent: from the kind, the paths (a protected glob of the charter or CI, lint and
test configuration: tier 3; a migration or schema: at least 2; any code: at least 1), and what the knowledge graph says
the paths reach. The answer says the tier and why.

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

## Answers

`evo-agents hub curator proposal accept|reject|defer ID [--note TEXT] [--days N]`, an admin of the project only, while
it is open or deferred. A deferred one opens again after its days. With the charter's `answer_by: agent`, each
proposal recorded open gets a thread in the project's triage chat, where the project's agent answers it.
