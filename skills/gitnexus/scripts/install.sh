#!/usr/bin/env bash
set -euo pipefail

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found. Install Node.js 18+ first." >&2
  exit 1
fi

if command -v gitnexus >/dev/null 2>&1; then
  echo "gitnexus already installed: $(gitnexus --version 2>/dev/null || echo unknown)"
else
  echo "Installing gitnexus globally (skipping optional Dart/Kotlin/Swift/Proto grammars)..."
  GITNEXUS_SKIP_OPTIONAL_GRAMMARS=1 npm install -g gitnexus
fi

echo "Configuring MCP + skills + hooks for detected editors..."
gitnexus setup

echo "Smoke test:"
gitnexus --version

cat <<'EOF'

Done. Next:
  cd <any-git-repo> && gitnexus analyze            # graph only
  cd <any-git-repo> && gitnexus analyze --embeddings  # + semantic search
  bash scripts/index-workspace.sh <root> <group>   # index a whole workspace

To parse Dart/Kotlin/Swift too, reinstall WITHOUT GITNEXUS_SKIP_OPTIONAL_GRAMMARS
and with python3 + make + g++ present:
  npm install -g gitnexus
EOF
