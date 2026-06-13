# PageDoctor — Feasibility: What Google Docs Lets Us Do (and Not)

> **Why this doc exists.** The approved spec assumes PageDoctor writes **native suggestions** (tracked changes) into the creator's Google Doc via a service account, using `documents.batchUpdate` with `SuggestInsertText` / `SuggestDeleteText`. **That capability does not exist.** This document states what is actually possible, what is not, and the workaround we propose. It supersedes the optimistic technical assumptions in the team feedback (§9) and the original context doc.

---

## The verified finding

A server-side application using a Google **service account cannot create suggestions** (suggesting-mode / tracked-changes edits) in a Google Doc. Google states it plainly:

> "You can use the API to **view** suggestions, but **not programmatically accept, reject, or create them**."
> — [Google Docs API — Work with suggestions](https://developers.google.com/workspace/docs/api/how-tos/suggestions)

- `SuggestInsertTextRequest` / `SuggestDeleteTextRequest` **do not exist**. There is no request type with "Suggest" in its name in the entire `batchUpdate` API. ([Request reference](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/request))
- Every `batchUpdate` write is a **direct edit**, committed as the service-account user. A deletion really deletes; there is no "reject" affordance.
- This is **not on Google's roadmap** as of June 2026. Treat it as permanent.

How third-party tools (Grammarly, etc.) show "suggestions" in Google Docs: they **don't use the API** — they run a **client-side browser extension** that overlays its own UI on the rendered editor. Their suggestions are not native Docs tracked-changes either. ([Grammarly Engineering](https://www.grammarly.com/blog/engineering/making-grammarly-feel-native-on-every-website/))

---

## Capability matrix

| Capability | Possible server-side (service account)? | Notes |
|---|---|---|
| **Read** the document text + structure with exact indices | ✅ Yes | `documents.get` |
| **Read** existing suggestions | ✅ Yes | `suggestionsViewMode`: `SUGGESTIONS_INLINE`, `PREVIEW_SUGGESTIONS_ACCEPTED`, `PREVIEW_WITHOUT_SUGGESTIONS`; fields `suggestedInsertionIds`, `suggestedDeletionIds`, `suggestedTextStyleChanges` |
| **Make direct edits** (insert/delete/replace/style text) | ✅ Yes | `batchUpdate` — but these are *direct*, not suggestions; they mutate the manuscript |
| **Create native suggestions** (tracked changes) | ❌ **No** | Not supported by any API. The core spec assumption. |
| **Accept / reject** suggestions | ❌ No | Not supported |
| **Create comments** on a Doc | ✅ Yes | Drive API `comments.create` |
| **Anchor a comment to a specific text span** | ⚠️ **Effectively no** | The `anchor` field is accepted and stored, but "Google Workspace editor apps treat these comments as **un-anchored** comments." ([Drive — Manage comments](https://developers.google.com/workspace/drive/api/guides/manage-comments)) Comments land at the document level, not pinned to the span. |
| Apps Script `DocumentApp` create suggestions | ❌ No | Same backend limit; Apps Script/add-ons gain nothing here |

**Two hard limits to internalize:** (1) no native suggestions server-side, and (2) API comments can't be visually pinned to a text span.

---

## What this breaks in the approved spec

- "Suggestions exactly as from a human editor… accept/reject is a native Google Docs function" — **not achievable server-side.**
- "Insert suggestions via `documents.batchUpdate` with `SuggestInsertText` / `SuggestDeleteText`" (§9) — **those calls don't exist.**
- "Color coding" of proofreading vs. editing as native suggestion colors — **not achievable** (no suggestion objects to color).

Everything else in the spec stands: the internal PM UI, the Sophie Hoffmann persona, the two check modes, configuration, the AI engine, the workflow, the data-protection rules. **Only the output mechanism into the doc changes.**

---

## The workaround options

### Option A — Browser automation drives the Docs UI in Suggesting mode
A headless browser (Playwright/Puppeteer) signs in as a **real "Sophie Hoffmann" Google account** (not a service account), opens the doc in **Suggesting mode**, and types the edits — producing **genuine native suggestions** with native accept/reject and proper anchoring.

- ✅ Delivers the exact promised UX — the only option that does.
- ✅ Can also place properly **anchored** comments through the same UI.
- ❌ Brittle: breaks when Google changes the Docs DOM/UI. A known-working but "imperfect and a little brittle" approach in the wild.
- ❌ Automating the Docs UI is a **Google ToS gray area**; risk of the Sophie account being flagged/locked.
- ❌ Slower; needs a logged-in session; more moving parts to maintain.
- ⚖️ Mitigated by the fact that this is an **internal, low-volume tool** (a PM runs it per manuscript), so slowness and occasional breakage are tolerable, and the automation surface can be kept thin and well-isolated.

### Option B — Comments-only, via the Drive API (no edits to the manuscript)
Sophie never touches the text. For each finding she posts a **comment** containing: the exact quoted original text, the problem, the proposed replacement, the category (proofreading/editing), and the priority (`[FEHLER]`/`[EMPFEHLUNG]`/`[HINWEIS]`). The consistency report is one summary comment.

- ✅ Fully supported, robust, server-side, no ToS risk, no brittleness.
- ✅ **Never mutates the manuscript** — the creator's text stays pristine; the creator applies every change themselves (very on-brand for "the creator decides").
- ❌ Comments are **unanchored** — they appear in the comment stream, not pinned to the span. The quoted text lets the creator locate the spot, but it's more scrolling on a long book.
- ❌ No one-click accept/reject — the creator edits manually.

### Option C — Direct edits styled to look like tracked changes (insert colored, delete struck-through) + comments
- ❌ **Not recommended.** It mutates the manuscript, real deletions are destructive, there's no clean "reject," and it pollutes the document. Strictly worse than B for an editing tool whose whole point is that the creator decides.

---

## ✅ Decision (made June 2026)

**v1 ships as Option B — comments-only via the Drive API.** Sophie never edits the manuscript; she posts structured comments and the creator applies changes themselves. The output layer is built **behind a swappable adapter interface** so that **Option A (browser automation for native suggestions) can be added later** as an upgrade without touching the AI engine, persona, modes, or config. We start safe and robust, and improve the UX over time.

Implications the next AI should treat as settled:
- Build the **output adapter as a clean interface** with one implementation (`CommentsOutput`) for v1; do not hard-wire comment logic into the engine.
- The AI engine, Sophie persona, two check modes, configuration, and workflow are **identical** regardless of adapter — build them once.
- "Color coding" of proofreading vs. editing is expressed **in the comment text** for v1 (e.g. a category tag / prefix), since there are no suggestion objects to color. See `PAGEDOCTOR_CONTEXT.md` §13.
- Each comment must carry enough to be useful while unanchored: the **exact quoted original text**, the problem, the proposed replacement, the category (proofreading/editing), and the priority (`[FEHLER]`/`[EMPFEHLUNG]`/`[HINWEIS]`).
- The manuscript is **never mutated** in v1 — a property worth preserving as a feature ("the creator decides").

---

## Recommendation (the reasoning behind the decision above)

**Primary: Option A (browser automation in Suggesting mode), because it is the only option that preserves the native accept/reject UX that was the entire reason to choose Google Docs in the first place.** Without native suggestions, the original rationale ("creators already know this, accept/reject is native, no UI to build") only half-holds. Keep the automation layer thin, isolated behind one interface, and treat it as the component most likely to need repair. Use a dedicated Sophie Hoffmann **user account**, not a service account.

**Robust fallback: Option B (comments-only)** if the team judges the ToS/reliability risk of UI automation unacceptable for a production workflow. It's the safe, boring, always-works choice. It trades UX fidelity (unanchored, manual apply) for zero brittleness and zero ToS exposure — and it has the virtue of never altering the manuscript.

**A pragmatic path:** ship **Option B first** (small, robust, proves the AI editing quality — which is the actual hard/valuable part), then add **Option A** as an output adapter once the editing engine is solid. The AI engine, persona, modes, and config are identical for both; only the "write to doc" adapter differs. Designing that adapter as a swappable interface from day one lets us start safe and upgrade the UX later without rework.

---

## Settled — and what's deferred to the Option A upgrade

The output-mechanism question is **decided** (Option B for v1; see the Decision section above). The following are explicitly **deferred** until Option A is built, and are out of scope for v1:

- Native one-click accept/reject UX
- Anchored, span-pinned suggestions
- Browser-automation infrastructure, the dedicated Sophie Hoffmann *login* account, and the associated ToS gut-check

For v1, Sophie uses a **service account** (comments + read access only), not a login account — which sidesteps the ToS question entirely until/unless Option A is taken on.

---

## Sources

- [Google Docs API — Work with suggestions](https://developers.google.com/workspace/docs/api/how-tos/suggestions) — "view… but not programmatically accept, reject, or create them"
- [Docs API — Request reference](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/request) — full list of `batchUpdate` request types (no Suggest*)
- [Docs API — documents.get](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/get) — `suggestionsViewMode`
- [Drive API — Manage comments and replies](https://developers.google.com/workspace/drive/api/guides/manage-comments) — anchor field + "treated as un-anchored" caveat
- [Apps Script — DocumentApp](https://developers.google.com/apps-script/reference/document/document-app) — direct-edit only
- [Grammarly Engineering — Making Grammarly feel native](https://www.grammarly.com/blog/engineering/making-grammarly-feel-native-on-every-website/) — client-side extension, not the API
- [Andy Bromberg — browser automation for AI edits in Docs](https://andybromberg.com/interface0-google-docs) — real-world Option A account
