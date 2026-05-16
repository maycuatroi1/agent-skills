# Agent Skills

Agent skills for AI coding agents, following the [Agent Skills](https://agentskills.io) open standard.

## Installation

```bash
npx skillfish add maycuatroi1/agent-skills
```

## Available Skills

| Skill | Description |
|-------|-------------|
| `generate-image` | Generate images using Google Gemini API via omelet CLI |
| `continuous-learning` | Auto-extract reusable patterns at session end (Stop hook) and save them as learned skills into the current project's `.claude/skills/learned/` |
| `credentials-utils` | Read/list/refresh/sync credentials in `~/.omelet.json`. Get values by nested key path, list with masked output, refresh rclone OAuth token, sync across machines via GitHub private repo + `gh` CLI |
| `create-slide` | Generate `.pptx` decks from a TypeScript content file via the open-source [`omelet-slide-generator`](https://github.com/maycuatroi1/omelet-slide-generator) (28 layouts, 3 themes, native OMML math, Shiki code highlighting) |
| `dokploy-cli` | Manage Dokploy services (apps, compose, postgres/mysql/mongo/redis, domains, env vars, deploys) via the official [`@dokploy/cli`](https://github.com/Dokploy/cli). 449 commands across 32 groups. One-shot setup: `bash skills/dokploy-cli/scripts/install.sh` (npm install + ~/.omelet.json check + shell rc + smoke test, idempotent) |

## Requirements

- [omelet CLI](https://github.com/maycuatroi1/omelet-cli) (`pip install omelet`) — for `generate-image`
- Google API key for Gemini — for `generate-image`
- `claude` CLI + `jq` + `python3` — for `continuous-learning`
- `python3` + `gh` CLI + `~/.omelet.json` — for `credentials-utils`
- Node.js 18+ (`npx`) — for `create-slide`
- Node.js 18+ + `npm i -g @dokploy/cli` + `~/.omelet.json` (`dokploy_url`, `dokploy_api_key`) — for `dokploy-cli`

## License

MIT
