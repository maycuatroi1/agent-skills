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

## Requirements

- [omelet CLI](https://github.com/maycuatroi1/omelet-cli) (`pip install omelet`) — for `generate-image`
- Google API key for Gemini — for `generate-image`
- `claude` CLI + `jq` + `python3` — for `continuous-learning`
- `python3` + `gh` CLI + `~/.omelet.json` — for `credentials-utils`
- Node.js 18+ (`npx`) — for `create-slide`

## License

MIT
