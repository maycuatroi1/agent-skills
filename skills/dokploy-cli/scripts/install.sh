#!/usr/bin/env bash
# Idempotent one-shot installer for the dokploy-cli skill.
#
# Does:
#   1. Install/verify the official @dokploy/cli (npm i -g @dokploy/cli).
#   2. Verify dokploy credentials in ~/.omelet.json (dokploy_url + dokploy_api_key).
#   3. Add the `source export_dokploy_env.sh` line to the user's shell rc
#      (zsh and/or bash, whichever exist), only if not already present.
#   4. Smoke-test by exporting + calling `dokploy project all --json` if a key is set.
#
# Safe to re-run. Idempotent. Exits non-zero on any unrecoverable error.
#
# Usage:
#   bash ~/agent-skills/skills/dokploy-cli/scripts/install.sh

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPORT_SCRIPT="$SKILL_DIR/scripts/export_dokploy_env.sh"
OMELET_CONFIG="${OMELET_CONFIG:-$HOME/.omelet.json}"

bold()  { printf '\033[1m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }
red()   { printf '\033[31m%s\033[0m\n' "$*" >&2; }

# --- 1. npm package -----------------------------------------------------------

bold "[1/4] @dokploy/cli"
if ! command -v node >/dev/null 2>&1; then
  red "node not found. Install Node.js 18+ (nvm install --lts) then re-run."
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  red "npm not found. Comes with Node.js — fix Node install."
  exit 1
fi
if command -v dokploy >/dev/null 2>&1; then
  green "  already installed: $(dokploy --version 2>/dev/null || echo '?') at $(command -v dokploy)"
else
  echo "  installing @dokploy/cli globally..."
  npm install -g @dokploy/cli >/dev/null
  green "  installed: $(dokploy --version 2>/dev/null || echo '?')"
fi

# --- 2. Credentials -----------------------------------------------------------

bold "[2/4] credentials in $OMELET_CONFIG"
if [ ! -f "$OMELET_CONFIG" ]; then
  yellow "  $OMELET_CONFIG not found — create it with the credentials-utils skill:"
  echo "    python3 ~/agent-skills/skills/credentials-utils/scripts/add_credential.py dokploy_url"
  echo "    python3 ~/agent-skills/skills/credentials-utils/scripts/add_credential.py dokploy_api_key"
  CREDS_OK=0
else
  CREDS_OK=1
  for key in dokploy_url dokploy_api_key; do
    val=$(python3 -c "import json,sys; print(json.load(open('$OMELET_CONFIG')).get('$key',''))" 2>/dev/null || true)
    if [ -z "$val" ]; then
      yellow "  missing: $key  — add with:"
      echo "    python3 ~/agent-skills/skills/credentials-utils/scripts/add_credential.py $key"
      CREDS_OK=0
    else
      if [ "$key" = "dokploy_api_key" ]; then
        green "  $key=${val:0:8}...${val: -4}"
      else
        green "  $key=$val"
      fi
    fi
  done
fi

# --- 3. Shell rc --------------------------------------------------------------

bold "[3/4] shell rc"
RC_SOURCE_LINE="source $EXPORT_SCRIPT"
RC_COMMENT="# Dokploy CLI credentials from ~/.omelet.json"

add_to_rc() {
  local rc="$1"
  if [ ! -f "$rc" ]; then
    yellow "  $rc does not exist — skipping (create it first if you use this shell)"
    return
  fi
  # Match either absolute path or tilde-prefixed form to be idempotent across
  # past edits that may have used either spelling.
  if grep -Eq "(${HOME}|~)/agent-skills/skills/dokploy-cli/scripts/export_dokploy_env\.sh" "$rc"; then
    green "  $rc already sources export_dokploy_env.sh"
    return
  fi
  printf '\n%s\n%s\n' "$RC_COMMENT" "$RC_SOURCE_LINE" >> "$rc"
  green "  appended to $rc"
}

# Detect which rc files exist and add to all of them
ADDED_ANY=0
for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
  if [ -f "$rc" ]; then
    add_to_rc "$rc"
    ADDED_ANY=1
  fi
done
if [ "$ADDED_ANY" = "0" ]; then
  yellow "  no .zshrc or .bashrc found — add this line manually to your shell rc:"
  echo "    $RC_SOURCE_LINE"
fi

# --- 4. Smoke test ------------------------------------------------------------

bold "[4/4] smoke test"
if [ "$CREDS_OK" = "1" ]; then
  # shellcheck disable=SC1090
  eval "$(bash "$EXPORT_SCRIPT" --print)"
  if dokploy project all --json >/dev/null 2>&1; then
    count=$(dokploy project all --json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
    green "  dokploy project all → $count projects ✓"
  else
    red "  dokploy project all failed — check token validity / network"
    exit 1
  fi
else
  yellow "  skipped (creds not configured yet)"
fi

echo
green "Done. Open a new terminal (or 'exec \$SHELL') to pick up the shell rc change."
