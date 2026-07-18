---
name: life-cli
description: Personal life management via the `life` CLI (pnpm workspace `red-life` from maycuatroi1/red-life). Trigger on "life cli", "install life", "todo/công việc", "lịch/calendar", "kế hoạch/plan", "nhật ký/journal", "people/mối quan hệ", "places/địa điểm", "notes", "health/cân nặng/calories", "daily overview", "drive/upload", "facebook messages", "tiktok", "teach/lịch dạy", "gmail/mail" when the user wants to manage personal data through the CLI. Compact by design: discover commands at runtime with `life --help` and `life <group> --help` instead of a hardcoded reference. Covers install via pnpm, credential locations (firebase-credentials.json, ~/.omelet.json), RED_LIFE_HOME, and the Playwright requirement for fb/tiktok.
version: 0.2.0
---

# life-cli

`life` is a personal life management CLI backed by Firestore (single source of truth, shared with the web app at http://life.omelet.tech). 14 command groups: todo, plan, journal, health, cal, mail, day, people, places, notes, drive, fb, tiktok, teach.

| Group | Purpose |
| --- | --- |
| `todo` | TODO management |
| `plan` | Plan management |
| `journal` | Daily journal |
| `health` | Health / weight tracking |
| `cal` | Google Calendar |
| `mail` | Gmail (read + send) |
| `day` | Daily overview (todos + calendar + plan + journal + health) |
| `people` | People / relationship management |
| `places` | Places / locations management |
| `notes` | Notes / knowledge base |
| `drive` | Google Drive (artifact uploads) |
| `fb` | Facebook / Messenger (via Playwright) |
| `tiktok` | TikTok channel management (via Playwright + yt-dlp) |
| `teach` | Teaching schedule, todos & calendar sync |

## Discovery (always do this first)

The CLI is self-documenting. Do NOT rely on a memorized command list, query it live:

```bash
life --help                  # 14 command groups
life <group> --help          # actions in a group (e.g. life todo --help)
life <group> <action> --help # flags for an action (e.g. life todo add --help)
```

## Install

`red-life` is a pnpm workspace (`web`, `packages/core`, `packages/cli`), not a published package. There is no pip install.

```bash
git clone https://github.com/maycuatroi1/red-life.git
cd red-life
pnpm install
```

`pnpm install` runs `scripts/link-cli-global.mjs`, which symlinks `packages/cli/bin/life.mjs` into the pnpm global bin dir as `life`. Requirements and escape hatches:

- Needs `PNPM_HOME` set, or `pnpm bin -g` must resolve. Make sure that dir is on `PATH`.
- Skipped when `CI` or `RED_LIFE_SKIP_LINK` is set, and when the installer is not pnpm.
- If linking fails it warns instead of failing the install. Link manually:
  `ln -sf <repo>/packages/cli/bin/life.mjs "$PNPM_HOME/bin/life"`

The bin is a thin `tsx` loader that runs `packages/cli/src/index.ts` directly, so there is no build step. Edits to the CLI take effect immediately.

On the dev machine the repo lives at `~/github/red-life`.

## Credentials and data root

`PROJECT_ROOT` resolution in `packages/core/src/utils/paths.ts`, in order:

1. `RED_LIFE_HOME` env var
2. `CLAUDE_PROJECT_DIR` env var
3. Nearest ancestor of `cwd` containing any of `firebase-credentials.json`, `pyproject.toml`, `pnpm-workspace.yaml`, `.git`
4. `~/.red-life` otherwise

Derived paths: `data/`, `workspace/`, `plans/`, `token.json`, `firebase-credentials.json`.

Firestore auth is the `firebase-credentials.json` service account (project omelet-f0b89) at `PROJECT_ROOT`, or the `FIREBASE_CREDENTIALS_JSON` env var holding the JSON inline.

Google OAuth and rclone are read from `~/.omelet.json` (override with `OMELET_CONFIG`): `google_calendar.credentials`, `google_calendar.token`, `gmail.token`, plus rclone `client_id` / `client_secret` / `token.refresh_token` for `teach` and `drive`. Run `life cal auth` once before `life mail auth`. Note: `~/.omelet.json` is a generated flat artifact, the source of truth is the per-service folder `~/.omelet.d/credentials/` (files `google-oauth/gmail.json`, `google-oauth/google-calendar.json`) managed by the `credentials-utils` skill, which compiles back to the flat file. Refresh expired Google tokens with `evo cred refresh --all`; sync across machines with `evo cred sync pull` / `evo cred sync push`.

New machine setup:

```bash
git clone https://github.com/maycuatroi1/red-life.git ~/github/red-life
cd ~/github/red-life && pnpm install
# copy firebase-credentials.json into the repo root (or set RED_LIFE_HOME)
life cal auth
```

## Gotchas

- `life todo list` shows pending only; add `--all` to include done/cancelled.
- `life fb *` and `life tiktok *` need Playwright Chromium (`npx playwright install chromium`, looked up under `~/.cache/ms-playwright`). They use persistent profiles at `~/.claude/playwright-profiles/facebook` and `~/.claude/playwright-profiles/tiktok`. Close any Playwright MCP browser first, they share the profile.
- `life tiktok *` also needs `yt-dlp` on `PATH`.
- `life places *` no longer needs Playwright.
- `life mail send` reads the body from stdin when neither `--body` nor `--body-file` is given.
- `life day` is the 5-second full overview: overdue + today + calendar + plan + journal + health.
- Because `PROJECT_ROOT` falls back to the nearest `.git` ancestor, running `life` from inside an unrelated repo resolves the data root to that repo. Set `RED_LIFE_HOME` to pin it.
- Timezone is Asia/Ho_Chi_Minh; dates are YYYY-MM-DD.

## See also

- Source: https://github.com/maycuatroi1/red-life (`packages/cli/src/index.ts` is the entry point, `packages/core` holds the shared logic)
- Credentials lifecycle: `credentials-utils` skill
- Dokploy management: `dokploy-cli` skill
