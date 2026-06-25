# Google Docs Add-on — Setup & Handoff (Issue #13, Option 1)

> Records the Google-side provisioning done for the post-v1 in-Docs UX, and what is handed
> off to development. This is an ops/handoff note — the source of truth for *what PageDoctor
> is* remains the three handoff docs and `docs/PAGEDOCTOR_FEASIBILITY.md`.

## Context

[Issue #13](https://github.com/MyBookhub/PageDoctor/issues/13) chose **Option 1 — a Google Docs
Editor Add-on (Apps Script)** as the path to a better, anchored-feeling review UX on top of the
v1 comments-only output. Scope is **internal only**: BookHub project managers run it; external
creators do not install anything. The add-on gives a sidebar with **jump-to-quote → highlight →
apply-fix**. It does **not** create native tracked suggestions — `apply` is a user-triggered
direct edit (see `docs/PAGEDOCTOR_FEASIBILITY.md`).

## What was provisioned (Google side)

| Item | Value / state |
|---|---|
| Google Cloud project | `internal-proofreading-bookhub` |
| OAuth consent screen (Google Auth Platform) | **External + Testing** for development; **Gustavo added as Test user**. Will be flipped to **Internal** for the PM rollout. |
| Apps Script project | Created and linked to the GCP project (via project number). [Open project](https://script.google.com/d/1XMx6xGVoJG-zSWDXDu3HphKc5C1DSp0-2VQXmdyfkL5s1I3p2smZ2-Qa/edit) |
| Sharing | Apps Script project + a **synthetic** test doc shared with Gustavo as **Editor** (Drive-level, not GCP IAM). |

Test content is **synthetic German only** — never real creator manuscripts (§9 / §11).

## OAuth scopes the add-on uses

- `documents.currentonly` — read/edit only the document the add-on is open in (single-doc scope).
- `script.container.ui` — show the sidebar / menu.
- `script.external_request` — *added later*, only when the add-on fetches real findings from the backend.

## Handoff — what's next

- **Gustavo (add-on code):** build the sidebar + `jump-to-quote` (`setSelection`) and `apply-fix`
  (`replaceText`) in the linked Apps Script project. Quotes are re-located fresh in the live doc
  (`findText`) — never trust stored offsets.
- **Backend (PageDoctor):** a **§9-clean findings endpoint** for the add-on to fetch a doc's
  findings as JSON — must **not** store finding/manuscript content; re-derive transiently from the
  comments Sophie already posted (comment ids known via `ReviewRun` + the idempotency checkpoint).

## Notes & caveats

- **Testing mode:** external test-user refresh tokens expire after **7 days** → periodic
  re-authorization during development. The "unverified app" warning on authorization is expected.
- **Rollout:** flip the consent screen **External → Internal** (PMs only, no verification needed).
  For domain-wide install, publish privately via the Google Workspace Marketplace SDK.
- **Do not switch the linked GCP project** later — it forces re-authorization for all users.
- **Validation status:** infrastructure/access only (Gustavo can open the project + test doc and
  authorize). Functional validation follows once the add-on code exists.
