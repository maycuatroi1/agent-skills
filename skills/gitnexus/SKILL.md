---
name: gitnexus
description: This skill should be used when the user wants to "index a repo", "index this workspace", "set up gitnexus", "code intelligence", "knowledge graph of the code", "impact analysis", "what breaks if I change X", "trace this execution flow", "query the codebase graph", "cross-repo / multi-repo context", or mentions GitNexus. GitNexus is a global, always-available code-intelligence tool (CLI + MCP) usable in ANY git repo or multi-repo workspace. Covers idempotent global install + MCP setup (scripts/install.sh), indexing one repo or every repo in a workspace and grouping them for cross-service queries (scripts/index-workspace.sh), the MCP tool workflow (query/context/impact/detect_changes/rename), the Web UI (gitnexus serve), and the real-world gotchas (embeddings are opt-in, FTS off without an extension, Dart/Kotlin/Swift grammars need a C++ toolchain, npx cold-start MCP timeout).
version: 0.1.0
---

# gitnexus

GitNexus builds a knowledge graph of a codebase (Tree-sitter AST + import/call/type resolution + Leiden community detection + execution-flow tracing) and exposes it to AI agents over MCP. Treat it as an always-available tool/skill for any workspace, not one project.

## When to use

- Understand architecture, trace execution flows, or explore unfamiliar code (better than grep).
- Impact / blast-radius analysis BEFORE editing a symbol; verify affected scope BEFORE committing.
- Call-graph-aware rename / refactor.
- Cross-repo questions across a multi-service workspace.
- Set up or refresh the index on a new machine or repo.

Skip it for trivial edits where the graph adds nothing.

## Install + MCP setup (once per machine)

```bash
bash scripts/install.sh
```

Idempotent: global-installs `gitnexus` (skipping the optional Dart/Kotlin/Swift/Proto grammars so no C++ toolchain is needed), runs `gitnexus setup` to wire MCP + skills + hooks into detected editors (Claude Code, Cursor, Codex, Antigravity, OpenCode), and smoke-tests. Re-run any time to repair config.

Global install is recommended over `npx gitnexus mcp`: a cold `npx` install can exceed Claude Code's `MCP_TIMEOUT` (~30s).

## Index a repo

```bash
gitnexus analyze                 # index the current repo (graph only)
gitnexus analyze --embeddings    # ALSO build semantic embeddings (see gotcha)
gitnexus analyze -f              # force full re-index
gitnexus list                    # show all indexed repos + paths + stats
```

Each `analyze` writes the index to `.gitnexus/` inside the repo (portable, gitignored) and registers a pointer in `~/.gitnexus/registry.json`. It also augments the repo's `CLAUDE.md`/`AGENTS.md` with a GitNexus section (suppress with `--skip-agents-md`).

## Index a whole multi-repo workspace

```bash
bash scripts/index-workspace.sh [ROOT_DIR] [GROUP_NAME] [--embeddings]
```

Analyzes every direct subdirectory of `ROOT_DIR` (default: cwd) that is a git repo. If `GROUP_NAME` is given, it creates the group and adds every repo it indexed under that root, then syncs the contract registry for cross-repo queries.

Group commands (run manually if you want a custom hierarchy; `registryName` comes from `gitnexus list`, which may differ from the dir name):

```bash
gitnexus group create <group>
gitnexus group add <group> <hierarchy/path> <registryName>   # e.g. backend/auth my-auth-svc
gitnexus group sync <group>
gitnexus group query <group> "<question>"     # execution flows across all repos
gitnexus group impact <group> <symbol>        # cross-repo blast radius
gitnexus group status <group>                 # staleness check
```

## MCP workflow (inside the editor)

- `query({query: "concept"})` - find execution flows, process-grouped, ranked. Use instead of grep.
- `context({name: "symbolName"})` - full context: callers, callees, flows it participates in.
- `impact({target: "symbolName", direction: "upstream"})` - blast radius before editing. Warn the user on HIGH/CRITICAL.
- `detect_changes()` - affected scope before committing; `detect_changes({scope:"compare", base_ref:"develop"})` for regression review vs a branch.
- `rename(...)` - call-graph-aware rename; never find-and-replace across files.

The bundled per-task skill files live under `.claude/skills/gitnexus/` after `gitnexus setup` (gitnexus-exploring, -debugging, -impact-analysis, -refactoring, -pr-review, -cli, -guide).

## Web UI

```bash
gitnexus serve                   # HTTP backend on http://localhost:4747 (--host 0.0.0.0 for remote)
```

Then open https://gitnexus.vercel.app - it auto-connects to the local backend and gives a graph explorer + AI chat over all indexed repos. `serve` also mounts MCP HTTP endpoints at `/api/mcp`.

## Gotchas

- Embeddings are OPT-IN. A plain `gitnexus analyze` builds the graph but NO semantic embeddings - semantic/hybrid search stays empty until you run `gitnexus analyze --embeddings` (50,000-node safety cap by default; `--embeddings 0` removes the cap). Graph/flow/impact tools work without embeddings.
- FTS keyword search needs a native extension that is often missing ("FTS extension unavailable; continuing without FTS"). Graph + semantic still work; `--repair-fts` tries to rebuild.
- Dart / Kotlin / Swift / Proto grammars are skipped by `scripts/install.sh` (env `GITNEXUS_SKIP_OPTIONAL_GRAMMARS=1`). Those languages will NOT be parsed (e.g. a Flutter app indexes almost nothing). To parse them, install with `python3` + `make` + `g++` present and WITHOUT that env var.
- npm 11 can crash `npx gitnexus` (#1939). Fix: `npm i -g gitnexus` and call `gitnexus` directly.
- The MCP server reads the LOCAL registry; indexes are per-machine and not shared automatically across devices.
