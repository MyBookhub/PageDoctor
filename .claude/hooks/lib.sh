#!/usr/bin/env bash
# Shared helpers for PageDoctor Claude Code hooks.
# Every hook degrades gracefully: if a tool isn't installed yet (the project is
# scaffolded by issue #2), the resolver returns empty and the caller no-ops.

# Resolve a CLI tool, preferring the project virtualenv over a global install.
# Usage: bin="$(find_tool ruff)"; [ -n "$bin" ] && "$bin" ...
find_tool() {
  local tool="$1" root="${CLAUDE_PROJECT_DIR:-$PWD}" candidate
  for candidate in "$root/.venv/bin/$tool" "$root/venv/bin/$tool"; do
    if [ -x "$candidate" ]; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  command -v "$tool" 2>/dev/null || true
}

# Read the edited file path from a PostToolUse hook payload on stdin.
# Echoes the path (or nothing). Requires jq.
edited_file_path() {
  local payload="$1"
  printf '%s' "$payload" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true
}

# True if the given path is a Python file that exists on disk.
is_existing_py() {
  case "$1" in
    *.py) [ -f "$1" ] ;;
    *) return 1 ;;
  esac
}
