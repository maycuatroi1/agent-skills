#!/usr/bin/env bash
# Export DOKPLOY_URL + DOKPLOY_API_KEY from ~/.omelet.json so the official
# `@dokploy/cli` (and any other tool reading these env vars) picks them up.
#
# Usage in shell rc (~/.zshrc, ~/.bashrc):
#   source ~/agent-skills/skills/dokploy-cli/scripts/export_dokploy_env.sh
#
# Or one-off:
#   eval "$(bash ~/agent-skills/skills/dokploy-cli/scripts/export_dokploy_env.sh --print)"
#
# Reads from $OMELET_CONFIG if set, else ~/.omelet.json. Silent if file absent.

_dokploy_env_config="${OMELET_CONFIG:-$HOME/.omelet.json}"

if [ ! -f "$_dokploy_env_config" ]; then
  unset _dokploy_env_config
  return 0 2>/dev/null || exit 0
fi

_dokploy_env_get() {
  python3 -c "import json,sys; d=json.load(open('$_dokploy_env_config')); v=d.get('$1',''); print(v)" 2>/dev/null
}

_dokploy_env_url="$(_dokploy_env_get dokploy_url)"
_dokploy_env_key="$(_dokploy_env_get dokploy_api_key)"

if [ "$1" = "--print" ]; then
  [ -n "$_dokploy_env_url" ] && printf 'export DOKPLOY_URL=%q\n' "$_dokploy_env_url"
  [ -n "$_dokploy_env_key" ] && printf 'export DOKPLOY_API_KEY=%q\n' "$_dokploy_env_key"
else
  [ -n "$_dokploy_env_url" ] && export DOKPLOY_URL="$_dokploy_env_url"
  [ -n "$_dokploy_env_key" ] && export DOKPLOY_API_KEY="$_dokploy_env_key"
fi

unset _dokploy_env_config _dokploy_env_url _dokploy_env_key
unset -f _dokploy_env_get
