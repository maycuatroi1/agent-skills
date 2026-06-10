---
name: life-cli
description: Personal life management via the `life` CLI (pip package `red-life` from maycuatroi1/red-life). Trigger on "life cli", "install life", "todo/cong viec", "lich/calendar", "ke hoach/plan", "nhat ky/journal", "people/moi quan he", "places/dia diem", "notes", "health/can nang/calories", "daily overview", "facebook messages", "gmail/mail" when the user wants to manage personal data through the CLI. Compact by design: discover commands at runtime with `life --help` and `life <group> --help` instead of a hardcoded reference. Covers install via pip, credential locations (firebase-credentials.json, ~/.omelet.json), RED_LIFE_HOME, and the playwright extra for fb/places.
version: 0.1.0
---

# life-cli

`life` is a personal life management CLI backed by Firestore (single source of truth, shared with the web app at http://life.omelet.tech). 12 command groups: todo, cal, plan, journal, people, places, notes, health, day, web, fb, mail.

## Discovery (always do this first)

The CLI is self-documenting. Do NOT rely on a memorized command list — query it live:

```bash
life --help                  # 12 command groups
life <group> --help          # actions in a group (e.g. life todo --help)
life <group> <action> --help # flags for an action (e.g. life todo add --help)
```

## Install

```bash
pip install git+https://github.com/maycuatroi1/red-life.git
pip install "red-life[browser] @ git+https://github.com/maycuatroi1/red-life.git"  # + playwright for fb/places
```

On the dev machine the repo lives at `~/git/red-life` and is installed editable (`pip install -e .`), so data and credentials resolve to the repo itself.

## Credentials and data root

`PROJECT_ROOT` resolution in `red_life_cli/utils/config.py`:

1. `RED_LIFE_HOME` env var if set
2. Repo root if running from a git checkout / editable install
3. `~/.red-life` otherwise (normal pip install)

Required files inside that root:

- `firebase-credentials.json` - Firestore service account (project omelet-f0b89)
- `token.json` - legacy Google OAuth token location

Shared Google OAuth lives in `~/.omelet.json`: `google_calendar.credentials`, `google_calendar.token`, `gmail.token`. Run `life cal auth` once before `life mail auth`. Sync `~/.omelet.json` across machines with the `credentials-utils` skill.

New machine setup:

```bash
pip install git+https://github.com/maycuatroi1/red-life.git
mkdir -p ~/.red-life
# copy firebase-credentials.json into ~/.red-life/ (or set RED_LIFE_HOME)
life cal auth
```

## Gotchas

- `life todo list` shows pending only; add `--all` to include done/cancelled.
- `life fb *` and `life places search/details/suggest` need playwright (`[browser]` extra plus `playwright install chromium`). FB uses the persistent profile at `~/.claude/playwright-profiles/facebook` - close any Playwright MCP browser first, they share the profile.
- `life mail send` reads the body from stdin when neither `--body` nor `--body-file` is given.
- `life day` is the 5-second full overview: overdue + today + calendar + plan + journal + health.
- `life web deploy` pushes master and triggers the Dokploy deploy of the web app.
- Timezone is Asia/Ho_Chi_Minh; dates are YYYY-MM-DD.

## See also

- Source: https://github.com/maycuatroi1/red-life (`red_life_cli/cli.py` is the entry point)
- Credentials lifecycle: `credentials-utils` skill
- Dokploy management: `dokploy-cli` skill
