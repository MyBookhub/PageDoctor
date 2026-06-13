# PageDoctor

**AI editing for BookHub manuscripts — Sophie Hoffmann reads the book, the creator decides.**

PageDoctor is the AI editing stage in BookHub's book-production pipeline. A project manager points it at a creator's Google Doc; an LLM proofreads and copy-edits the whole manuscript in German and writes its findings back into that same doc as comments, under the identity of a fictional editor, **Sophie Hoffmann**. The creator reviews them natively in Google Docs. PageDoctor does the first pass; a human editor does the final polish.

```
Manuscript ready → PageDoctor (AI editing) → Human proofreading → Print approval
```

---

## Goals

- Give every BookHub manuscript a professional-grade first editing pass in minutes, not weeks.
- Let creators review in the tool they already use — Google Docs — with zero new app to learn.
- Free the human editor to focus on fine polish instead of catching obvious errors.
- Keep the creator in full control: nothing is changed without them — they apply, dismiss, or reply to every comment.

## Non-goals

- Not a replacement for the human editor.
- Not a creator-facing product — no public app, no creator login.
- Not a rewriting/ghostwriting tool — it suggests, it never silently changes the book.
- No developmental editing in v1 (pacing, structure, plot) — deferred.

---

## How it works

### Two parts

1. **Project Manager UI** — a minimal internal web app for the BookHub team. One form, one button, one progress indicator. Not public.
2. **Output in Google Docs** — Sophie's findings written into the creator's own doc as comments (v1) via the Drive API.

### Two roles

- **Project Manager** (internal): pastes the doc link, picks mode + settings, runs the analysis, optionally prunes weak comments, tells the creator it's ready, and can run a second pass.
- **Content Creator**: only ever opens their Google Doc, reads Sophie's comments, and applies / dismisses / replies to them natively.

### Two check modes (individual or combined)

| Mode | Checks | Example |
|---|---|---|
| **Proofreading** (Korrektorat) | Spelling, grammar, punctuation, typos | "Rezpet" → "Rezept" |
| **Editing** (Lektorat) | Phrasing, consistency, repetition, readability | "ein Rezept was gut schmeckt" → "…das gut schmeckt" |

---

## What lands in the doc

> **v1 output = comments only.** The Google Docs API cannot create native suggestions server-side (see `PAGEDOCTOR_FEASIBILITY.md`), so Sophie never edits the manuscript — she posts structured comments and the creator applies the changes. Native tracked-change suggestions are a planned later upgrade behind a swappable output adapter.

Each finding is a **comment** from Sophie containing:
- The **exact quoted original text** (so the creator can find the spot — comments are not pinned to the span)
- The **proposed change**
- A one-line German reason
- The **category** — proofreading or editing (conveyed in the comment text, since there are no suggestion colors in v1)
- A **priority label**:
  - `[FEHLER]` — definitely wrong, should be fixed
  - `[EMPFEHLUNG]` — not wrong, but improvable
  - `[HINWEIS]` — pure style, optional

Plus a **consistency report** comment: inconsistent terms, spelling variants across the whole book, repetition stats per chapter.

Everything Sophie writes is in **German**, in the warm, competent tone of a real editor — never "AI" language. The manuscript text is **never mutated** in v1 — the creator decides every change.

---

## Configuration (set by the project manager)

- **Check mode** — proofreading / editing / both
- **Book type** — Cookbook · Advice · Novel/Memoir · Children's (tunes the AI's judgment)
- **Strictness** — Light (errors only) · Standard (+ style, repetition, consistency) · Thorough (+ readability, sentence length, phrasing)
- **Language** — German (primary) · English (if needed)
- **Custom dictionary** — words Sophie must ignore (made-up names, brands, dialect, deliberate spellings)
- **Recipe mode** (cookbooks) — quantity consistency, ingredient-list ↔ body reconciliation, temperature/serving/abbreviation consistency

---

## Workflow

1. PM pastes the Google Docs link, picks mode + settings, clicks **Review**.
2. Sophie analyzes the manuscript (progress shown in the UI).
3. Sophie writes comments into the doc.
4. PM checks the result, optionally removes weak suggestions, tells the creator.
5. Creator reviews in Google Docs — accepts, rejects, counter-comments.
6. Optional second pass.
7. Final manuscript → human editor → print.

---

## Technical shape

**Build principle.** Production-ready technologies and sound patterns, scoped to exactly what this spec describes — neither bare-minimum-to-work nor over-built. The operator UI stays deliberately simple; the system behind it (manuscript handling, reliability, data protection) is production-grade. Scope is the publishing team's call; quality of what we build is ours.

**Stack (confirmed)**
- **All-Python.** **FastAPI** backend + **HTMX/Jinja** server-rendered operator UI — no separate frontend toolchain. The UI is one form, one button, one progress bar.
- **Pydantic** domain models; **hexagonal / ports-and-adapters** architecture. External concerns (output, LLM provider, document source, job runner) sit behind interfaces, so the domain core is testable with zero network.
- The **output adapter is the central seam**: v1 = comments via the Drive API; native-suggestion output (browser automation) slots in later without touching the engine.

**Persistence (confirmed)**
- **Postgres, metadata only** — reuses BookHub's existing Aurora/RDS ops and evolves cleanly into the Phase-2 features. **SQLite for local dev/tests**, behind a repository interface. Alembic migrations.
- **Never a column holding manuscript text or finding snippets** — store references and aggregate counts only.

**Jobs & progress (confirmed)**
- A whole-book pass runs for minutes → run it as a **durable, resumable async background job** with **SSE** progress (pairs natively with HTMX).
- **Idempotent posting** — a retry or restart must never double-post comments into an author's doc; a failed run fails cleanly, never leaving a half-edited doc.

**AI engine**
- LLM, chunk-wise over long manuscripts, with a **whole-book consistency pass**; excellent German required; uses **quote-and-locate** to map findings to exact text (never trusts model-reported offsets).

**Google integration**
- Existing Google Cloud project with Docs API enabled; **Sophie Hoffmann service account** (avatar set), shared as editor per doc. **Comments via the Drive API** (v1); document reads via the Docs API.

**Deployment (confirmed)**
- **Single container is the artifact.** Runs locally via **docker-compose** (app + local Postgres) as the primary dev loop; deploys to **AWS ECS Fargate + RDS/Aurora**, secrets in **Secrets Manager/SSM**. Actual AWS provisioning (Terraform/CDK) is deferred until deploy — the container is the contract, so the deploy decision never blocks development.

**Hard constraints (from the feedback — non-negotiable)**
- **Data protection.** Manuscripts are confidential, unpublished IP: analysis-only, **never stored**, **never logged** (not even in error traces), **never used for model training** (requires an LLM provider with contractual no-training / no-retention). Google access scoped to the single doc, never the whole Drive.
- **Never corrupt the author's doc.** Output lands in a real, shared document, so this is a decided requirement — **not** an open question:
  - **Idempotent posting** — checkpoint which findings have been posted so a retry or container restart never double-posts comments.
  - **Clean partial-failure** — a failed run marks the `ReviewRun` incomplete; it never leaves a half-commented doc presented as done.
  - **Durable, resumable job** — the analysis job survives a restart and resumes without re-posting (matches the Postgres-backed job decision).
  - **Second pass re-reads fresh** — the creator may have edited between passes; re-index from scratch, and don't re-post comments already resolved/dismissed.

---

## Validate before building

The concept hinges on a few unknowns. Spike these first:

1. **Native suggestions via the API — RESOLVED & DECIDED.** A server-side service account cannot create Google Docs suggestions; `SuggestInsertText`/`SuggestDeleteText` don't exist, and API comments can't be pinned to a span. **Decision: v1 ships comments-only (Option B)** behind a swappable output adapter; native-suggestion output (browser automation) is a later upgrade. See **`PAGEDOCTOR_FEASIBILITY.md`**.
2. **Exact-position mapping** — robustly translate LLM-found spans to Docs API index ranges (quote-and-locate, not model-reported offsets).
3. **Whole-book consistency** while processing in chunks (build a glossary/term map, then flag deviations).
4. **Second-pass re-read** — re-index from scratch; the creator may have edited between passes.
5. **German quality + no-training/no-retention** — choose the model under both constraints together.

See `PAGEDOCTOR_CONTEXT.md` for the full handoff, the verbatim team feedback, and the list of open questions to resolve with the team.

---

## Phase 2

Per-creator style memory · email notification when done · stats dashboard · saved settings profiles · version history between passes · batch mode · full accept/reject audit trail.
