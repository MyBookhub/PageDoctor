---
name: new-domain-model
description: Add a Pydantic v2 domain model (entity, value object, or enum) to PageDoctor's pure domain core. Use when introducing a new typed structure under src/pagedoctor/domain/models/. Enforces the no-dicts-across-boundaries, frozen-value-object, StrEnum rules.
allowed-tools: Read, Grep, Glob, Edit, Write, Agent
---

# New Domain Model

Adds a typed model to `src/pagedoctor/domain/models/`. The domain core is pure: **stdlib + Pydantic only** (CLAUDE.md §5.7).

## Before writing anything

1. **Run the `pagedoctor-lookup` agent** with the model's name/purpose. If it already exists, import it — stop here (DRY, §5.6).
2. Re-read the relevant entity in `CLAUDE.md` §6 — names there are the contract.

## Rules for the model

- **Pydantic v2 `BaseModel`.** Value objects (anything compared by value — `LocatedSpan`, `Suggestion`, `TermVariant`) are `model_config = ConfigDict(frozen=True)`.
- **Fixed value sets are `StrEnum`** (`CheckMode`, `BookType`, `Strictness`, `Priority`, `Category`, `RunStatus`) — never bare string literals.
- **Full type hints, modern generics** (`list[Finding]`, `frozenset[str]`, `X | None`). No `Any` without an inline `# Any: <reason>`.
- **No docstrings.** A comment only for a genuinely non-obvious invariant.
- **No `dict` fields that smuggle structure** — model the structure. A field that is "some JSON" is a missing model.
- **No imports of `anthropic`/`google`/`fastapi`/`sqlalchemy`** — if the model seems to need one, it belongs in an adapter's mapping layer, not the domain.
- Place it in the right file under `domain/models/` (`finding.py`, `config.py`, `document.py`, `consistency.py`, `run.py`) per §4; create a new module only if no existing one fits.
- Imports at top, three groups, absolute (§5.5).

## After writing

- Add or extend a unit test under `tests/unit/` constructing the model and asserting validation/immutability where it matters (tests are first-class, §5.13).
- The per-edit hooks run `ruff` + `mypy` and the domain-purity check automatically; resolve anything they surface before moving on.

Do not wire the model into adapters or routes here — that is `new-adapter` / app work.
