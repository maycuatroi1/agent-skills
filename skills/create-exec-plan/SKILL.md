---
name: create-exec-plan
description: This skill should be used when the user asks to "create an execution plan", "write an implementation plan", "plan this change", "create a cross-repo plan", "tạo kế hoạch triển khai", "điều tra rồi lập kế hoạch", or requests a complete YAML plan under plans/active. It investigates project context first, asks only decision-bearing clarification questions, writes one validated plans/active/<slug>.yaml artifact, and stops without implementing the plan.
version: 0.3.0
---

# Create exec plan

Create a durable implementation plan, not a chat outline. Investigate first, separate facts from
decisions, resolve every blocking ambiguity with the user, then write the complete plan to
`plans/active/<slug>.yaml`.

A plan fixes the contract and leaves the route to the agent that executes it. The contract is the goal,
the acceptance criteria and their checks, the invariants, the non-goals, the seam order, and the
checkpoints before anything irreversible. The route is which files change, in what order, through which
intermediate states. The executing agent reads the code when it gets there and chooses the route then;
a route written before anyone touched the code goes stale: on the largest plan written with this
workflow, 24 of 29 steps recorded a deviation from it. Prescribe the route only where a wrong one cannot
be undone.

The plan is the only deliverable. Do not create branches, edit product code, commit, push, or begin
implementation after writing it.

## When to use

- The user asks for an implementation or execution plan.
- Work is substantial enough to benefit from ordered steps and explicit verification.
- A change crosses repositories, packages, services, or registered seams.
- The user explicitly wants a plan under `plans/active/`.

Do not use this skill for a short answer, brainstorming with no requested artifact, personal planning,
or a trivial edit whose implementation is clearer than a plan. A change that one session can finish and
one command can prove needs no plan file: state the goal and the check, and do it. If the user asked for a
plan anyway, say so once and let them choose.

## Non-negotiable rules

1. Investigate before asking questions.
2. Do not ask for facts available in the repository, git history, issue, contract registry, or code graph.
3. Ask all known decision-bearing questions in one grouped round when possible.
4. Do not write the plan while any blocking question remains unanswered.
5. Never overwrite an existing plan without explicit confirmation.
6. Every implementation step must name its repository, the outcome it makes true, dependencies,
   verification, status, and whether it blocks completion. Only a prescribed step (Phase 3) also fixes
   the exact operations.
7. A multi-repo plan must derive merge order from contract ownership. Owners land before consumers.
8. The final YAML must contain no placeholders such as `TBD`, `<repo>`, `later`, or `figure this out`.
9. Stop after writing and validating the plan.

## Resolve the plan root

Resolve a provisional destination before investigating deeply:

1. Use a root explicitly supplied by the user.
2. Otherwise use the nearest ancestor containing `harness.yaml`.
3. For cross-repo work launched inside a participant repo, use the registered harness root when one is
   available through `harness.py where` or `~/.claude/harness/registry.json`.
4. Otherwise use the current git root.
5. If no project root can be established, ask the user where the plan belongs.

The output path is always `<resolved-root>/plans/active/<slug>.yaml`. Create `plans/active/` if the root is
valid but the directory does not exist.

After tracing the change, resolve the destination again. If investigation expands the work from one repo
to multiple repos, switch to the registered harness root, then inspect that root's active and completed
plans before continuing. If multi-repo work has no harness root, ask where the shared plan belongs.

When the root's `harness.yaml` has a `hub:` key with a `project`, it is a hub harness: its plans live on
the evo-agents hub, and the files under `plans/` are read-only copies the hub wrote. The file this skill
writes is then a draft that goes to the hub once validated (Phase 4), and from that moment the file in git
is the hub's copy. Nobody writes it by hand again.

## Phase 1: Investigate

Build enough context that another agent can execute the plan without repeating discovery.

### Read the maps

- Read applicable `AGENTS.md`, `CLAUDE.md`, `README.md`, and project documentation.
- For a harness, read `CLUSTER.md`, `harness.yaml`, `contracts.yaml`, principles, and relevant checks.
- Read active and recently completed plans to learn local schema, conventions, and overlapping work.
- Inspect `git status`, the current branch, recent history, and relevant diffs without changing them.

### Trace the change

- Locate the relevant entry points, symbols, callers, data models, tests, configuration, and generated
  artifacts.
- Use GitNexus for execution flow, impact analysis, and cross-repo relationships when an index is
  available. Use targeted Glob, Grep, and file reads for direct evidence.
- Follow source URLs, issues, pull requests, or external specifications supplied by the user.
- Identify persisted data, public APIs, CLI surfaces, file formats, credentials, deployment boundaries,
  and other compatibility constraints.
- Determine the smallest set of repositories and files that must change. Record checked-but-not-needed
  repositories when omitting them could look accidental.
- Write what the investigation found into `context` and `references`, which every step's executor
  reads. Do not copy it into each step as instructions: in a step it reads as a route to follow, and it
  is only a starting point.

### Establish verification

- Find the real test, lint, typecheck, build, smoke-test, contract, and deployment commands from project
  files instead of inventing commands.
- Run only cheap baseline checks needed to establish current state. Do not assume tests are read-only;
  capture git status before and after commands that may create snapshots, caches, or generated files.
- Record pre-existing failures separately so the plan does not claim responsibility for them.

### Separate facts from unknowns

Before questioning the user, prepare an internal list of:

- Verified facts with file, symbol, command, issue, or URL evidence.
- Decisions already fixed by repository invariants or contract ownership.
- Assumptions that are safe and non-blocking.
- Product or architecture decisions that cannot be inferred.

## Phase 2: Clarify

Ask only questions whose answers change scope, architecture, compatibility, rollout, merge order,
acceptance criteria, or an irreversible operation.

Typical blocking questions include:

- Which observable outcome defines success when the request has multiple plausible meanings?
- Which behavior is intentionally out of scope?
- Is backward compatibility, migration, staged rollout, or data preservation required?
- Which tradeoff should win when multiple approaches remain valid after investigation?
- Should an existing overlapping plan be updated, replaced, or left separate?

Use the available question tool. Give concise options, put the recommended option first, and explain the
tradeoff. Group independent questions into one round. If an answer creates a new blocking ambiguity,
investigate that ambiguity and ask one follow-up round.

Do not ask the user for repository paths, current branches, callers, test commands, or other discoverable
facts. Do not write a draft plan as a substitute for unanswered blocking questions.

## Phase 3: Design the plan

### Slug and collision handling

- Use a short kebab-case slug that names the outcome, not the implementation mechanism.
- Search active and completed plans for the same goal before choosing it. In a hub harness, also run
  `evo-agents hub plan list` from the harness root: the hub may hold plans whose copies this checkout
  has not exported yet.
- If the target file exists, the hub already holds the slug, or an overlapping plan is active, ask whether
  to update it or choose a new scope. Never silently overwrite or fork duplicate work.
- Updating a hub plan, once the user confirms, starts from its current copy (`evo-agents hub plan export .`
  first). Edit that copy as the draft and send it in Phase 4 with
  `evo-agents hub plan put plans/active/<slug>.yaml --if-revision <N>`, where `<N>` is the `revision`
  under the copy's `hub:` key.

### Repository and merge order

For single-repo work, include one repo with `order: 1` and no dependencies.

For multi-repo work:

- Derive participants from traced impact and `contracts.yaml`, not only from the user's initial list.
- Put each seam owner before its consumers.
- Express the same order in both `order` and `depends_on`.
- If two touched seams impose opposite ownership directions, use compatible phases in one plan when safe.
  If separate plans are required, ask which scope this artifact should cover and record the other plan as
  an explicit follow-up. This workflow still writes exactly one file.
- Use the existing feature branch if work is already in progress. Otherwise use the repository's
  established branch convention, falling back to `feat/<slug>` when no convention exists.
- Keep the repo status `pending` while its planned branch has not been created or checked out. Lifecycle
  checks treat that mismatch as planned work; change the status to `in_progress` when execution starts.

### Acceptance criteria and invariants

Give every acceptance criterion an `id` (`a1`, `a2`, ...), so steps can name the criteria they make true.
Mark a criterion `invariant: true` when it must hold after every step and not only at the end, such as
"the OpenAPI document does not change" or "the full suite stays green". Every acceptance criterion needs a
`verify` an agent can run, or a precise manual check when no command can prove it.

### Two kinds of step

**Outcome steps are the default.** An outcome step says what becomes true and leaves the files, the order
and the intermediate commits to the executor, who records each choice it makes as a `Decision:` line in
the step's evidence. A step is an outcome step exactly when it has an `acceptance` list. Each item is the
id of a plan criterion the step satisfies (`a1`), or, for an intermediate outcome no plan criterion
covers, one sentence stating it ("hub code gets its connections from the engine; driver() still works").
The step's `verify` proves every item.

**Prescribed steps** fix the exact operations. Write one only where a wrong route cannot be undone, or the
user asked for that detail:

- a migration, backfill or bulk change on real data;
- a deploy, release or publish;
- creating, rotating or revoking credentials, or changing a production service;
- a seam change whose owner and consumers must move in lockstep;
- deleting data or history that is not the plan's own scratch.

A prescribed step has no `acceptance` key. Its `what` names the operations in order, and its `verify` and
the plan's `rollback` say how to check and reverse them.

### Where to cut steps

Cut a step where something has to happen between two pieces of work, not to keep each step small:

- an outcome that can be verified on its own is one step, however many files it touches; a mechanical
  change across a whole package with one machine check is one step, not one step per directory;
- a seam owner's change is a step its consumers' steps depend on;
- a checkpoint (a prescribed step, a full-suite comparison, a review the user wants) gets its own step;
- work that can run in parallel, in another repo or on files no other step touches, gets its own step.

A repository usually needs a handful of outcome steps. If a plan reaches the old shape of one step per
module, merge steps that share a verify and have no checkpoint between them.

### Step construction

Every step:

- Carries a `title` of at most 60 characters, written in the same prose language as the rest of the plan
  and with full diacritics when that language uses them. The title names the resulting outcome, not the
  mechanism, and must be distinguishable from every other step in the same repository. `title` is only the
  label shown in a step list or dependency graph; `what` remains the full description and is never
  shortened to compensate.
- Depends only on earlier step IDs.
- Has a `verify` of runnable commands, written to run from the repo root (a worker runs it again in its
  own worktree), or a precise manual procedure when nothing can be run.
- States why it is blocking or non-blocking when that is not obvious.

An outcome step's `what`:

- states the outcome as behavior, and restates in words each plan criterion its `acceptance` names by
  id: a worker's single-step run sees the step's `what`, `verify` and `note`, not the plan's
  `acceptance`;
- names the constraints that bind this step, including the contracts it must keep (schemas, APIs, CLI
  surfaces, file formats) and the invariants it could break;
- may point at starting points the investigation found, phrased as starting points ("the queries live
  mostly in ..."), never as a file-by-file sequence;
- includes the contract, documentation, generated-artifact and cleanup work the outcome implies.

Its `verify` runs the checks of every item of its `acceptance`, plus the checks of the invariants it
could break.

A prescribed step's `what` names exact files, symbols, commands and order, as far as the investigation
established them.

Put owner-side contract changes before consumer changes. Put compatibility bridges before migrations,
migrations before removals, and irreversible operations behind an explicit checkpoint and rollback.

## Canonical YAML

Use English field names so `evo harness` can parse and mutate the plan. Write prose in the project's
documentation language; if no convention exists, follow the user's language. Leave out the `hub:` key and
the comment line above `id:` that hub copies carry; the hub writes both.

```yaml
id: outcome-slug
goal: >
  One observable sentence describing what becomes true after the plan lands.
created_at: '2026-07-20T12:00:00+07:00'

context: >
  Current behavior, root cause, constraints, and why the change is needed.

acceptance:
  - id: a1
    criterion: Observable completion condition.
    verify: Exact command or manual check that proves it.
  - id: a2
    criterion: Condition that must hold after every step, such as an unchanged public contract.
    verify: Exact command that proves it.
    invariant: true

non_goals:
  - Explicitly excluded behavior or follow-up.

references:
  - what: Evidence or design input used by this plan.
    where: File path, symbol, command output, issue, pull request, or URL.

repos:
  - repo: repository-name
    branch: feat/outcome-slug
    order: 1
    depends_on: []
    status: pending
    scope: What changes in this repository.

steps:
  - id: 1
    repo: repository-name
    title: Short outcome label, at most 60 characters.
    what: >
      The behavior that becomes true, each criterion it satisfies restated in words, the contracts and
      invariants it must keep, and starting points the investigation found. No file-by-file route.
    acceptance: [a1]
    depends_on: []
    verify: Commands of a1 and of the invariants this step could break, runnable from the repo root.
    status: pending
    blocking: true
    note: Why this ordering or verification matters.
  - id: 2
    repo: repository-name
    title: Short outcome label of an irreversible operation.
    what: >
      Exact operations in order, with files, commands and the checkpoint before the irreversible one.
    depends_on: [1]
    verify: Exact runnable command or precise manual procedure.
    status: pending
    blocking: true
    note: Why this step is prescribed rather than an outcome.

seams_touched:
  - name: contract-name
    owner: owner-repository
    consumers: [consumer-repository]
    verify: Exact contract check.

risks:
  - risk: Specific failure mode.
    mitigation: Prevention, detection, and containment.

rollback: >
  Exact safe reversal order, compatibility window, and any operation that cannot be rolled back.

assumptions:
  - Non-blocking assumption supported by current evidence.

decisions:
  - date: '2026-07-20'
    what: Decision made during clarification.
    why: Evidence and tradeoff behind the decision.

tech_debt: []
open_questions: []
```

Omit a section only when it truly does not apply. Keep `repos`, `steps`, `acceptance`, `references`,
`decisions`, and `open_questions` present. `open_questions` may contain only non-blocking or deliberately
deferred questions because all blocking questions must be resolved before writing.

Use these statuses for compatibility with `evo harness`:

- Repo: `pending`, `in_progress`, `done`, `merged`, `not-needed`.
- Step: `pending`, `in_progress`, `blocked`, `done`.
- Tech debt: `open`, `fixed`.
- Open question: `open`, `answered`.

When `tech_debt` or `open_questions` is non-empty, use mappings that lifecycle commands can mutate:

```yaml
tech_debt:
  - issue: Known compromise intentionally left by this plan.
    severity: low
    status: open
    note: Why it is safe to defer and what closes it.
open_questions:
  - issue: Non-blocking question that can remain after implementation starts.
    status: open
    blocking: false
    note: Owner, decision point, or evidence needed to answer it.
```

## Phase 4: Write and validate

Before writing, verify that:

- The goal and every acceptance criterion are observable.
- Scope and non-goals prevent the main likely misunderstandings.
- Every affected repo is included or explicitly checked as not needed.
- Merge order follows every touched seam.
- Every step has a non-empty `title` of at most 60 characters.
- Every blocking step has verification.
- Every acceptance criterion has an `id` and is proven by the `verify` of at least one step.
- Every id in an outcome step's `acceptance` names an existing criterion, and its `what` restates those
  criteria in words.
- No outcome step lays out a file-by-file route, and every prescribed step is one of the cases Phase 3
  lists or one the user asked for.
- Rollback is honest about irreversible actions.
- No blocking question, placeholder, invented command, or unsupported factual claim remains.

Write exactly one file at `plans/active/<slug>.yaml`. Do not modify product code or create a second chat
version of the plan.

After writing:

1. Parse the file with PyYAML or the project's YAML parser.
2. Re-read it and check required fields, unique step IDs, dependency references, acyclic dependencies,
   contiguous repo order, allowed statuses, acceptance ids that steps reference, and absence of
   placeholders.
3. When the resolved root contains `harness.yaml` and `evo harness` is available, run
   `evo harness show <slug>`, `evo harness graph <slug>`, and `evo harness graph <slug>:steps` from that
   root. Do not run `evo harness check <slug>` until every planned branch or ref it checks exists; branch
   absence before implementation is expected, not a failed plan validation.
4. In a hub harness, send the validated draft to the hub from the harness root:
   `evo-agents hub plan put plans/active/<slug>.yaml` (add `--if-revision <N>` only when updating an
   existing plan as above). The hub stores it and rewrites the file as its copy, with a header line and a
   `hub:` key holding the project, revision and digest. Report any warnings it prints. Without
   `--if-revision` it never replaces a plan the hub already holds; if it refuses because the slug exists,
   go back to collision handling instead of adding the flag. When `evo-agents` is missing, not signed in,
   or the hub does not answer, leave the draft where it is, report the error, and say the plan is not on
   the hub yet.
5. Run the harness plan or contract validation command when the project provides one.
6. Compare final git status with the captured baseline to confirm this workflow changed only the plan
   artifact and any explicitly requested planning metadata. In a hub harness that artifact is the copy
   `put` wrote; leave committing it to the user, for whom `evo-agents hub plan export . --commit` commits
   exactly the copies that changed.

Report the final path, a one-sentence scope summary, and validation results. In a hub harness, also report
the hub project and revision, or that the push failed. Mention pre-existing failures or deliberately
deferred non-blocking questions. Stop there.

## Relationship to harness-engineering

`harness-engineering` owns cluster setup, contracts, audits, drift detection, and plan lifecycle commands.
This skill owns interactive plan authoring. `harness.py plan create` produces only a skeleton; do not treat
that skeleton as the completed artifact required by this workflow.
