---
name: new-migration
description: Create an Alembic schema migration for PageDoctor's metadata store. Use when adding or changing a table/column in the persistence layer. Always generates the revision via Alembic from the correct directory — never hand-author or hand-edit a revision file. Enforces the metadata-only rule (no manuscript/finding content columns).
allowed-tools: Read, Grep, Glob, Bash, Edit
---

# New Migration

All schema changes go through Alembic. **Never** hand-write or hand-edit a revision file (CLAUDE.md §5.9).

## Hard rule before touching the schema

The store is **metadata only** (§9). A migration may add columns for: doc id, timestamps, mode/config, status, counts, correlation id, posted-finding **keys** (hashes). A migration may **never** add a column, table, or blob that holds manuscript text, finding text, quotes, proposed changes, reasons, or comment bodies. If the change implies storing content, stop and reconsider — that is a design error, not a migration.

## Steps

1. Make the model change first in the SQLAlchemy metadata (the persistence adapter's table definitions) so autogenerate can see it.
2. Generate the revision from the persistence directory using the project venv's Alembic — **autogenerate, then review**:
   ```bash
   .venv/bin/alembic -c <alembic.ini path> revision --autogenerate -m "short description"
   ```
   (Adjust the path to wherever `alembic.ini` / the migrations env lives under `adapters/persistence/`.)
3. **Read the generated revision** and verify: it matches the intended change, has a correct `down_revision`, and a working `downgrade()`. Edit only to correct an autogenerate mistake — never to author a migration from scratch.
4. Re-confirm the metadata-only rule against the diff (no content columns).
5. Apply locally to verify it runs clean:
   ```bash
   .venv/bin/alembic -c <alembic.ini path> upgrade head
   ```

If Alembic isn't initialized yet (pre-scaffold / before the persistence adapter exists), that setup is part of issue #4 — do not improvise a migrations tree here; report that it's missing.
