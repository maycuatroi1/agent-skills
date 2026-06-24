#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${OMELET_SYNC_REPO:-}" ]]; then
    echo "OMELET_SYNC_REPO env var required (format: owner/repo, must be PRIVATE)" >&2
    exit 1
fi
REPO="$OMELET_SYNC_REPO"
DIR_IN_REPO="${OMELET_SYNC_DIR:-credentials}"
SRC_DIR="${OMELET_DIR:-$HOME/.omelet.d}/credentials"

if ! command -v gh >/dev/null 2>&1; then
    echo "gh CLI not found. Install: https://cli.github.com" >&2
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "gh not authenticated. Run: gh auth login" >&2
    exit 1
fi

if [[ ! -d "$SRC_DIR" ]]; then
    echo "local credentials folder $SRC_DIR not found (run migrate_to_folder.py)" >&2
    exit 1
fi

VISIBILITY="$(gh repo view "$REPO" --json visibility -q .visibility 2>/dev/null || echo "")"
if [[ "$VISIBILITY" != "PRIVATE" ]]; then
    echo "refusing to push: repo $REPO visibility is '$VISIBILITY' (must be PRIVATE)" >&2
    exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

gh repo clone "$REPO" "$TMP/repo" -- --quiet 2>/dev/null || gh repo clone "$REPO" "$TMP/repo"

rm -rf "$TMP/repo/$DIR_IN_REPO"
mkdir -p "$TMP/repo/$DIR_IN_REPO"
cp -a "$SRC_DIR/." "$TMP/repo/$DIR_IN_REPO/"

cd "$TMP/repo"
git add -A "$DIR_IN_REPO"
if git diff --cached --quiet; then
    echo "no changes to push" >&2
    exit 0
fi

HOST="$(hostname)"
STAMP="$(date -Iseconds)"
git commit -m "sync $DIR_IN_REPO from $HOST at $STAMP" >/dev/null

if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
    git push --quiet
else
    BRANCH="$(git symbolic-ref --short HEAD)"
    git push --quiet --set-upstream origin "$BRANCH"
fi
echo "pushed $DIR_IN_REPO/ to $REPO (from $HOST)" >&2
