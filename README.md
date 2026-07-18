# Agent Skills

Agent skills for AI coding agents, following the [Agent Skills](https://agentskills.io) open standard.

## Installation

```bash
npx skillfish add maycuatroi1/agent-skills
```

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
| `manim-explainer-video` | Build animated technical explainer videos with [Manim Community](https://www.manim.community/): light theme, Vietnamese narration, real computed numbers, plus a timecoded dubbing script and frame-accurate SRT subtitles. Ships a working scaffold (`scripts/new-video.sh <dir>`) and the macOS workarounds Manim needs to render LaTeX + Vietnamese at all |

## Requirements

- [omelet CLI](https://github.com/maycuatroi1/omelet-cli) (`pip install omelet`) — for `generate-image`
- Google API key for Gemini — for `generate-image`
- `claude` CLI + `jq` + `python3` — for `continuous-learning`
- `evo` >= 0.12.0 (`pip install evo_cli`, or `python setup.py` here) + `gh` CLI - for `credentials-utils`
- Node.js 18+ (`npx`) — for `create-slide`
- Node.js 18+ + `npm i -g @dokploy/cli` + `~/.omelet.json` (`dokploy_url`, `dokploy_api_key`) — for `dokploy-cli`
- Node.js 18+ (`npm i -g gitnexus`) - for `gitnexus` (optional `python3`/`make`/`g++` to also parse Dart/Kotlin/Swift)
- `python3` + `pyyaml` + `git` - for `harness-engineering` (`claude` CLI only for `garden --headless`). Runs on Windows and POSIX.
- macOS + Homebrew (`dvisvgm`, `mupdf-tools`, `ffmpeg`, `texlive`, `font-inter`) + [`uv`](https://github.com/astral-sh/uv) + Python 3.12 - for `manim-explainer-video` (`scripts/setup.sh` installs all of it, idempotent)

## License

MIT
