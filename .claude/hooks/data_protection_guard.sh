#!/usr/bin/env bash
# PostToolUse (Edit|Write|MultiEdit): tripwire for the two hard data-protection
# rules (CLAUDE.md §9): never log/print manuscript or finding text, and never
# widen Google access beyond the single shared doc.
# This is a fast heuristic, not a proof — it surfaces a line to review (exit 2),
# it does not block. The data-protection-auditor subagent does the deep pass.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$PWD}"
# shellcheck source=/dev/null
source "$root/.claude/hooks/lib.sh"

payload="$(cat)"
file="$(edited_file_path "$payload")"
[ -n "$file" ] || exit 0
is_existing_py "$file" || exit 0

warning=""

# 1) Logging or printing manuscript/finding content.
content_terms='manuscript|chunk_text|original_text|proposed_change|reason_de|comment_body|finding|suggestion|\.text\b|\bquote\b'
log_call='(logger?|logging)\.[a-z_]+\(|\bprint\('
if hits="$(grep -nIE "($log_call)[^)]*($content_terms)" "$file")"; then
  warning+="Possible manuscript/finding text in a log/print statement (never log content — §9):\n$hits\n"
fi

# 2) Google scope broader than single-doc (use per-doc sharing + drive.file — §8).
if hits="$(grep -nIE 'auth/drive([^.a-z]|$)|auth/drive\.readonly|auth/documents([^.a-z]|$)' "$file")"; then
  warning+="Google scope looks broader than single-doc access (§8):\n$hits\n"
fi

if [ -n "$warning" ]; then
  printf 'DATA-PROTECTION GUARD — review before continuing:\n%b\nIf this is a false positive, confirm no content is logged and proceed.\n' "$warning" >&2
  exit 2
fi
exit 0
