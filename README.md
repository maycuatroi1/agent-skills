# Agent Skills

Agent skills for AI coding agents, following the [Agent Skills](https://agentskills.io) open standard.

## Installation

The skills reach the team's machines through the
[evo-agents hub](https://github.com/maycuatroi1/evo-agents/blob/main/docs/hub.md). A hub admin publishes
every skill directory from a clean checkout of `main`; a skill whose files did not change keeps its
version.

```bash
for name in $(ls skills); do
  evo-agents hub skills publish skills/$name --scope global \
    --source-repo agent-skills --source-commit $(git rev-parse HEAD)
done
```

Each machine, signed in with `evo-agents hub login`, then writes the latest versions into every agent
runtime it has (`claude`, `agents`, `codex`, `cursor`, `gemini`):

```bash
evo-agents hub skills sync --check   # say what would change, write nothing
evo-agents hub skills sync           # install or update every skill the hub lists
evo-agents hub skills sync --adopt   # also take over copies the hub did not write, after a backup
```

Sync changes only directories it wrote itself, and saves a copy under `~/.evo/hub/backups/` before
replacing anything. A copy made by `install.py` or skillfish stays as it is until `--adopt` takes it over.
`evo-agents hub skills list --scope global` shows what is published, and from which commit.

Without the hub, install straight from GitHub:

```bash
npx skillfish add maycuatroi1/agent-skills
```

## Fallback: install.py

`install.py` copies `skills/` into the runtimes of a machine that does not sync from the hub. Do not run
it on one that does: it deletes every file the source lacks, including the `.evo-hub.json` marker that
sync keeps in each skill it wrote, and sync then treats those directories as copies made by hand.

`setup.py` only writes `~/.claude/CLAUDE.md`; it never copied a single skill. Without hub sync or
`install.py` the checked-in skills and the ones the agents actually load drift apart in silence - on
2026-07-30 the runtime copy of `harness-engineering` was 5 days behind source and produced 13 findings
that had already been fixed.

```bash
python install.py --check   # compare only, exit 1 and name every file that differs
python install.py           # copy skills/ into ~/.claude/skills/ and ~/.opencode/skills/
```

- Idempotent. `--check` after an install prints `in sync` and exits 0.
- Skips `__pycache__`, `.skillfish.json`, `.claude/` and `*.pyc` - runtime-generated, target-side only.
- Compares text files with line endings normalized, so a CRLF checkout on Windows is not reported as drift.
- Backs the target skill up to `<root>/.backup-<timestamp>/` before overwriting anything.
- A runtime whose parent directory is absent (no `~/.opencode`) is skipped out loud, not created.
- `--target claude|opencode`, `--skill NAME` (repeatable) and `--dest PATH` narrow what is touched.

## Setup global style rules

Append style rules (no em-dash / en-dash / smart quotes) to `~/.claude/CLAUDE.md` so every Claude Code session on this machine follows them. Idempotent, safe to re-run on every new device:

```bash
python3 setup.py
```

## Available Skills

| Skill | Description |
|-------|-------------|
| `generate-image` | Generate images using Google Gemini API via omelet CLI |
| `continuous-learning` | Auto-extract reusable patterns at session end (Stop hook) and save them as learned skills into the current project's `.claude/skills/learned/` |
| `credentials-utils` | Read/list/refresh/sync credentials in the omelet store, all via `evo cred` ([evo-cli](https://github.com/maycuatroi/evo-cli) owns the implementation). Get values by nested key path, list with masked output, refresh Google OAuth tokens, sync across machines via GitHub private repo + `gh` CLI. This skill is a mirror of the `evo cred` surface and ships no scripts |
| `create-slide` | Generate `.pptx` decks from a TypeScript content file via the open-source [`omelet-slide-generator`](https://github.com/maycuatroi1/omelet-slide-generator) (28 layouts, 3 themes, native OMML math, Shiki code highlighting) |
| `dokploy-cli` | Manage Dokploy services (apps, compose, postgres/mysql/mongo/redis, domains, env vars, deploys) via the official [`@dokploy/cli`](https://github.com/Dokploy/cli). 449 commands across 32 groups. One-shot setup: `bash skills/dokploy-cli/scripts/install.sh` (npm install + ~/.omelet.json check + shell rc + smoke test, idempotent) |
| `life-cli` | Personal life management via the [`red-life`](https://github.com/maycuatroi1/red-life) `life` CLI (todo, calendar, plan, journal, people, places, notes, health, fb, mail; Firestore-backed). Compact skill: discovers commands at runtime via `life --help` |
| `add-tasks` | Add todos via the `life` CLI with auto-managed context: fetches the referenced source (Google Sheets CSV export, Docs, GitHub, web), extracts the relevant rows, attaches the link + a self-contained summary to the todo |
| `gitnexus` | Code-intelligence tool (CLI + MCP) for any git repo or multi-repo workspace via [`gitnexus`](https://github.com/abhigyanpatwari/GitNexus). Builds a knowledge graph for impact analysis, flow tracing, call-graph-aware rename, and cross-repo queries. One-shot setup: `bash skills/gitnexus/scripts/install.sh` (global install + MCP setup, idempotent); index a whole workspace: `bash skills/gitnexus/scripts/index-workspace.sh <root> <group>` |
| `harness-engineering` | Analyze, build and maintain an agent harness for a **cluster** of tightly-related repos. Scores the cluster against an 11-dimension rubric (`audit`), finds drift (`doctor`), coordinates changes spanning N repos with an explicit merge order (`plan`), and - the point - watches real sessions and turns each agent stumble into a proposal for the artifact that would have prevented it (`garden`). Built on [Anthropic's harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) and [OpenAI's harness engineering](https://openai.com/index/harness-engineering/) |
| `create-exec-plan` | Investigate project context, ask only decision-bearing clarification questions, and write one complete, validated `plans/active/<slug>.yaml` execution plan. The plan fixes the contract (acceptance criteria, invariants, seam order, checkpoints) and leaves the route to the executor through outcome steps; only irreversible work gets prescribed steps. Supports single-repo and cross-repo work and stops before implementation. In an evo-agents worker author run (`EVO_RUN_KIND=author`) it asks the member in the run's chat and puts the plan with `evo-agents worker put` |
| `speak` | Text to speech via [`evo tts`](https://github.com/maycuatroi/evo-cli): Vbee for Vietnamese (realtime `mode: sync`, bulk `mode: async` + polling), OpenAI `gpt-4o-mini-tts` for everything else. Ships the `evo-tts` MCP server (`mcp/tts/server.py`) whose `speak` tool lets an agent hand over a spoken summary through your speakers. One-shot setup: `bash mcp/tts/install.sh` |
| `manim-explainer-video` | Build animated technical explainer videos with [Manim Community](https://www.manim.community/): light theme, Vietnamese narration, real computed numbers, plus a timecoded dubbing script and frame-accurate SRT subtitles. Ships a working scaffold (`scripts/new-video.sh <dir>`) and the macOS workarounds Manim needs to render LaTeX + Vietnamese at all |
| `stop-slop` | Strip AI tells out of English prose. Banned-phrase list (throat-clearing openers, emphasis crutches, business jargon, all adverbs, vague declaratives), structural clichés (binary contrasts, negative listing, dramatic fragmentation, false agency, passive voice), before/after rewrites, and a 5-dimension score with a ship/revise threshold. Ported from [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (MIT); no dependencies |
| `update-evo-agents` | Bring evo-agents up to the latest release on this machine and in a harness's CI: checks the CLI, the `evo-hub` and `evo-kg` plugins, the worker daemon and the `evo-ak==` pins, then an `evo-agents-updater` subagent upgrades what is behind, restarts an idle daemon and opens a pull request per pin. `scripts/check.py --notice` in a SessionStart hook says when something is behind |

## Requirements

- [omelet CLI](https://github.com/maycuatroi1/omelet-cli) (`pip install git+https://github.com/maycuatroi1/omelet-cli`) — for `generate-image`
- Google API key for Gemini — for `generate-image`
- `claude` CLI + `jq` + `python3` — for `continuous-learning`
- `evo` >= 0.12.2 (`pip install evo-cli`, or `python setup.py` here) + `gh` CLI - for `credentials-utils`
- Node.js 18+ (`npx`) — for `create-slide`
- Node.js 18+ + `npm i -g @dokploy/cli` + `~/.omelet.json` (`dokploy_url`, `dokploy_api_key`) — for `dokploy-cli`
- Node.js 18+ (`npm i -g gitnexus`) - for `gitnexus` (optional `python3`/`make`/`g++` to also parse Dart/Kotlin/Swift)
- `python3` + `pyyaml` + `git` - for `harness-engineering` (`claude` CLI only for `garden --headless`). Runs on Windows and POSIX.
- `evo-agents` >= 0.2.0 (`uv tool install 'evo-ak>=0.2.0'`), signed in with `evo-agents hub login` - for hub sync, and for `harness-engineering`, `create-exec-plan` and `execute-plan` in a harness whose `harness.yaml` has `hub.project`, where `execute-plan` also needs `evo` >= 0.29.0 (`pip install -U evo-cli`)
- An evo-agents worker daemon >= 0.9.0 - for `create-exec-plan` in an author run; the worker brings `evo-agents worker plan` and `worker put`, and the hub hands the run its own copy of the skill
- `evo-agents` + `uv` + `gh` CLI + the `claude` CLI - for `update-evo-agents` (`python3` 3.9+ for its `scripts/check.py`, stdlib only)
- macOS + Homebrew (`dvisvgm`, `mupdf-tools`, `ffmpeg`, `texlive`, `font-inter`) + [`uv`](https://github.com/astral-sh/uv) + Python 3.12 - for `manim-explainer-video` (`scripts/setup.sh` installs all of it, idempotent)
- [`uv`](https://github.com/astral-sh/uv) + a Vbee app (`vbee.app_id`, `vbee.token`) and/or `openai_api_key` in the omelet store - for `speak`. `uv` resolves `evo_cli` from the server's PEP 723 metadata, so nothing is installed globally. `ffmpeg` (or any of `mpv`/`vlc`/`afplay`) for playback

## MCP servers

Skills are instructions; these are running servers an agent connects to.

| Server | Path | Tools | Setup |
|--------|------|-------|-------|
| `evo-tts` | `mcp/tts/server.py` | `speak`, `speak_batch`, `list_voices` | `bash mcp/tts/install.sh` |

`evo-tts` is a stdio MCP server with no SDK dependency - plain JSON-RPC, with `evo_cli` declared in
PEP 723 inline script metadata so `uv run --script` resolves it on first run. The installer
smoke-tests `tools/list` and registers the server with Claude Code at user scope.

## License

MIT
