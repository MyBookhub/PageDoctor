# PageDoctor — Context & Handoff

> **Purpose of this document.** This is the complete context for the AI that will plan and build PageDoctor. It is **context, not a plan** — it does not decide architecture, model choice, or task breakdown. Those are the next AI's job. Read this end to end before planning. Where something is undecided, it is called out explicitly in *Open Questions* (§13) — do not silently invent answers; ask.
>
> **Source of truth.** The approved spec is the Publishing Team feedback (June 2026), reproduced and expanded below. Where the original proposal and the feedback disagree, **the feedback wins**. The two PDF proposals in the repo (`PROPOSAL_PAGEDOCTOR.pdf`, plus `PROPOSAL.pdf` for the sister project CoverCraft) are historical and partly superseded.

---

## 1. One-paragraph essence

PageDoctor is the **AI editing stage** inside BookHub's book-production pipeline. A BookHub project manager pastes a link to the creator's manuscript (a Google Doc) into a minimal internal web app, picks a check mode and settings, and clicks "Review." An LLM proofreads and/or copy-edits the whole manuscript and writes its findings **directly into the creator's Google Doc** — as inline suggestions plus margin comments — under the identity of a fictional human editor named **Sophie Hoffmann**. The creator then opens their familiar Google Doc and accepts, rejects, or counter-comments each suggestion using native Google Docs features. PageDoctor does **not** replace the human editor; it does the heavy first pass so the human editor can focus on fine polish.

The pipeline position is fixed:

```
Manuscript ready → PageDoctor (AI editing) → Human proofreading → Print approval
```

---

## 2. Company context (background — read once)

**BookHub** (mybookhub.de) is a small German **Print-on-Demand publishing platform**, founded July 2023 (Bookhub by Muthu GmbH, Bad Vilbel). Founders: Tillmann Durth (MD) and Julia Lantelme (CEO). Team is ~4–10 people. The developer building PageDoctor is BookHub's backend engineer; **this is a solo summer side-project**, intended to live in its **own standalone codebase**, not in BookHub's main `aws-eda-backend` monorepo (where these context files currently sit only because that's where the brainstorm happened).

**Positioning — "Der Creator-First Verlag."** BookHub deliberately does *not* chase hobby novelists (that's KDP/BoD territory). It serves **creators who already have an audience** — YouTubers, Instagrammers, niche experts — who want to turn that audience into a physical book without losing their brand or customer data. Flagship case: the creator *Nicolnic* sold 10,000+ copies of a cookbook in two months through BookHub.

**Why this matters for PageDoctor:**
- The manuscripts are **creator content**, skewing to **cookbooks, advice/non-fiction, lifestyle, memoir, children's books** — not just fiction. This is exactly why the spec has per-book-type behavior and a dedicated recipe mode (§7).
- The audience is **German**, the books are **in German**, and quality matters because a creator's existing fans are the first, harshest readers.
- BookHub is small and high-touch; an internal tool that lets one project manager do a professional first-pass edit in minutes is real leverage.

This section is background. The operative requirements are §§3–12.

---

## 3. Architecture: minimal internal UI + Google Docs as the channel

This is the single biggest change from the original proposal. **There is no creator-facing app.** PageDoctor is two parts:

### Part 1 — Project Manager UI (internal web app)
A simple single-page internal tool for the BookHub team only. No creator ever sees it. It is essentially **one form, one button, one progress indicator**. The project manager:
- Pastes a Google Docs link
- Selects check mode (proofreading / editing / both)
- Configures book type, language, strictness, custom dictionary, recipe mode
- Clicks "Review"
- Watches analysis progress
- Optionally removes unsuitable suggestions in the doc afterward
- Can start a **second pass** after the creator has reviewed

### Part 2 — Output written into the creator's Google Doc
The AI writes its findings into the doc via the **Google Docs / Drive APIs**, as **suggestions** (tracked changes) plus **comments**, under the **Sophie Hoffmann** service-account identity. The creator opens their own doc and reviews exactly as if a human editor had gone through it.

**Why this design (per the team):** creators already live in Google Docs; accept/reject and commenting are native; no custom frontend, comment system, auth, or share-links to build; far less development effort.

---

## 4. The two roles

| Role | Sees | Does |
|---|---|---|
| **Project Manager** (BookHub-internal) | The internal UI **and** the Google Doc | Pastes link, picks mode/settings, starts analysis, optionally prunes suggestions, tells the creator it's ready, starts second pass or hands to human editor |
| **Content Creator** | **Only** their Google Doc | Opens the doc, sees Sophie's suggestions + comments, accepts/rejects (native), writes counter-comments (e.g. *"Ich möchte es lieber so: …"*), marks done |

---

## 5. The two check modes (selectable individually or combined)

| Mode | What it checks | Color coding | Example |
|---|---|---|---|
| **Proofreading** (Korrektorat) | Spelling, grammar, punctuation, typos | One color (e.g. red/orange) | "Rezpet" → "Rezept" |
| **Editing** (Lektorat) | Style, consistency, repetition, phrasing, readability | A different color (e.g. blue/purple) | "Das ist ein Rezept was gut schmeckt" → "…das gut schmeckt" |

The distinct colors let the creator tell at a glance whether something is a hard error (proofreading) or a stylistic recommendation (editing). The color is conveyed in the comment/labeling — see §13 for the open question of how "color" is actually expressed through the Docs API.

---

## 6. The AI persona: Sophie Hoffmann

The AI must **never** present itself as "AI" or "PageDoctor." All output appears as **Sophie Hoffmann**, a fictional German editor.

- The Google service account is set up as "Sophie Hoffmann" with a professional avatar.
- Every suggestion and comment appears under this name in the doc.
- Comment tone is a **friendly, competent human editor** writing **in German**.
  - Good: *"Hier fehlt ein Komma vor dem Relativsatz."*
  - Bad: *"GRAMMATIK-FEHLER ERKANNT"*
- **Rationale (psychological):** "Sophie has 47 improvement suggestions for you" lands very differently from "An AI found 47 errors."

**Language rule:** this spec is in English, but **everything Sophie writes in the doc must be in German** — that is the language creators write and read in.

---

## 7. What appears in the Google Doc

**Suggestions (suggestion mode):** every correction is a Google Docs suggestion — original struck through, proposed change beside it.

**A comment on every suggestion**, containing:
- A one-sentence reason (e.g. *"Komma vor Relativsatz"* or *"Dieses Wort kommt 4x in diesem Absatz vor"*)
- Category: proofreading or editing
- Priority label:

| Level | Label | Meaning |
|---|---|---|
| Error | `[FEHLER]` | Definitely wrong — should be corrected |
| Recommendation | `[EMPFEHLUNG]` | Not wrong, but improvable |
| Note | `[HINWEIS]` | Pure style, optional |

**Consistency report:** a summary at the end of the doc (or as a comment at the top) listing inconsistent terms, spelling variants across the whole book, and repetition statistics per chapter.

---

## 8. Check categories

### Proofreading (finding errors)
| Category | Checks | Example |
|---|---|---|
| Spelling | Typos, transposed letters | "Rezpet" → "Rezept" |
| Grammar | Sentence structure, case, conjugation | "dem Creator" → "den Creator" |
| Punctuation | Commas, quotation marks, periods | Missing commas in relative clauses |
| Consistency | Names, terms, spellings **across the whole book** | "Basilikum" vs. "Baslikum" |

### Editing (improving style)
| Category | Checks | Example |
|---|---|---|
| Phrasing | Clumsy/unclear sentences, better alternatives | "Das ist ein Rezept was gut schmeckt" → "…das gut schmeckt" |
| Repetition | Same words in close succession, filler words | "lecker" 4× in one paragraph |
| Readability | Over-long / hard sentences | Flag sentences over ~40 words |

---

## 9. Configuration (the Project Manager form)

- **Google Docs link** (text field)
- **Check mode:** proofreading only / editing only / both
- **Book type** (changes the AI's judgment):
  | Book type | Special considerations |
  |---|---|
  | Cookbook | Recipe mode available; quantity consistency; colloquial language generally OK |
  | Advice book | Factual tone, clear structure, more formal language |
  | Novel / Memoir | Colloquial language allowed in dialogue; check dialogue formatting |
  | Children's book | Simple language, short sentences preferred |
- **Strictness:** Light (only real errors) / Standard (errors + style, repetition, consistency) / Thorough (everything incl. readability, sentence length, phrasing alternatives)
- **Language variant:** German (Germany) / English (if needed) — **German is primary**
- **Custom dictionary:** PM-entered words Sophie must ignore — made-up names, brand names, dialect, deliberate spellings (e.g. "Schmackofatz")
- **Recipe mode** (cookbook-specific, additional checks):
  - Quantity consistency ("200g" vs "200 g" vs "200 Gramm")
  - Ingredients in the list reconciled against the body text
  - Temperature specs consistent (Ober/Unterhitze vs Umluft)
  - Serving sizes present
  - Consistent abbreviations (EL, TL, ml)

---

## 10. Workflow sequence (end to end)

1. PM opens the UI, pastes the Google Docs link.
2. PM selects check mode + settings.
3. PM clicks "Review."
4. Sophie analyzes the manuscript (progress visible in the UI).
5. Sophie writes suggestions + comments into the Google Doc.
6. PM checks the result, optionally removing unsuitable suggestions.
7. PM tells the creator (*"Dein Manuskript ist lektoriert, schau mal rein"*).
8. Creator opens the doc, sees the suggestions.
9. Creator accepts / rejects, commenting where needed.
10. Creator reports done to the PM.
11. *Optional:* PM starts a second pass.
12. Final manuscript goes to the human editor for final polish.

---

## 11. Technical notes (from the team)

**Google Docs / Drive API**
- A Google Cloud Console project with the Docs API **already exists and is enabled**.
- A **service account "Sophie Hoffmann"** with write access is to be used; it must be shared as **editor** on each target doc.
- Feedback's stated approach: insert suggestions via `documents.batchUpdate` (`SuggestInsertText` / `SuggestDeleteText`); insert comments via the Drive API (`comments.create`). **⚠️ See §12 — this specific capability must be verified before anything else is built.**

**AI engine**
- LLM-based, **chunk-wise** processing for long manuscripts.
- The **consistency check must work across the whole book**, not per chunk.
- **German proofreading must be excellent** — model choice matters.
- Output must reference **exact text positions** in the document so the Docs API can place suggestions correctly.

**Project Manager UI**
- Simple web app (Next.js or Flask — developer's choice).
- Internal only, not public.
- One form, one button, one progress indicator.
- Optional: a list of previous passes (which doc, when, which mode).

**Data protection (hard requirement)**
- Manuscripts are **unpublished, confidential** works.
- Manuscript text is used **only for the analysis**, **never stored** beyond the session.
- **No use of manuscripts for AI training** (rules out providers/settings that train on input).
- Google Docs access rights stay **minimal** — only the specific doc, never the whole Drive.

---

## 12. ⚠️ Critical risks (one is now RESOLVED — read `PAGEDOCTOR_FEASIBILITY.md`)

1. **Can the Google Docs API create *suggestions* (tracked changes)? — RESOLVED: NO. Output mechanism DECIDED.**
   Verified against Google's official docs: a server-side **service account cannot create suggestions**; the API can only *read* them and make *direct* edits. `SuggestInsertText`/`SuggestDeleteText` **do not exist**. API comments also **cannot be reliably anchored** to a text span. This breaks the spec's stated output mechanism (§9), but nothing else.
   **Decision (June 2026): v1 ships comments-only (Option B)** via the Drive API — Sophie posts structured comments (quoted original + proposed change + reason + category + priority), never edits the manuscript. Built **behind a swappable output adapter** so native-suggestion output via **browser automation (Option A)** can be added later without touching the engine. Full analysis, capability matrix, and the decision rationale are in **`PAGEDOCTOR_FEASIBILITY.md`** — read it before planning.

   The remaining risks below are still open and unverified.

2. **Exact-position mapping.** The Docs API addresses content by integer indices. The pipeline must read the document structure with its index map, extract plain text while preserving an index↔offset mapping, run the LLM, receive spans back, and translate them to precise ranges. LLMs do not natively emit character offsets reliably — design a robust matching strategy (e.g. quote-and-locate rather than trusting model-reported indices).

3. **Cross-chunk consistency on a whole book.** Chunk-wise LLM calls can't see the whole book at once, but consistency (names, terms, spelling variants, repetition stats per chapter) is explicitly required globally. Needs an accumulation strategy — e.g. a first pass that builds a glossary/term-frequency map, then a second that flags deviations.

4. **Document mutation between passes.** If the creator edits the doc before a "second pass," all indices shift. A second pass must re-read the doc fresh; it cannot reuse stale positions.

5. **German-language quality + no-training constraint together.** The chosen model must both proofread German at a professional level **and** run under terms that guarantee no training on input and no retention. These two constraints interact with model/provider choice — decide them together.

6. **Large-document API limits.** Whole books may hit Docs API request-size / rate limits and LLM context limits at once. Batching and pacing matter.

---

## 13. Open questions for the planning AI / the team

Resolve these before or during planning — **ask, don't assume**:

- **Model/provider choice** — which LLM proofreads German best under a no-training/no-retention guarantee? (Not yet decided.)
- **Hosting** — where does the internal UI + backend run? Any BookHub-preferred infra, or developer's choice since it's standalone?
- **Persistence** — the "list of previous passes" and any audit trail imply storage. What is stored, where, and for how long, given the "never store manuscript text" rule? (Likely: metadata only — doc id, timestamp, mode — never content.)
- **Internal-UI auth** — how do BookHub team members sign in? (Google Workspace SSO is the obvious fit but unconfirmed.)
- **Sync vs async** — a whole-book analysis is slow; is "Review" a long-running job with a progress feed? How is progress surfaced?
- **"Color coding" mechanics** — RESOLVED by the output decision: v1 has no suggestion objects to color, so proofreading-vs-editing is expressed **in the comment text** (a category tag/prefix). Revisit if/when Option A lands.
- **"Remove unsuitable suggestions" UX** — for v1 (comments-only) this is the PM deleting Sophie's comments directly in Google Docs; confirm whether any UI affordance is wanted.
- **Second-pass semantics** — re-analyze the whole doc, or only un-resolved regions? (Note: with comments-only, a second pass should also avoid re-posting comments the creator already resolved/deleted.)
- **Creator "mark as done"** — a message to the PM, a status in the doc, or out of scope for v1?
- **Where do these context/proposal files ultimately live** — confirm the build is a fresh standalone repo, separate from `aws-eda-backend`.

---

## 14. Phase 2 (explicitly out of v1 scope)

- Per-creator style dictionary (remember a creator's accepted spellings for future books)
- Automatic email to the creator when editing is finished
- Statistics dashboard (common error types per creator, accept/reject rates)
- Saved settings profiles per book type
- Version history / diff between passes
- Batch mode (multiple docs at once)
- Full audit trail of accepted/rejected suggestions via the Docs API

---

## 15. What changed vs. the original proposal (summary)

1. **No custom creator frontend** — output goes straight into the Google Doc.
2. **No custom comment system** — native Google Docs suggestions + comments.
3. **No auth/share-link system for creators** — docs are already shared.
4. **Minimal internal UI** — one form for the project manager.
5. **Two check modes** — proofreading vs. editing, color-coded, individual or combined.
6. **Sophie Hoffmann persona** — the AI appears as a fictional human editor.
7. **Creator can comment** — counter-suggestions directly in the doc.
8. **Configurability** — book type, strictness, language, custom dictionary, recipe mode.
9. **German as the primary language** — not English-first.
10. **Embedded in the BookHub process** — AI editing → human proofreading as a fixed workflow stage.
11. **Google Cloud project with Docs API already in place.**
