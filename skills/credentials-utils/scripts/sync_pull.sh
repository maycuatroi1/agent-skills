#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${OMELET_SYNC_REPO:-}" ]]; then
    echo "OMELET_SYNC_REPO env var required (format: owner/repo, must be PRIVATE)" >&2
    exit 1
fi
REPO="$OMELET_SYNC_REPO"
FILE_IN_REPO="${OMELET_SYNC_FILE:-omelet.json}"
DEST="${OMELET_CONFIG:-$HOME/.omelet.json}"

if ! command -v gh >/dev/null 2>&1; then
    echo "gh CLI not found. Install: https://cli.github.com" >&2
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "gh not authenticated. Run: gh auth login" >&2
    exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

gh repo clone "$REPO" "$TMP/repo" -- --depth=1 --quiet

SRC="$TMP/repo/$FILE_IN_REPO"
if [[ ! -f "$SRC" ]]; then
    echo "file '$FILE_IN_REPO' not found in repo $REPO" >&2
    exit 1
fi

if [[ -f "$DEST" ]]; then
    BACKUP="${DEST}.bak.$(date +%Y%m%d-%H%M%S)"
    cp -p "$DEST" "$BACKUP"
    echo "backed up existing $DEST -> $BACKUP" >&2
fi

cp "$SRC" "$DEST"
chmod 600 "$DEST"
echo "pulled $REPO:$FILE_IN_REPO -> $DEST" >&2
