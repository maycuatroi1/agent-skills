#!/usr/bin/env bash
set -euo pipefail

# init-deck.sh — bootstrap a new omelet-slide-generator deck
#
# Usage:
#   bash init-deck.sh <target-dir> [theme]
#
#   <target-dir>  Directory to create (must not already exist as non-empty)
#   [theme]       n8n | minimalism | midnight  (default: n8n)
#
# Drops:
#   <target-dir>/package.json        (pinned to omelet-slide-generator on GitHub)
#   <target-dir>/slides/index.ts     (working starter content)
#   <target-dir>/slides/assets/      (empty image folder)
#   <target-dir>/.gitignore
#   <target-dir>/dist/               (created by npm run build)

if [[ $# -lt 1 ]]; then
  echo "usage: bash init-deck.sh <target-dir> [theme]" >&2
  exit 1
fi

TARGET="$1"
THEME="${2:-n8n}"

case "$THEME" in
  n8n|minimalism|midnight) ;;
  *)
    echo "error: unknown theme '$THEME' (use n8n | minimalism | midnight)" >&2
    exit 1
    ;;
esac

if [[ -e "$TARGET" && -n "$(ls -A "$TARGET" 2>/dev/null)" ]]; then
  echo "error: '$TARGET' exists and is not empty" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"

mkdir -p "$TARGET/slides/assets" "$TARGET/dist"

DECK_NAME="$(basename "$TARGET" | tr '[:upper:] ' '[:lower:]-')"

sed -e "s/DECK_NAME/$DECK_NAME/g" -e "s/THEME_NAME/$THEME/g" \
  "$ASSETS_DIR/package.template.json" > "$TARGET/package.json"

cp "$ASSETS_DIR/starter-slides.ts" "$TARGET/slides/index.ts"

cat > "$TARGET/.gitignore" <<'EOF'
node_modules/
dist/
*.log
EOF

cat <<EOF
Created $TARGET
  theme:    $THEME
  content:  $TARGET/slides/index.ts
  output:   $TARGET/dist/deck.pptx (after build)

Next:
  cd $TARGET
  npm install
  npm run build
EOF
