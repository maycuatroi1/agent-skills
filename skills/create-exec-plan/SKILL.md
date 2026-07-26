---
name: create-exec-plan
description: This skill should be used when the user asks to "create an execution plan", "write an implementation plan", "plan this change", "create a cross-repo plan", "tạo kế hoạch triển khai", "điều tra rồi lập kế hoạch", or requests a complete YAML plan under plans/active. It investigates project context first, asks only decision-bearing clarification questions, writes one validated plans/active/<slug>.yaml artifact, and stops without implementing the plan.
version: 0.1.0
---

# Create exec plan

Create a durable implementation plan, not a chat outline. Investigate first, separate facts from
decisions, resolve every blocking ambiguity with the user, then write the complete plan to
`plans/active/<slug>.yaml`.

The plan is the only deliverable. Do not create branches, edit product code, commit, push, or begin
implementation after writing it.

## When to use

- The user asks for an implementation or execution plan.
- Work is substantial enough to benefit from ordered steps and explicit verification.
- A change crosses repositories, packages, services, or registered seams.
- The user explicitly wants a plan under `plans/active/`.

Do not use this skill for a short answer, brainstorming with no requested artifact, personal planning,
or a trivial edit whose implementation is clearer than a plan.

## Non-negotiable rules

1. Investigate before asking questions.
2. Do not ask for facts available in the repository, git history, issue, contract registry, or code graph.
3. Ask all known decision-bearing questions in one grouped round when possible.
4. Do not write the plan while any blocking question remains unanswered.
5. Never overwrite an existing plan without explicit confirmation.
6. Every implementation step must name its repository, concrete change, dependencies, verification,
   status, and whether it blocks completion.
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
- Search active and completed plans for the same goal before choosing it.
- If the target file exists or an overlapping plan is active, ask whether to update it or choose a new
  scope. Never silently overwrite or fork duplicate work.

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

### Step construction

Each step is one reviewable state transition. It must:

- Carry a `title` of at most 60 characters, written in the same prose language as the rest of the plan
  and with full diacritics when that language uses them. The title names the resulting outcome, not the
  mechanism, and must be distinguishable from every other step in the same repository. `title` is only the
  label shown in a step list or dependency graph; `what` remains the full description and is never
  shortened to compensate.
- Name exact files, modules, symbols, schemas, or commands when investigation identified them.
- Explain the behavioral result, not just "update code" or "add tests".
- Depend only on earlier step IDs.
- Include a runnable verification command or a precise manual verification procedure.
- State why it is blocking or non-blocking when that is not obvious.
- Include contract, documentation, migration, generated artifact, and cleanup work where applicable.

Put owner-side contract changes before consumer changes. Put compatibility bridges before migrations,
migrations before removals, and irreversible operations behind an explicit checkpoint and rollback.

## Canonical YAML

Use English field names so `evo harness` can parse and mutate the plan. Write prose in the project's
documentation language; if no convention exists, follow the user's language.

```yaml
id: outcome-slug
goal: >
  One observable sentence describing what becomes true after the plan lands.
created_at: '2026-07-20T12:00:00+07:00'

context: >
  Current behavior, root cause, constraints, and why the change is needed.

acceptance:
  - criterion: Observable completion condition.
    verify: Exact command or manual check that proves it.

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
      Concrete implementation state transition with files or symbols.
    depends_on: []
    verify: Exact runnable command or precise manual procedure.
    status: pending
    blocking: true
    note: Why this ordering or verification matters.

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
- Rollback is honest about irreversible actions.
- No blocking question, placeholder, invented command, or unsupported factual claim remains.

Write exactly one file at `plans/active/<slug>.yaml`. Do not modify product code or create a second chat
version of the plan.

After writing:

1. Parse the file with PyYAML or the project's YAML parser.
2. Re-read it and check required fields, unique step IDs, dependency references, acyclic dependencies,
   contiguous repo order, allowed statuses, and absence of placeholders.
3. When the resolved root contains `harness.yaml` and `evo harness` is available, run
   `evo harness show <slug>`, `evo harness graph <slug>`, and `evo harness graph <slug>:steps` from that
   root. Do not run `evo harness check <slug>` until every planned branch or ref it checks exists; branch
   absence before implementation is expected, not a failed plan validation.
4. Run the harness plan or contract validation command when the project provides one.
5. Compare final git status with the captured baseline to confirm this workflow changed only the plan
   artifact and any explicitly requested planning metadata.

Report the final path, a one-sentence scope summary, and validation results. Mention pre-existing failures
or deliberately deferred non-blocking questions. Stop there.

## Relationship to harness-engineering

`harness-engineering` owns cluster setup, contracts, audits, drift detection, and plan lifecycle commands.
This skill owns interactive plan authoring. `harness.py plan create` produces only a skeleton; do not treat
that skeleton as the completed artifact required by this workflow.
