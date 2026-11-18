#!/usr/bin/env bash
# PostToolUse hook: format the file Claude just edited.
# Python -> ruff format (backend venv), TS/TSX/JS/CSS/JSON -> prettier (frontend).
set -euo pipefail

file=$(jq -r '.tool_input.file_path // empty')
[[ -z "$file" || ! -f "$file" ]] && exit 0

root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

case "$file" in
  *.py)
    if command -v uv >/dev/null 2>&1; then
      (cd "$root/backend" && uv run --quiet ruff format "$file" >/dev/null 2>&1) || true
    fi
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.css|*.json)
    if [[ "$file" == "$root/frontend/"* && -x "$root/frontend/node_modules/.bin/prettier" ]]; then
      "$root/frontend/node_modules/.bin/prettier" --write --log-level silent "$file" || true
    fi
    ;;
esac
exit 0
