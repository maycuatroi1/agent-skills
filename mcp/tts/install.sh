#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Under Git Bash `pwd` yields /c/Users/... which MSYS rewrites only for arguments it
# passes straight to a native binary. Embedded in a longer string it survives verbatim
# and lands in the config as a path uv cannot open, so normalise it up front.
if command -v cygpath >/dev/null 2>&1; then HERE="$(cygpath -m "$HERE")"; fi
SERVER="$HERE/server.py"
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

# Env baked onto each entry rather than left to the shell: agent CLIs are often
# launched from a GUI that never sourced a profile, so an exported variable is not
# reliably there when the server starts.
ENV_KEYS=(EVO_TTS_PROVIDER EVO_TTS_VOICE EVO_TTS_VOICE_OPENAI EVO_TTS_VOICE_VBEE EVO_TTS_SPEED EVO_TTS_DIR)
CLAUDE_ENV=() CODEX_ENV=() EVO_ENV=() BAKED=()
for key in "${ENV_KEYS[@]}"; do
  value="${!key:-}"
  if [ -n "$value" ]; then
    CLAUDE_ENV+=(-e "$key=$value")
    CODEX_ENV+=(--env "$key=$value")
    EVO_ENV+=(--env "$key=$value")
    BAKED+=("$key=$value")
  fi
done
if [ ${#BAKED[@]} -gt 0 ]; then
  echo "Baking into each entry: ${BAKED[*]}"
else
  echo "No EVO_TTS_* set; entries use provider auto-detection."
fi

if command -v claude >/dev/null 2>&1; then
  claude mcp remove "$NAME" --scope "$SCOPE" >/dev/null 2>&1 || true
  # `claude mcp add` takes -e as a variadic flag, so the name must come before it or
  # it gets swallowed as another KEY=value.
  claude mcp add --scope "$SCOPE" "$NAME" "${CLAUDE_ENV[@]}" -- "${RUN[@]}" >/dev/null
  echo "Claude Code: registered '$NAME' ($SCOPE scope)."
else
  echo "Claude Code: \`claude\` not on PATH, skipped." >&2
fi

if command -v codex >/dev/null 2>&1; then
  codex mcp remove "$NAME" >/dev/null 2>&1 || true
  codex mcp add "$NAME" "${CODEX_ENV[@]}" -- "${RUN[@]}" >/dev/null
  echo "Codex: registered '$NAME'."
else
  echo "Codex: \`codex\` not on PATH, skipped." >&2
fi

if command -v evo >/dev/null 2>&1; then
  evo mcp add "$NAME" --opencode-only --force "${EVO_ENV[@]}" --command "${RUN[*]}" >/dev/null
  echo "OpenCode: registered '$NAME' (via evo, which owns the opencode.jsonc writer)."
else
  echo "OpenCode: \`evo\` not on PATH, skipped. Install it with: pip install evo_cli" >&2
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
