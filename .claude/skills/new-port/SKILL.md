---
name: new-port
description: Define a new hexagonal port (a Protocol interface in the domain) plus a fake in-memory implementation for tests. Use when the domain needs a new external capability (a new kind of document source, output target, provider, or repository) before any concrete adapter exists.
allowed-tools: Read, Grep, Glob, Edit, Write, Agent
---

# New Port

A port is the domain's interface to the outside world. It lives in the domain and is **pure** — it speaks only in domain models (CLAUDE.md §2, §5.7).

## Before writing anything

1. **Run `pagedoctor-lookup`** — one of the four existing ports (`DocumentSourcePort`, `LlmProviderPort`, `OutputPort`, `RunRepositoryPort`) may already cover the need. If so, extend it rather than adding a new one.
2. Confirm the capability is genuinely external (network, LLM, DB, clock). Pure compute is a `domain/services/` function, not a port.

## Define the port — `src/pagedoctor/domain/ports/<name>.py`

- A `typing.Protocol` (preferred) or ABC. Methods are fully typed and **accept and return domain models only** — never a `dict`, a raw SDK object, or `Any`.
- Failure is communicated by **raising a typed domain exception** from `domain/errors.py` (add one via the error hierarchy if needed) — never an error return. (§5.2)
- No docstrings; a comment only for a non-obvious contract detail (e.g. "must re-read fresh — indices are not stable across runs").
- Keep methods minimal — one capability per port; don't bundle reads and writes that belong to different responsibilities (§5.3).

## Ship a fake — `tests/fakes/` (or `tests/unit/fakes/`)

- An in-memory implementation of the Protocol for use in domain unit tests: deterministic, no network, records calls so tests can assert behavior. This is how the domain is tested with **zero network** (§5.13). A port without a fake is incomplete.

## After writing

- The domain-purity and `mypy` hooks run on save. The real adapter that implements this port is created later with the `new-adapter` skill.
