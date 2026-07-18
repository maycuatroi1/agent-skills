---
name: credentials-utils
description: This skill should be used when the user asks to "get credential", "load token", "đọc api key", "lấy token từ omelet.json", "refresh google/rclone token", "check outdated credentials", "sync omelet config", or mentions reading/listing/refreshing/syncing values from the omelet credential store. The store is owned by the `evo` CLI: a per-service folder (`~/.omelet.d/credentials/`) that compiles to a flat `~/.omelet.json` for backward compatibility. Every operation is a subcommand of `evo cred`.
version: 0.3.0
---

# credentials-utils

Read, list, refresh, and sync credentials for the omelet ecosystem.

**This skill owns no code.** The credential store is implemented in evo-cli
(`evo_cli/credentials/`, surfaced as `evo cred`). This file is a mirror of that command surface. If a
command here does not exist, the skill is stale - run `evo cred --help` and trust the CLI, then fix
this file.

## Prerequisite

`evo` >= 0.12.0 must be on PATH. `python setup.py` at the root of agent-skills installs it and
verifies `evo cred` exists. Check with `evo cred path`.

## Architecture

Source of truth is a **folder of per-service files**, not a single flat JSON:

```
~/.omelet.d/credentials/        <- OMELET_DIR (default ~/.omelet.d), synced to a private repo
  ai/openai.json                <- one file per service, with metadata + secret
  cms/ghost.json
  google-oauth/gmail.json
  ...
~/.omelet.json                  <- GENERATED flat artifact (DO NOT EDIT by hand)
```

Each file holds metadata (`service`, `category`, `type`, `expiry`, `status`, `rotate`, `description`)
plus a `flat` block. `evo cred compile` deep-merges every `flat` block into `~/.omelet.json`. The flat
file exists only for backward compat with consumers that read it directly (`omelet` CLI, `life`/red-life,
dokploy export script). **Edit the folder, then compile.**

## When to use

Trigger on any of:
- Need an API key, token, URL, or service-account path from the omelet store.
- Want to enumerate available credentials and see which are expired/stale.
- A Google OAuth access token is expired (rclone / gmail / google-drive / google-calendar).
- Adding or rotating a credential.
- Setting up the store on a new laptop, or syncing changes across machines.

## Quick reference

| Task | Command |
|------|---------|
| Health + expiry of every credential | `evo cred doctor` |
| List the store without the exit-code gate | `evo cred list` |
| Read one value (dotted path) | `evo cred get <key.path>` |
| Read into env var | `eval "$(evo cred get --export OPENAI_API_KEY openai_api_key)"` |
| Add / update a value | `evo cred add <key.path>` (writes folder file, recompiles) |
| Refresh Google OAuth tokens | `evo cred refresh --all` (or `--service gmail`) |
| Rebuild flat `~/.omelet.json` | `evo cred compile` |
| Migrate an old flat omelet.json -> folder | `evo cred migrate [--source PATH] [--merge]` |
| Pull folder from remote | `evo cred sync pull` |
| Push folder to remote | `evo cred sync push` |
| Show resolved store paths | `evo cred path` |

Configurable via env (no personal defaults baked in):
- `OMELET_DIR` - credentials folder root (default `~/.omelet.d`, folder is `$OMELET_DIR/credentials`)
- `OMELET_CONFIG` - compiled flat file path (default `~/.omelet.json`)
- `OMELET_SYNC_REPO` - **required** for sync; GitHub private repo `owner/repo`
- `OMELET_SYNC_DIR` - folder name inside the sync repo (default `credentials`)
- `RCLONE_DRIVE_CLIENT_ID` / `RCLONE_DRIVE_CLIENT_SECRET` - OAuth client for rclone refresh;
  alternatively stored in `google-oauth/rclone.json`

Set `OMELET_SYNC_REPO` once in your shell rc on every laptop.

## How to use each command

### Checking health (start here)

`evo cred doctor` scans every file, prints `FILE | SERVICE | TYPE | HEALTH | SECRET | EXPIRY`, flags
`EXPIRED` / `expiring` OAuth tokens and `deprecated` entries, and exits non-zero if anything is expired
(usable in a hook). Run it to answer "what do I have" and "what is outdated". `evo cred list` prints the
same table but always exits 0.

### Reading a single credential

`evo cred get` reads the compiled flat file by dotted path. Only the value reaches stdout, so it
composes:

```bash
OPENAI_KEY="$(evo cred get openai_api_key)"
RCLONE_AT="$(evo cred get rclone.token.access_token)"
```

Exits non-zero with a message if the path is missing. Never echo the value.

### Adding or updating a credential

`evo cred add <key.path>` writes into the matching per-service folder file (looked up by top-level key),
stamps `last_rotated`, then recompiles the flat file. Default mode prompts with no echo:

```bash
evo cred add openai_api_key
```

Alternative sources: `--from-stdin`, `--from-env VAR`, `--value VALUE` (leaks to history), `--json`
(parse as JSON). Unknown top-level keys land in `tools/<key>.json` with minimal metadata - edit that
file afterwards to set proper `service`/`category`/`description`, or add a spec to
`evo_cli/credentials/registry.py`.

### Migrating an old flat omelet.json into the folder

`evo cred migrate` splits a flat `~/.omelet.json` into the per-service folder. Use it for the
first-ever migration, or to fold in an old `omelet.json` from another machine.

```bash
evo cred migrate --dry-run                              # preview the split, write nothing
evo cred migrate                                        # first migration (refuses if folder non-empty)
evo cred migrate --source ~/old.omelet.json --merge     # fold an old file into the folder
```

Behaviour:
- Keys known to the registry go to their mapped file; **unmapped keys** are routed to `misc/<key>.json`
  with placeholder metadata and a warning. Pass `--strict` to abort on unmapped keys instead.
- `--merge` adds only keys **not already present** in the folder (existing values are never
  overwritten) - safe for pulling a stale machine's extra keys without clobbering newer ones.
- Without `--merge`, it refuses to touch a non-empty folder unless `--force`.
- Backs up the source file to `<source>.bak.<timestamp>` before writing, then recompiles.

### Refreshing Google OAuth tokens

`rclone`, `gmail`, `google-drive`, `google-calendar` use ~1h access tokens with long-lived refresh
tokens. Refresh and recompile in one step:

```bash
evo cred refresh --all                      # all four
evo cred refresh --service gmail            # one
evo cred refresh --all --dry-run            # verify without calling Google
```

It POSTs to Google's token endpoint, writes the new access token + expiry back into the folder file, and
recompiles.

### Syncing across machines

The credentials **folder** lives in a GitHub private repo; sync via `gh` CLI per laptop.
- After editing locally: `evo cred sync push` (refuses unless the repo is PRIVATE).
- On another laptop: `evo cred sync pull` (backs up existing folder, then recompiles flat).
- First-time setup: see `references/sync-setup.md`.

## Security rules

- Never `cat` a file or echo a credential into the conversation, logs, or shared terminals.
- The sync repo must be private. The flat `~/.omelet.json` is a generated artifact - never commit it to
  the sync repo (only the folder is synced) and never hand-edit it.
- Folder and files are `chmod 600/700`. Preserve those modes.
- If a token leaks, rotate at the provider, update the folder file (`evo cred add`), then
  `evo cred sync push`.

## Write-race hazard

`~/.omelet.json` has more than one writer. `evo cred compile` regenerates it from `~/.omelet.d/`, while
red-life (`packages/core/src/drive`) refreshes `rclone.token` straight into the flat file. If red-life
refreshed last, a `compile` silently reverts that token.

Before compiling after a gap, check that the two sides agree:

```bash
OMELET_CONFIG=/tmp/probe.json evo cred compile
python3 -c "import json,os;a=json.load(open('/tmp/probe.json'));b=json.load(open(os.path.expanduser('~/.omelet.json')));print('folder:',a['rclone']['token']['expiry']);print('flat  :',b['rclone']['token']['expiry'])"
```

If the flat file is newer, fold it back into the folder with
`evo cred add rclone.token.access_token --from-stdin` before compiling. See
`red-life-harness/principles/golden-principles.md`.

## Additional resources

- **`references/credentials-schema.md`** - folder layout, the per-file metadata schema, and per-service
  rotation notes.
- **`references/sync-setup.md`** - one-time setup of the GitHub private repo and `gh` auth on a fresh
  laptop.
