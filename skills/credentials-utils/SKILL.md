---
name: credentials-utils
description: This skill should be used when the user asks to "get credential", "load token", "đọc api key", "lấy token từ omelet.json", "refresh rclone token", "sync omelet config", or mentions reading/listing/refreshing/syncing values from `~/.omelet.json`. Provides scripts to safely read nested keys, list available credentials with masked values, refresh Google Drive OAuth tokens, and sync the config across machines via GitHub private repo + `gh` CLI.
version: 0.1.0
---

# credentials-utils

Read, list, refresh, and sync credentials stored in `~/.omelet.json` (the user's ad-hoc local secrets file).

## When to use

Trigger on any of:
- Need an API key, token, URL, or service-account path that lives in `~/.omelet.json`.
- Want to enumerate what credentials are available without dumping plaintext.
- The rclone Google Drive `access_token` is expired (check `rclone.token.expiry`).
- Setting up the file on a new laptop, or pushing local changes to other machines.

## Quick reference

| Task | Command |
|------|---------|
| Read one value | `python3 scripts/get_credential.py <key.path>` |
| Read into env var | `eval "$(python3 scripts/get_credential.py --export OPENAI_API_KEY openai_api_key)"` |
| Add / update a value | `python3 scripts/add_credential.py <key.path>` (prompts for value, no echo) |
| List everything (masked) | `python3 scripts/list_credentials.py` |
| Refresh rclone access_token | `python3 scripts/refresh_rclone_token.py` |
| Pull config from remote | `OMELET_SYNC_REPO=owner/repo bash scripts/sync_pull.sh` |
| Push local config to remote | `OMELET_SYNC_REPO=owner/repo bash scripts/sync_push.sh` |

Configurable via env (no personal defaults baked in):
- `OMELET_CONFIG` — path to config file (default `~/.omelet.json`)
- `OMELET_SYNC_REPO` — **required** for sync; GitHub private repo `owner/repo`
- `OMELET_SYNC_FILE` — filename inside the sync repo (default `omelet.json`)
- `RCLONE_DRIVE_CLIENT_ID` / `RCLONE_DRIVE_CLIENT_SECRET` — OAuth client for refresh; alternatively store in config under `rclone.client_id` / `rclone.client_secret`

Set `OMELET_SYNC_REPO` once in your shell rc (`~/.bashrc`, `~/.zshrc`) on every laptop.

## Key paths

Use dotted notation for nested keys. Common ones:
- `openai_api_key`, `google_api_key`, `kimi_code_api_key`, `cloudflare_api_token`
- `ghost_api_url`, `ghost_admin_api_key`, `ghost_content_api_key`
- `rclone.token.access_token`, `rclone.token.refresh_token`, `rclone.root_folder_id`
- `google_sheets_sa_key_path`, `google_sheets_sa_email`

Run `list_credentials.py` to see every key path with its purpose. Full schema in `references/credentials-schema.md`.

## How to use each script

### Reading a single credential

Prefer `get_credential.py` over `jq` or hand-rolled `python -c` — it handles nested paths, errors on missing keys, and stays silent on stdout so it composes cleanly:

```bash
OPENAI_KEY="$(python3 ~/git/agent-skills/skills/credentials-utils/scripts/get_credential.py openai_api_key)"
```

The script exits non-zero with a stderr message if the key path is missing. Never echo the value into terminal output or log files.

### Adding or updating a credential

Use `add_credential.py` to write a new key or rotate an existing one. Default mode prompts interactively with no echo — preferred to avoid leaking the value to shell history:

```bash
python3 ~/git/agent-skills/skills/credentials-utils/scripts/add_credential.py openai_api_key
```

Alternative sources:
- `--from-stdin` — pipe value in (`pbpaste | add_credential.py KEY --from-stdin`)
- `--from-env VAR_NAME` — copy from env var
- `--value VALUE` — inline (avoid when possible; leaks to shell history)
- `--json` — parse value as JSON (for booleans, numbers, nested objects)

Creates missing parent keys when using nested paths (e.g. `rclone.token.access_token` will create `rclone.token` if absent). Writes atomically and preserves `chmod 600`.

### Listing what is available

Run `list_credentials.py` when the user asks "what tokens do I have" or when picking a key to use. Output masks values (first 4 + last 4 chars only) and includes a description for each known key.

### Refreshing the rclone OAuth token

The `rclone.token.access_token` expires every ~1 hour. Check `rclone.token.expiry` (ISO8601); if past or near, run:

```bash
python3 ~/git/agent-skills/skills/credentials-utils/scripts/refresh_rclone_token.py
```

This POSTs to Google's OAuth token endpoint using `rclone.token.refresh_token` and writes the new access_token + expiry back atomically. Add `--dry-run` to verify without making the request. The script uses rclone's default Drive OAuth client unless `RCLONE_DRIVE_CLIENT_ID` / `RCLONE_DRIVE_CLIENT_SECRET` are set in env.

### Syncing across machines

The user keeps `~/.omelet.json` in a **GitHub private repo** and syncs via `gh` CLI on every laptop. Repo name lives in `OMELET_SYNC_REPO` env var, set per machine.

- First-time setup on a new machine: see `references/sync-setup.md`.
- Daily flow:
  - After editing local config: `bash scripts/sync_push.sh`
  - On another laptop, before working: `bash scripts/sync_pull.sh`
- `sync_pull.sh` backs up the existing local file to `~/.omelet.json.bak.<timestamp>` before overwriting.
- `sync_push.sh` is a no-op if there are no changes, and refuses to upload unless `gh repo view` reports the repo is PRIVATE.

## Security rules

- Never `cat` the file or echo a credential value into the conversation, logs, or shared terminals.
- Never commit `~/.omelet.json` (or any extracted secret) to a public repo. The sync repo must be private; the scripts assume this but do not enforce it.
- After `sync_pull.sh`, the file is `chmod 600`. Preserve that mode.
- If a token leaks, rotate at the provider (Google / OpenAI / Cloudflare / Ghost console) then push the new config with `sync_push.sh`.

## Additional resources

- **`references/credentials-schema.md`** — full table of every key in `~/.omelet.json`: purpose, lifetime, how to rotate.
- **`references/sync-setup.md`** — one-time setup of the GitHub private repo and `gh` auth on a fresh laptop.
