#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${OMELET_SYNC_REPO:-}" ]]; then
    echo "OMELET_SYNC_REPO env var required (format: owner/repo, must be PRIVATE)" >&2
    exit 1
fi
REPO="$OMELET_SYNC_REPO"
FILE_IN_REPO="${OMELET_SYNC_FILE:-omelet.json}"
SRC="${OMELET_CONFIG:-$HOME/.omelet.json}"

if ! command -v gh >/dev/null 2>&1; then
    echo "gh CLI not found. Install: https://cli.github.com" >&2
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "gh not authenticated. Run: gh auth login" >&2
    exit 1
fi

if [[ ! -f "$SRC" ]]; then
    echo "local config $SRC not found" >&2
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

cp "$SRC" "$TMP/repo/$FILE_IN_REPO"

cd "$TMP/repo"
git add "$FILE_IN_REPO"
if git diff --cached --quiet; then
    echo "no changes to push" >&2
    exit 0
fi

HOST="$(hostname)"
STAMP="$(date -Iseconds)"
git commit -m "sync $FILE_IN_REPO from $HOST at $STAMP" >/dev/null

if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
    git push --quiet
else
    BRANCH="$(git symbolic-ref --short HEAD)"
    git push --quiet --set-upstream origin "$BRANCH"
fi
echo "pushed $FILE_IN_REPO to $REPO (from $HOST)" >&2
