---
name: github-subissues
description: Attach existing GitHub issues as native sub-issues of a parent (the structured "Sub-issues" panel with progress bar — not a markdown checklist). Use whenever the user asks for a parent feature issue with child / sub-issues, or says an issue tree "is not properly linked". `gh issue create` alone does NOT create the relationship; you must POST to the sub_issues REST endpoint with the child's internal `id` (not its `number`).
---

# GitHub Sub-Issues — the right way to link them

## The one rule everyone gets wrong

**`gh issue create` does not create sub-issue relationships.** Listing children as `- [ ] #123` in the parent body just renders task-list references. The native **Sub-issues panel** (with progress bar, collapsible tree, type=Task tagging) only shows up when you POST to a separate REST endpoint with the child issue's **internal `id`** — not its human-readable `number`.

Every time you create a parent + children with `gh issue create` and stop there, the user will rightly say "the sub-issues are not properly integrated". This skill exists so you don't make that mistake again.

## Endpoint

```
POST /repos/{owner}/{repo}/issues/{parent_number}/sub_issues
Body: {"sub_issue_id": <child_internal_id>}
```

- `parent_number` → the parent's human-readable issue number (e.g. `788`)
- `sub_issue_id` → the **child's `id` field** from the issue payload (a large integer like `4350446953`), **NOT** the child's `number`. Mixing these up is the #1 mistake.
- One POST per child. The endpoint is idempotent-ish: re-posting an already-attached sub-issue returns 422.
- Auth: needs `repo` scope on the GitHub token (the gh CLI default scope is fine).

## Standard flow

### 1. Create the parent issue

```bash
gh issue create --repo <owner>/<repo> \
  --title "..." \
  --label enhancement \
  --body "$(cat <<'EOF'
## Story
...
## Acceptance Criteria
- [ ] ...
EOF
)"
# → returns https://github.com/.../issues/788
```

Capture the parent number (`788`).

### 2. Create the child issues

Same `gh issue create` for each child. Capture each issue **number** as you go:

```bash
gh issue create --repo <owner>/<repo> --title "Child A" --body "Parent: #788\n..."
# → 789
gh issue create --repo <owner>/<repo> --title "Child B" --body "Parent: #788\n..."
# → 790
# ...
```

A `Parent: #<num>` line in the body is nice-to-have for readers, but the actual relationship comes from step 4.

### 3. Look up the children's internal IDs

`gh issue create` returns the URL only — you must fetch the `id` field separately:

```bash
for n in 789 790 791 792 793; do
  gh api "repos/<owner>/<repo>/issues/$n" --jq '{number, id, title}'
done
```

Output:
```json
{"id":4350446953,"number":789,"title":"Child A"}
{"id":4350448002,"number":790,"title":"Child B"}
...
```

The `id` is the value you need next. Do **not** use `number`.

### 4. Attach each child as a sub-issue

```bash
for id in 4350446953 4350448002 4350449220 4350450326 4350451160; do
  gh api -X POST "repos/<owner>/<repo>/issues/788/sub_issues" \
    -F sub_issue_id=$id --jq '.number'
done
```

Each call returns the parent's number on success. Do them sequentially (not in parallel) — there's no documented race condition, but ordering preserves the order they appear in the panel.

### 5. Verify

```bash
gh api "repos/<owner>/<repo>/issues/788/sub_issues" --jq '.[] | {number, title}'
```

You should see all children listed. If the panel still looks empty in the GitHub UI, hard-refresh the page — the sub-issues panel is sometimes cached.

## Doing it in one shot — recommended pattern

When creating a tree from scratch, capture numbers as you go and run all attaches at the end. Example for a parent with 9 children:

```bash
PARENT=$(gh issue create --repo MyBookhub/aws-eda-backend \
  --title "Feature X" --label enhancement --body "..." | tail -1 | grep -oE '[0-9]+$')

CHILD_NUMBERS=()
for title in "Child 1" "Child 2" "Child 3"; do
  url=$(gh issue create --repo MyBookhub/aws-eda-backend \
    --title "$title" --body "Parent: #$PARENT")
  CHILD_NUMBERS+=( "$(echo "$url" | grep -oE '[0-9]+$')" )
done

for n in "${CHILD_NUMBERS[@]}"; do
  id=$(gh api "repos/MyBookhub/aws-eda-backend/issues/$n" --jq .id)
  gh api -X POST "repos/MyBookhub/aws-eda-backend/issues/$PARENT/sub_issues" \
    -F sub_issue_id=$id --jq '.number'
done
```

In Claude Code: write the parent + children with `gh issue create`, then a single batch loop calling the sub_issues endpoint.

## Other operations on the relationship

### Re-order sub-issues

```
PATCH /repos/{owner}/{repo}/issues/{parent}/sub_issues/priority
Body: {"sub_issue_id": <id>, "after_id": <id_to_place_after>}
```

`after_id: 0` (or omitted) puts it first.

### Detach a sub-issue

```
DELETE /repos/{owner}/{repo}/issues/{parent}/sub_issues
Body: {"sub_issue_id": <id>}
```

Removes the child from the parent's tree but keeps the issue itself.

### List sub-issues of a parent

```
GET /repos/{owner}/{repo}/issues/{parent}/sub_issues
```

Returns the children in their tree order.

### List parents of a child (issues with this as a sub-issue)

There is no "list my parents" endpoint. The relationship is one-way from the API. If you need it, search `is:issue` and parse the parent panel — but this is rare in practice.

## Pitfalls

1. **`number` vs `id` confusion.** The sub_issues endpoint wants the global `id` (large integer like `4350446953`), not the visible `#789`. Always fetch `id` via `gh api repos/.../issues/<n> --jq .id` before POSTing.
2. **`gh issue create --body` doesn't create relationships.** A `- [ ] #789` checklist in the body renders as a task list with progress, but it is **not** the same as the native Sub-issues panel. The user can tell — they'll say "not properly integrated".
3. **Cross-repo sub-issues are not supported.** Parent and child must be in the same repository.
4. **Limit: 100 sub-issues per parent, 8 levels deep.** Past these, the API returns 422. For huge feature trees, group into intermediate parents.
5. **422 on re-attach.** If a child is already a sub-issue of this parent (or another parent), re-POSTing returns 422. Detach first if you need to move it.
6. **Only `repo` scope is required**, but the token must have write access to the parent. PRs from forks can't attach.
7. **Don't rely on the body checklist for progress.** Once natively attached, GitHub renders a progress bar on the parent ("3/9 done") based on the children's open/closed state. The markdown checklist won't auto-update.
8. **Order of POSTs = order in panel.** Do them sequentially in the order you want users to see (typically dependency order).
9. **`gh issue edit --add-sub-issue` does not exist** as of this writing — you must use the `gh api` raw call. Don't waste time looking for a flag.
10. **The body of the parent can stay minimal.** Once children are attached natively, the panel is the source of truth. A redundant markdown list in the body is fine but optional — leave it out if you want a clean parent body.

## Quick reference — exact gh commands

```bash
# Create parent (capture number from URL)
gh issue create --repo OWNER/REPO --title "..." --body "..."

# Create child (do this N times)
gh issue create --repo OWNER/REPO --title "..." --body "Parent: #PARENT\n..."

# Get child internal id
gh api repos/OWNER/REPO/issues/CHILD_NUM --jq .id

# Attach child to parent
gh api -X POST repos/OWNER/REPO/issues/PARENT_NUM/sub_issues \
  -F sub_issue_id=CHILD_ID

# Verify
gh api repos/OWNER/REPO/issues/PARENT_NUM/sub_issues --jq '.[].number'

# Detach (rare)
gh api -X DELETE repos/OWNER/REPO/issues/PARENT_NUM/sub_issues \
  -F sub_issue_id=CHILD_ID

# Re-order (rare)
gh api -X PATCH repos/OWNER/REPO/issues/PARENT_NUM/sub_issues/priority \
  -F sub_issue_id=CHILD_ID -F after_id=OTHER_CHILD_ID
```

## Sources

- [GitHub REST API — Sub-issues](https://docs.github.com/en/rest/issues/sub-issues)
- [Sub-issues feature announcement (GitHub Changelog)](https://github.blog/changelog/2025-01-23-evolving-github-issues-public-preview/)
