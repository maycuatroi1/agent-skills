#!/usr/bin/env bash
set -u

if [ "${CONTINUOUS_LEARNING_CHILD:-0}" = "1" ]; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config.json"
EXTRACTOR="$SCRIPT_DIR/extract_patterns.py"

INPUT="$(cat)"
if [ -z "$INPUT" ]; then
  exit 0
fi

CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty')"
TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty')"
SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty')"
STOP_ACTIVE="$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false')"

if [ -z "$CWD" ] || [ -z "$TRANSCRIPT" ] || [ -z "$SESSION_ID" ]; then
  exit 0
fi
if [ "$STOP_ACTIVE" = "true" ]; then
  exit 0
fi
if [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

LOG="/tmp/continuous-learning-${SESSION_ID}.log"
PROCESSED_DIR="$CWD/.claude/skills/learned/.processed"
if [ -f "$PROCESSED_DIR/$SESSION_ID" ]; then
  exit 0
fi

CONTINUOUS_LEARNING_CHILD=1 setsid nohup python3 "$EXTRACTOR" \
  --transcript "$TRANSCRIPT" \
  --cwd "$CWD" \
  --session-id "$SESSION_ID" \
  --config "$CONFIG" \
  >"$LOG" 2>&1 </dev/null &

disown || true
exit 0
