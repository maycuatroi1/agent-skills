#!/usr/bin/env bash
# Tao thu muc video moi tu scaffold roi dung moi truong.
#
#   ./new-video.sh <duong-dan-thu-muc> [slug]
#
# Vi du: ./new-video.sh ~/git/blog/manim/gradient-descent gradient-descent
set -euo pipefail

TARGET="${1:?Thieu duong dan thu muc dich}"
SLUG="${2:-$(basename "$TARGET")}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -e "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  echo "!! $TARGET da ton tai va khong rong. Dung de tranh ghi de."
  exit 1
fi

mkdir -p "$TARGET"
cp -R "$SKILL_DIR/assets/scaffold/." "$TARGET/"
chmod +x "$TARGET/render.sh"

# dat slug vao manifest de ten file mp4 dung ngay tu dau
python3 - "$TARGET/manifest.py" "$SLUG" <<'EOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
s = p.read_text(encoding="utf-8").replace('SLUG = "ten-video"', f'SLUG = "{sys.argv[2]}"')
p.write_text(s, encoding="utf-8")
EOF

echo "Scaffold da vao $TARGET (slug: $SLUG)"
echo
exec "$SKILL_DIR/scripts/setup.sh" "$TARGET"
