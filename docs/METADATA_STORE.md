# PageDoctor — What the database holds (and what it must not)

The store holds two kinds of data: **metadata** (ids, hashes, settings, counts, timestamps) and,
since the owner decision of 2026-07, **findings** — the suggestions/corrections Sophie produces —
kept **encrypted at rest**. The whole manuscript is still never stored. This note is the reference
for where the line is.

The governing rule is CLAUDE.md §9 (amended). The DB is now the **source of truth for findings**;
the comments Sophie posts remain the **creator-facing view** (non-BookHub accounts read findings in
the Google Doc).

## The line: what may and may not be stored

| May be stored | Must never be stored |
|---|---|
| Google doc id, Drive `revisionId` | The **whole manuscript** / chunk body text |
| Timestamps, review settings, counts | Anything derived from the manuscript **in plaintext** |
| One-way hashes (chunk hashes, finding keys) | A finding logged to the structured logs (§9.5) |
| Findings — quote, proposed change, reason — **encrypted** | — |

Storing a finding is allowed (encrypted, on purpose). **Logging** a finding is still a defect. And
the full document text never touches disk — it lives in memory only for the duration of a run.

## Tables

- **`review_runs`** — run metadata: id, doc id, config, status, timestamps, finding count,
  correlation id, posted-finding key hashes. No content.
- **`doc_review_states`** — per-document change-detection: `revision_id`, `chunk_hashes` (one-way
  hashes), the last `config`, `updated_at`. Powers incremental review. No content.
- **`findings`** — the one content table. `original_text`, `proposed_change`, `reason_de` are
  **Fernet ciphertext** (never plaintext); `category`, `priority`, `status` are enums; `key` is a
  hash; `comment_id` is an opaque Drive id; plus `run_id` and timestamps. Composite PK
  `(doc_id, key)`.

## Encryption at rest

Finding text is encrypted at the persistence boundary (`adapters/persistence/crypto.py`,
`FindingCipher`), so **ciphertext never crosses a domain port** — the domain and every port handle
only plaintext `StoredFinding` models. The key is `FINDING_ENCRYPTION_KEY` (a Fernet key), a
**required** setting: the app refuses to boot without it (fail-fast, §5.12), so findings can never
be written unencrypted by accident. A live adapter test asserts the plaintext is absent from the raw
column.

## Lifecycle

- On each review, the orchestrator posts comments, then reads them back (they carry the real Drive
  comment ids), and persists each finding to the DB (`status = open`). Re-reviews are idempotent —
  an already-stored finding keeps its status (an applied/dismissed one never reverts to open).
- The sidebar reads findings straight from the DB (no re-parsing of comment text).
- **Apply / dismiss** flips the finding's status (`applied` / `dismissed`) and resolves the Drive
  comment. A finding whose quote no longer appears is marked `obsolete` and its comment resolved.
- **TTL:** findings are purged `FINDINGS_TTL_DAYS` (default 90) after they were last touched, so
  stored excerpts don't linger indefinitely.

## Hosting note

On the current single VPS the disk is not encrypted at the block level, which is why finding text is
encrypted at the **application** layer regardless of host. For real production this should move to a
managed encrypted database (e.g. RDS with KMS + automated backups + PITR); the app-level encryption
then stacks on top. See the deploy runbook.
