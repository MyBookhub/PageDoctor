#!/usr/bin/env bash
# PostToolUse (Edit|Write|MultiEdit): when a file under domain/ changes, enforce
# hexagonal purity — the domain core may import only stdlib + Pydantic.
# Two layers: a fast inline import scan (works before any test exists) and the
# authoritative purity test once it lands.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$PWD}"
# shellcheck source=/dev/null
source "$root/.claude/hooks/lib.sh"

payload="$(cat)"
file="$(edited_file_path "$payload")"
[ -n "$file" ] || exit 0
case "$file" in
  *.py) ;;
  *) exit 0 ;;
esac
# Only the domain core is gated.
case "$file" in
  */domain/*|domain/*) ;;
  *) exit 0 ;;
esac

forbidden='^[[:space:]]*(import|from)[[:space:]]+(fastapi|starlette|anthropic|google|googleapiclient|google_auth|sqlalchemy|alembic|httpx|requests|aiohttp|psycopg|boto3)\b'
if [ -f "$file" ] && hits="$(grep -nE "$forbidden" "$file")"; then
  printf 'Hexagonal violation — domain/ may import only stdlib + Pydantic.\n%s\n%s\n\nMove this dependency into an adapter behind a port.\n' "$file" "$hits" >&2
  exit 2
fi

# Authoritative check when present.
pytest="$(find_tool pytest)"
purity_test="$root/tests/unit/test_domain_purity.py"
if [ -n "$pytest" ] && [ -f "$purity_test" ]; then
  if ! out="$("$pytest" -q "$purity_test" 2>&1)"; then
    printf 'Domain-purity test failed:\n%s\n' "$out" >&2
    exit 2
  fi
fi
exit 0
