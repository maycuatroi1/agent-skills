---
name: credentials-utils
description: This skill should be used when the user asks to "get credential", "load token", "đọc api key", "lấy token từ omelet.json", "refresh google/rclone token", "check outdated credentials", "sync omelet config", or mentions reading/listing/refreshing/syncing values from the omelet credential store. Source of truth is a per-service folder (`~/.omelet.d/credentials/`) that compiles to a flat `~/.omelet.json` for backward compatibility. Provides scripts to read nested keys, run a health/expiry doctor, refresh Google OAuth tokens, add/update entries, and sync the folder across machines via GitHub private repo + `gh` CLI.
version: 0.2.0
---

# credentials-utils

Read, list, refresh, and sync credentials for the omelet ecosystem.

## Architecture

Source of truth is a **folder of per-service files**, not a single flat JSON:

```
~/.omelet.d/credentials/        <- OMELET_DIR (default ~/.omelet.d), synced to private repo
  ai/openai.json                <- one file per service, with metadata + secret
  cms/ghost.json
  google-oauth/gmail.json
  ...
~/.omelet.json                  <- GENERATED flat artifact (DO NOT EDIT by hand)
```

Each file holds metadata (`service`, `category`, `type`, `expiry`, `status`, `rotate`, `description`) plus a `flat` block. `compile.py` deep-merges every `flat` block into `~/.omelet.json`. The flat file exists only for backward compat with consumers that read it directly (`omelet` CLI, `evo` CLI, `life`/red-life, dokploy export script). **Edit the folder, then compile.** External consumers (`evo`, `life`) can't be changed, which is why the flat artifact is kept.

## When to use

Trigger on any of:
- Need an API key, token, URL, or service-account path from the omelet store.
- Want to enumerate available credentials and see which are expired/stale (`doctor.py`).
- A Google OAuth access token is expired (rclone / gmail / google-drive / google-calendar).
- Adding or rotating a credential.
- Setting up the store on a new laptop, or syncing changes across machines.

## Quick reference

| Task | Command |
|------|---------|
| Health + expiry of every credential | `python3 scripts/doctor.py` |
| Read one value (dotted path) | `python3 scripts/get_credential.py <key.path>` |
| Read into env var | `eval "$(python3 scripts/get_credential.py --export OPENAI_API_KEY openai_api_key)"` |
| Add / update a value | `python3 scripts/add_credential.py <key.path>` (writes folder file, recompiles) |
| Refresh Google OAuth tokens | `python3 scripts/refresh_google_oauth.py --all` (or `--service gmail`) |
| Rebuild flat `~/.omelet.json` | `python3 scripts/compile.py` |
| Migrate an old flat omelet.json -> folder | `python3 scripts/migrate_to_folder.py [--source PATH] [--merge]` |
| Pull folder from remote | `OMELET_SYNC_REPO=owner/repo bash scripts/sync_pull.sh` |
| Push folder to remote | `OMELET_SYNC_REPO=owner/repo bash scripts/sync_push.sh` |

Configurable via env (no personal defaults baked in):
- `OMELET_DIR` — credentials folder root (default `~/.omelet.d`, folder is `$OMELET_DIR/credentials`)
- `OMELET_CONFIG` — compiled flat file path (default `~/.omelet.json`)
- `OMELET_SYNC_REPO` — **required** for sync; GitHub private repo `owner/repo`
- `OMELET_SYNC_DIR` — folder name inside the sync repo (default `credentials`)
- `RCLONE_DRIVE_CLIENT_ID` / `RCLONE_DRIVE_CLIENT_SECRET` — OAuth client for rclone refresh; alternatively stored in `google-oauth/rclone.json`

Set `OMELET_SYNC_REPO` once in your shell rc on every laptop.

## How to use each script

### Checking health (start here)

`doctor.py` scans every file, prints `FILE | SERVICE | TYPE | HEALTH | SECRET | EXPIRY`, flags `EXPIRED` / `expiring` OAuth tokens and `deprecated` entries, and exits non-zero if anything is expired (usable in a hook). Run it to answer "what do I have" and "what is outdated".

### Reading a single credential

`get_credential.py` reads the compiled flat file by dotted path (unchanged interface). It stays silent on stdout so it composes:

```bash
OPENAI_KEY="$(python3 scripts/get_credential.py openai_api_key)"
RCLONE_AT="$(python3 scripts/get_credential.py rclone.token.access_token)"
```

Exits non-zero with a stderr message if the path is missing. Never echo the value.

### Adding or updating a credential

`add_credential.py <key.path>` writes into the matching per-service folder file (looked up by top-level key), stamps `last_rotated`, then recompiles the flat file. Default mode prompts with no echo:

```bash
python3 scripts/add_credential.py openai_api_key
```

Alternative sources: `--from-stdin`, `--from-env VAR`, `--value VALUE` (leaks to history), `--json` (parse as JSON). Unknown top-level keys land in `tools/<key>.json` with minimal metadata - edit that file afterwards to set proper `service`/`category`/`description`.

### Migrating an old flat omelet.json into the folder

`migrate_to_folder.py` splits a flat `~/.omelet.json` into the per-service folder. Use it for the first-ever migration, or to fold in an old `omelet.json` from another machine.

```bash
python3 scripts/migrate_to_folder.py --dry-run               # preview the split, write nothing
python3 scripts/migrate_to_folder.py                         # first migration (refuses if folder non-empty)
python3 scripts/migrate_to_folder.py --source ~/old.omelet.json --merge   # fold an old file into the folder
```

Behaviour:
- Keys known to `_registry.py` go to their mapped file; **unmapped keys** are routed to `misc/<key>.json` with placeholder metadata and a warning (review and recategorize later, or add a spec to `_registry.py`). Pass `--strict` to abort on unmapped keys instead.
- `--merge` adds only keys **not already present** in the folder (existing values are never overwritten) - safe for pulling a stale machine's extra keys without clobbering newer ones.
- Without `--merge`, it refuses to touch a non-empty folder unless `--force`.
- Backs up the source file to `<source>.bak.<timestamp>` before writing.
- Run `compile.py` afterwards (or it is printed as the next step) to regenerate the flat file.

### Refreshing Google OAuth tokens

`rclone`, `gmail`, `google-drive`, `google-calendar` use ~1h access tokens with long-lived refresh tokens. Refresh and recompile in one step:

```bash
python3 scripts/refresh_google_oauth.py --all          # all four
python3 scripts/refresh_google_oauth.py --service gmail # one
python3 scripts/refresh_google_oauth.py --all --dry-run # verify without calling Google
```

It POSTs to Google's token endpoint, writes the new access token + expiry back into the folder file, and recompiles. `refresh_rclone_token.py` is kept as a thin wrapper (`--service rclone`).

### Syncing across machines

The credentials **folder** lives in a GitHub private repo; sync via `gh` CLI per laptop.
- After editing locally: `bash scripts/sync_push.sh` (refuses unless repo is PRIVATE).
- On another laptop: `bash scripts/sync_pull.sh` (backs up existing folder, then recompiles flat).
- First-time setup: see `references/sync-setup.md`.

## Security rules

- Never `cat` a file or echo a credential into the conversation, logs, or shared terminals.
- The sync repo must be private. The flat `~/.omelet.json` is a generated artifact - never commit it to the sync repo (only the folder is synced) and never hand-edit it.
- Folder and files are `chmod 600/700`. Preserve those modes.
- If a token leaks, rotate at the provider, update the folder file (`add_credential.py`), then `sync_push.sh`.

## Additional resources

- **`references/credentials-schema.md`** — folder layout, the per-file metadata schema, and per-service rotation notes.
- **`references/sync-setup.md`** — one-time setup of the GitHub private repo and `gh` auth on a fresh laptop.
