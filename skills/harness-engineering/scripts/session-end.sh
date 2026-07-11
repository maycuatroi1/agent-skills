#!/usr/bin/env bash
set -uo pipefail

INPUT=$(cat 2>/dev/null || true)
[ -z "$INPUT" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY=$(command -v python3 || command -v python || true)
[ -z "$PY" ] && exit 0

read -r TRANSCRIPT CWD SESSION_ID <<EOF
$("$PY" -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("transcript_path", ""), d.get("cwd", ""), d.get("session_id", ""))
except Exception:
    print("", "", "")
' <<<"$INPUT")
EOF

[ -z "${TRANSCRIPT:-}" ] && exit 0
[ -f "$TRANSCRIPT" ] || exit 0
[ -z "${CWD:-}" ] && exit 0
[ -z "${SESSION_ID:-}" ] && exit 0

"$PY" "$SCRIPT_DIR/harness.py" digest \
    --transcript "$TRANSCRIPT" \
    --cwd "$CWD" \
    --session-id "$SESSION_ID" >/dev/null 2>&1 || true

exit 0
