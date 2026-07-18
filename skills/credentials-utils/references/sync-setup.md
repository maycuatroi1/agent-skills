# Sync setup: credentials folder via GitHub private repo + `gh` CLI

The **folder** `${OMELET_DIR:-~/.omelet.d}/credentials/` is the source of truth and the thing synced. The flat `~/.omelet.json` is a generated artifact - it is NOT committed to the sync repo and must never be hand-edited; each machine regenerates it locally via `evo cred compile` (run automatically after `evo cred sync pull`).

One-time setup per repo (one machine) and per laptop. After this, daily sync uses `evo cred sync pull` / `evo cred sync push`.

## Prerequisites

- `gh` CLI installed and on `PATH` (`gh --version`)
- A GitHub account (the repo will live under it)
- A migrated local folder (`evo cred migrate` once, if coming from a flat `~/.omelet.json`)

## First-ever setup (run on ONE laptop only)

```bash
gh auth login

gh repo create <owner>/<repo> --private --description "Personal credentials sync (private)" --confirm

export OMELET_SYNC_REPO="<owner>/<repo>"

evo cred sync push
```

The push command clones the repo, mirrors `~/.omelet.d/credentials/` into the repo under `credentials/`, commits, and pushes.

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
evo cred sync pull
```

`evo cred sync pull` clones the repo, replaces `~/.omelet.d/credentials/` (backing up any existing folder to `~/.omelet.d/credentials.bak.<timestamp>`), and runs `evo cred compile` to regenerate `~/.omelet.json`.

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

After editing the folder (via `evo cred add`, `evo cred refresh`, or hand-editing a file then `evo cred compile`):

```bash
evo cred sync push
```

On another laptop, before working:

```bash
evo cred sync pull
```

The push command refuses to upload if `gh repo view` reports the repo is not `PRIVATE`.

## Safety guarantees

- `evo cred sync pull` - backs up the existing folder before overwrite; `chmod go-rwx` after copy; recompiles flat.
- `evo cred sync push` - aborts if the remote repo is not Private or `gh` is not logged in; no-op when there are no changes.
- Neither command logs secret values; only paths and commit metadata.

## Optional: encryption layer (out of scope for this skill)

A private GitHub repo is the chosen trust boundary. For stronger guarantees later, replace (not extend) the sync flow with `age` + `chezmoi`, `git-crypt`, `sops`, or 1Password CLI (`op`). None are wired in here.

## Recovery

If the local folder is corrupted or lost:

```bash
evo cred sync pull
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
