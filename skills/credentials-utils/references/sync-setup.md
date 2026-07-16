# Sync setup: credentials folder via GitHub private repo + `gh` CLI

The **folder** `${OMELET_DIR:-~/.omelet.d}/credentials/` is the source of truth and the thing synced. The flat `~/.omelet.json` is a generated artifact - it is NOT committed to the sync repo and must never be hand-edited; each machine regenerates it locally via `compile.py` (run automatically after `sync_pull.sh`).

One-time setup per repo (one machine) and per laptop. After this, daily sync uses `sync_pull.sh` / `sync_push.sh`.

## Prerequisites

- `gh` CLI installed and on `PATH` (`gh --version`)
- A GitHub account (the repo will live under it)
- A migrated local folder (`python3 scripts/migrate_to_folder.py` once, if coming from a flat `~/.omelet.json`)

## First-ever setup (run on ONE laptop only)

```bash
gh auth login

gh repo create <owner>/<repo> --private --description "Personal credentials sync (private)" --confirm

export OMELET_SYNC_REPO="<owner>/<repo>"

bash ~/git/agent-skills/skills/credentials-utils/scripts/sync_push.sh
```

The push script clones the repo, mirrors `~/.omelet.d/credentials/` into the repo under `credentials/`, commits, and pushes.

Verify on github.com:
- Repo visibility shows **Private** (lock icon).
- A `credentials/` folder is present (per-service files); no flat `omelet.json`.
- No collaborators.

Recommended hardening:
- Enable 2FA; use a passkey/hardware key for `gh auth login`.
- Disable Issues, PRs, Wiki, Discussions in repo settings.

## Setup on every new laptop

```bash
gh auth login
export OMELET_SYNC_REPO="<owner>/<repo>"
bash ~/git/agent-skills/skills/credentials-utils/scripts/sync_pull.sh
```

`sync_pull.sh` clones the repo, replaces `~/.omelet.d/credentials/` (backing up any existing folder to `~/.omelet.d/credentials.bak.<timestamp>`), and runs `compile.py` to regenerate `~/.omelet.json`.

Persist the env var:

```bash
echo 'export OMELET_SYNC_REPO="<owner>/<repo>"' >> ~/.bashrc   # or ~/.zshrc
```

## Customizing paths

```bash
export OMELET_SYNC_REPO="<owner>/<repo>"
export OMELET_SYNC_DIR="credentials"            # folder name inside the repo
export OMELET_DIR="$HOME/.omelet.d"             # local store root
export OMELET_CONFIG="$HOME/.omelet.json"       # generated flat artifact
```

## Daily flow

After editing the folder (via `add_credential.py`, `refresh_google_oauth.py`, or hand-editing a file then `compile.py`):

```bash
bash ~/git/agent-skills/skills/credentials-utils/scripts/sync_push.sh
```

On another laptop, before working:

```bash
bash ~/git/agent-skills/skills/credentials-utils/scripts/sync_pull.sh
```

The push script refuses to upload if `gh repo view` reports the repo is not `PRIVATE`.

## Safety guarantees in the scripts

- `sync_pull.sh` — backs up the existing folder before overwrite; `chmod go-rwx` after copy; recompiles flat.
- `sync_push.sh` — aborts if the remote repo is not Private or `gh` is not logged in; no-op when there are no changes.
- Neither script logs secret values; only paths and commit metadata.

## Optional: encryption layer (out of scope for this skill)

A private GitHub repo is the chosen trust boundary. For stronger guarantees later, replace (not extend) the sync flow with `age` + `chezmoi`, `git-crypt`, `sops`, or 1Password CLI (`op`). None are wired in here.

## Recovery

If the local folder is corrupted or lost:

```bash
bash ~/git/agent-skills/skills/credentials-utils/scripts/sync_pull.sh
```

If the remote is wrong (bad commit pushed):

```bash
cd "$(mktemp -d)"
gh repo clone "$OMELET_SYNC_REPO" .
git log --oneline -- credentials/
git checkout <good-commit-sha> -- credentials/
git commit -m "revert credentials to <good-commit-sha>"
git push
```
