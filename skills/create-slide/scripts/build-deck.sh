#!/usr/bin/env bash
set -euo pipefail

# build-deck.sh — build instructor + student variants in one call
#
# Usage:
#   bash build-deck.sh <content-file> <output-prefix> [theme]
#
#   <content-file>   Path to slides/index.ts (or .js)
#   <output-prefix>  Output path without .pptx; produces <prefix>.pptx and <prefix>-student.pptx
#   [theme]          n8n | minimalism | midnight (default: n8n)
#
# Examples:
#   bash build-deck.sh slides/index.ts dist/lecture7
#   bash build-deck.sh slides/index.ts dist/lecture7 minimalism

if [[ $# -lt 2 ]]; then
  echo "usage: bash build-deck.sh <content-file> <output-prefix> [theme]" >&2
  exit 1
fi

CONTENT="$1"
PREFIX="$2"
THEME="${3:-n8n}"

case "$THEME" in
  n8n|minimalism|midnight) ;;
  *)
    echo "error: unknown theme '$THEME' (use n8n | minimalism | midnight)" >&2
    exit 1
    ;;
esac

if [[ ! -f "$CONTENT" ]]; then
  echo "error: content file not found: $CONTENT" >&2
  exit 1
fi

mkdir -p "$(dirname "$PREFIX")"

echo "Building instructor variant..."
npx -y github:maycuatroi1/omelet-slide-generator "$CONTENT" "${PREFIX}.pptx" --theme="$THEME"

echo "Building student variant..."
npx -y github:maycuatroi1/omelet-slide-generator "$CONTENT" "${PREFIX}-student.pptx" --theme="$THEME" --no-notes

echo "Done:"
echo "  ${PREFIX}.pptx          (instructor)"
echo "  ${PREFIX}-student.pptx  (student, no notes)"
