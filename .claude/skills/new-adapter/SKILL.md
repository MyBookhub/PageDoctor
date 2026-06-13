---
name: new-adapter
description: Scaffold a concrete adapter that implements a domain port (Google Docs source, comments output, Anthropic provider, Postgres repository, etc.), wire it into the composition root, write the raw↔domain mapping at the edge, and add a mocked-dependency test. Use when implementing a port against a real external system. Enforces the hexagonal / DI / no-leak rules.
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, Agent
---

# New Adapter

An adapter is the **only** place an external SDK is allowed. It implements a port and translates between the outside world and the domain (CLAUDE.md §2, §5.7).

## Before writing anything

1. **Run `pagedoctor-lookup`** for the port and for any model the mapping needs — don't recreate an existing exception or model.
2. Identify the port being implemented (`src/pagedoctor/domain/ports/`). The adapter's public surface is exactly that Protocol — nothing wider.

## Build the adapter — `src/pagedoctor/adapters/<area>/<name>.py`

`<area>` is `google`, `llm`, or `persistence` (§4).

- The class **implements the port's Protocol** and is constructed with its dependencies **injected** (the SDK client, settings) — **no module-level client globals**, no client built at import time. (§5.7)
- **Map at the edge.** Convert the raw Anthropic response / Google object / SQLAlchemy row **into domain models** before returning, and convert domain models into SDK calls on the way in. The domain never sees a raw object; a repository returns domain models, not ORM rows. (§5.7, §5.9)
  - Anthropic: parse via `messages.parse` into the `ChunkFindings` wrapper; on validation failure **raise `LlmResponseInvalidError`**. Never raw-string-match output. (§5.10)
  - Google: read via the Docs API; write comments via the Drive API (`comments.create`) — **never** mutate the manuscript. Keep scope single-doc. (§8)
  - Output adapters must post **idempotently** — consult the per-finding checkpoint; a retry never double-posts. (§5.12, §10)
- **Raise typed domain exceptions** on failure; do not return error values. Catch SDK/transport errors here and translate them to the domain hierarchy.
- **No blocking I/O on an async path** — use the async client or offload (§5.8).

## Wire it in — `src/pagedoctor/app/container.py`

Register the adapter in the composition root so it's injected wherever the port is depended on. The domain and routes depend on the **port**, never the concrete class.

## Test it — `tests/adapters/test_<name>.py`

- Mock the external dependency (Anthropic SDK / Google client / DB session). Assert: the port contract holds, raw payloads map correctly to domain models, failures raise the right typed exception, and (for output adapters) re-running does not double-post. Tests are first-class and kept. (§5.13)

## After writing

- Run the `hexagonal-guard` agent on the diff; for any Google/LLM/persistence change also run `data-protection-auditor`. The per-edit and stop hooks handle ruff/mypy/pytest.
