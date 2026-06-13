---
name: create-issue
description: Create a GitHub issue for the Bookhub backend project. Use when the user wants to create, draft, or write a GitHub issue.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, Agent
---

# Create GitHub Issue

## Project Context
- Repo: `MyBookhub/aws-eda-backend`
- Virtual env: `venv/bin/`

## Available Labels
| Label | Use for |
|---|---|
| `planned` | Future work, not yet scheduled |
| `enhancement` | New feature or improvement |
| `bug` | Something isn't working |
| `refactor` | Code quality / structural improvements |
| `migration` | Runtime, layer, or infrastructure migrations |
| `weekly_goal` | Planned for current week |
| `today` | In progress today |
| `priority` | High priority |
| `blocked` | Blocked by something |
| `documentation` | Docs improvements |

**Default label:** `planned` — unless the user specifies otherwise or the context clearly fits another label (e.g. `bug` for a defect, `refactor` for cleanup).

## Issue Template: Story with Acceptance Criteria

Always use this format:

```
## Story
As a [developer / user / ...], I want [goal], so that [benefit].

## Background
[Context, relevant file paths, code locations, why this matters. Implementation details belong here, not in the ACs.]

## Acceptance Criteria
- [ ] AC 1
- [ ] AC 2
- [ ] ...
```

## Language

**Write parent / feature issues in English** so they read naturally for the whole team and tooling. Child / implementation issues may use German if the parent is German, but default to English. The Story should always be in English for feature-level issues.

## Be terse — readers don't get paid to read

- **Story: 1–2 sentences.** No paragraphs.
- **Background: only what isn't obvious from the title.** A 3-line note is usually enough. Drop motivation that repeats the Story. Drop "why this matters" if the title already says it.
- **ACs: short, no filler.** Skip phrases like "with no manual intervention", "in a clear, actionable way", "actionable error rather than a silent zero", "without coordinating with another codebase". One observable behaviour per bullet, in plain language.
- **Don't restate the Story in the AC list.** If the Story says "drop the external call", don't also write an AC "the external call is dropped" plus three reworded variants.
- **Cut tables and prose unless they carry information that doesn't fit elsewhere.** A 3-row pricing-fields table can be worth keeping; a 6-row "supplier responsibilities" table that just lists the obvious is not.
- **Aim for issue bodies under ~150 words for child issues, under ~300 for parents.** If you exceed it, ask which bullet you can delete.

## Acceptance Criteria — observable, not implementation

ACs describe **practical, externally-observable outcomes** — what the system does, not how the code is shaped. A reviewer should be able to verify each AC by interacting with the deployed system or running an integration test, without reading the diff.

**Do not put in ACs:**

- Module / file / class / function names (`bookhub_price_model.py`, `update_product_pricing` handler, `PrintCostRepository`)
- Table or column names (`supplier.product_supplier.MarginNetto`, schema details)
- Event payload fields, listener Lambda names, EventBridge rule wiring
- "Stub raises NotImplementedError" or other interim code states
- SAM template snippets, IAM permissions, layer-deploy notes
- "Pattern follows X / mirrors Y" style references

**Do put in ACs:**

- Capabilities the system gains ("the system can compute production cost per supplier for a given set of specs")
- Behaviour visible at API / event boundaries ("a secured preview endpoint returns supplier costs for given specs")
- Data outcomes a stakeholder can verify ("when retail price changes, the per-supplier margin is re-computed automatically")
- Domain rules upheld ("supplier priority is not changed automatically by margin")
- Verification you can demo ("this is covered by integration tests against a deployed stack")

If you catch yourself writing a path or a class name in an AC, move it to Background. The ACs should still make sense if the architecture is rewritten.

**Feature vs. implementation issues:**
- Parent / feature issues — ACs are user / business / system-level. Implementation hints stay in Background.
- Child / implementation issues — ACs may include concrete files, tables, modules where useful, since the implementation itself is the deliverable. Even here, prefer outcome-oriented ACs and put exact paths in a "Files touched" sub-list under Background.

## Workflow

1. **Understand the topic** — if $ARGUMENTS is vague or missing context, explore the relevant code first (use Grep/Glob/Read/Agent to find file paths, classes, patterns).

2. **Draft the issue** — write title + body following the Story template. Include:
   - Concrete file paths and line numbers in Background where relevant
   - ACs that describe observable outcomes, not implementation steps (see "Acceptance Criteria" guidance above)
   - Suggest the appropriate label with brief reasoning

3. **Present to user for approval** — show the full draft (title, label, body). Ask if anything should be changed before creating.

4. **Create only after explicit approval** — run:
   ```bash
   gh issue create --title "..." --label "..." --body "..."
   ```
   Output the issue URL when done.

5. **Save useful discoveries to memory** — if you learned something structural about the codebase while researching (e.g. a pattern that's inconsistently applied, a file that's a central reference), update the memory file at:
   `.claude/projects/-Users-tillmanndurth-coding-projects-aws-eda-backend/memory/MEMORY.md`

## Input
$ARGUMENTS
