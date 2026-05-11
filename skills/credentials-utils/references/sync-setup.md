# Sync setup: `~/.omelet.json` via GitHub private repo + `gh` CLI

One-time setup per repo (one machine) and per laptop. After this, daily sync uses `sync_pull.sh` / `sync_push.sh`.

## Prerequisites

- `gh` CLI installed and on `PATH` (`gh --version`)
- A GitHub account (the repo will live under it)
- `git` installed (comes with `gh` on most systems)

## First-ever setup (run on ONE laptop only)

This creates the private repo that holds `omelet.json`. Replace `<owner>` and `<repo>` with your own:

```bash
gh auth login

gh repo create <owner>/<repo> --private --description "Personal config sync (private)" --confirm

export OMELET_SYNC_REPO="<owner>/<repo>"

bash ~/git/agent-skills/skills/credentials-utils/scripts/sync_push.sh
```

The push script will clone the new (empty) repo, copy `~/.omelet.json` into it, commit, and push.

Verify on github.com:
- Repo visibility shows **Private** (lock icon).
- `omelet.json` is present.
- No collaborators.

Recommended hardening:
- Enable 2FA on the GitHub account.
- Use a passkey or hardware key for `gh auth login`.
- In repo settings, disable Issues, Pull Requests, Wiki, Discussions (not needed).

## Setup on every new laptop

```bash
gh auth login
export OMELET_SYNC_REPO="<owner>/<repo>"
bash ~/git/agent-skills/skills/credentials-utils/scripts/sync_pull.sh
```

`sync_pull.sh` clones the repo, copies the synced file to `~/.omelet.json`, and `chmod 600` it. Any pre-existing local file is backed up to `~/.omelet.json.bak.<timestamp>` first.

Persist the env var so future shells pick it up:

```bash
echo 'export OMELET_SYNC_REPO="<owner>/<repo>"' >> ~/.bashrc
```

(or `~/.zshrc` for zsh)

## Customizing the filename / config path

Override via env vars (set them in `~/.bashrc` / `~/.zshrc` if non-default):

```bash
export OMELET_SYNC_REPO="<owner>/<repo>"
export OMELET_SYNC_FILE="omelet.json"
export OMELET_CONFIG="$HOME/.omelet.json"
```

All scripts read these vars.

## Daily flow

After editing local `~/.omelet.json` (new key, rotated token, etc.):

```bash
bash ~/git/agent-skills/skills/credentials-utils/scripts/sync_push.sh
```

On another laptop, before working:

```bash
bash ~/git/agent-skills/skills/credentials-utils/scripts/sync_pull.sh
```

The push script refuses to upload if `gh repo view` reports the repo is not `PRIVATE` — a guard against accidental public exposure.

## Safety guarantees in the scripts

- `sync_pull.sh` — Backs up `~/.omelet.json` before overwrite; sets `chmod 600` after copy.
- `sync_push.sh` — Aborts if remote repo is not Private; aborts if `gh` not logged in; no-op when there are no changes to commit.
- Neither script logs token values; only paths and commit metadata.

## Optional: encryption layer (out of scope for this skill)

A private GitHub repo is the user's chosen trust boundary. If stronger guarantees are needed later:

- **age + chezmoi** — Encrypt the file with `age` and let `chezmoi` manage state. See https://www.chezmoi.io/user-guide/encryption/age/
- **git-crypt** — Transparent file-level encryption inside the repo. Requires GPG key sync across machines.
- **1Password CLI (`op`)** — Store each credential as a separate item; `op read` injects at runtime. Stronger isolation per secret.

None of these are wired into this skill — they would replace, not extend, the current sync flow.

## Recovery

If the local file is corrupted or lost:

```bash
bash ~/git/agent-skills/skills/credentials-utils/scripts/sync_pull.sh
```

If the remote repo is wrong (bad commit pushed):

```bash
cd "$(mktemp -d)"
gh repo clone "$OMELET_SYNC_REPO" .
git log --oneline omelet.json
git checkout <good-commit-sha> -- omelet.json
git commit -m "revert to <good-commit-sha>"
git push
```
