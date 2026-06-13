---
name: german-eval
description: Run PageDoctor's German proofreading evaluation against the labelled sample manuscripts and report precision/recall, weighted toward minimizing false positives (Sophie must not flag correct text). Use to measure editing quality after changing the engine, prompts, model, or config — and to guard against regressions.
allowed-tools: Read, Grep, Glob, Bash
---

# German Eval

Measures how good Sophie's editing actually is. The engine's value is editorial quality in German; this is how we know it improved (or regressed) — not vibes.

## What it measures

Against a set of **labelled sample manuscripts** (`tests/fixtures/` — synthetic German text with known issues; never real creator content, §9), run the engine with a fixed `ReviewConfig` and compare the findings it produces to the gold labels:

- **Precision** — of the issues Sophie flagged, how many are real. **This is weighted highest:** a false positive (flagging correct German) erodes the creator's trust and wastes the PM's pruning time, which is worse than a miss. Report precision prominently and treat a precision drop as a failure even if recall rose.
- **Recall** — of the known issues, how many Sophie caught.
- Break both down by category (proofreading vs editing) and priority, so a regression is localizable.

## How to run

If the eval harness exists (a script under `scripts/` or `tests/eval/` plus a labelled fixture set), run it via the project venv and report the table:

```bash
.venv/bin/python -m pagedoctor.eval.german   # or the harness entrypoint
```

If the harness does **not** exist yet, building it is the first task when this skill is invoked: a small runner that (1) loads labelled fixtures, (2) runs the engine through the orchestrator against a **fake or recorded** LLM where determinism matters — or the real model when measuring true quality, (3) matches findings to labels by located span/quoted text, (4) prints precision, recall, and per-category counts. Keep it deterministic where it can be; isolate any real-model calls. It must never log manuscript text (§9) — report counts and ids only.

## Reporting

Output a compact table (overall + per category) and a one-line verdict vs the last baseline: improved / regressed / flat, with precision called out first. Note the model and config used so results are comparable.
