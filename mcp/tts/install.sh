#!/usr/bin/env bash
set -euo pipefail

SERVER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/server.py"
NAME="${EVO_TTS_MCP_NAME:-evo-tts}"
SCOPE="${EVO_TTS_MCP_SCOPE:-user}"

RUN=(uv run --script "$SERVER")
if [ -n "${EVO_TTS_PYTHON:-}" ]; then
  RUN=("$EVO_TTS_PYTHON" "$SERVER")
elif ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv not found. Install it: https://docs.astral.sh/uv/getting-started/installation/" >&2
  echo "       Or point at an interpreter that has evo_cli: EVO_TTS_PYTHON=\$(which python)" >&2
  exit 1
fi

SMOKE=("${RUN[@]}")
if [ -z "${EVO_TTS_PYTHON:-}" ]; then
  SMOKE=(uv run --refresh --script "$SERVER")
fi

echo "Smoke test (uv resolves evo_cli on first run)..."
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"install","version":"1"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | "${SMOKE[@]}" | tail -1

if command -v claude >/dev/null 2>&1; then
  claude mcp remove "$NAME" --scope "$SCOPE" >/dev/null 2>&1 || true
  claude mcp add --scope "$SCOPE" "$NAME" -- "${RUN[@]}"
  echo "Registered '$NAME' with Claude Code ($SCOPE scope)."
else
  echo "WARN: \`claude\` CLI not found. Register manually:" >&2
  echo "  claude mcp add --scope $SCOPE $NAME -- ${RUN[*]}" >&2
fi

cat <<EOF

Tools: speak, speak_batch, list_voices.

Credentials come from the omelet store, add at least one provider:
  evo cred add vbee.app_id --from-stdin     # https://studio.vbee.vn/apps
  evo cred add vbee.token --from-stdin
  evo cred add openai_api_key --from-stdin

Optional env overrides on the MCP entry:
  EVO_TTS_PROVIDER=vbee|openai|auto   EVO_TTS_VOICE=<code>
  EVO_TTS_SPEED=1.0                   EVO_TTS_DIR=<scratch audio dir>

uv resolves evo_cli from PyPI via the script's inline metadata. To run against a
local checkout instead (pip install -e /path/to/evo-cli first):
  EVO_TTS_PYTHON=\$(which python) bash mcp/tts/install.sh
EOF
