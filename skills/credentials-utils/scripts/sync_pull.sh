#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${OMELET_SYNC_REPO:-}" ]]; then
    echo "OMELET_SYNC_REPO env var required (format: owner/repo, must be PRIVATE)" >&2
    exit 1
fi
REPO="$OMELET_SYNC_REPO"
DIR_IN_REPO="${OMELET_SYNC_DIR:-credentials}"
DEST_DIR="${OMELET_DIR:-$HOME/.omelet.d}/credentials"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

SRC_DIR="$TMP/repo/$DIR_IN_REPO"
if [[ ! -d "$SRC_DIR" ]]; then
    echo "folder '$DIR_IN_REPO' not found in repo $REPO" >&2
    exit 1
fi

if [[ -d "$DEST_DIR" ]]; then
    BACKUP="${DEST_DIR}.bak.$(date +%Y%m%d-%H%M%S)"
    cp -a "$DEST_DIR" "$BACKUP"
    echo "backed up existing $DEST_DIR -> $BACKUP" >&2
fi

mkdir -p "$DEST_DIR"
rm -rf "${DEST_DIR:?}/"*
cp -a "$SRC_DIR/." "$DEST_DIR/"
chmod -R go-rwx "$DEST_DIR"
echo "pulled $REPO:$DIR_IN_REPO/ -> $DEST_DIR" >&2

python3 "$HERE/compile.py"
