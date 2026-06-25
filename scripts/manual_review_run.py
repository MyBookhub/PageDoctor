"""Manual smoke test for the review orchestrator (issue #5) against the real stack.

NOT a unit test — it reads a real Google Doc, calls Anthropic, posts comments, and
persists run metadata in Postgres. Prints metadata only (never manuscript/finding text),
per the data-protection rule. Use a throwaway Doc shared as editor with the Sophie
service account, and keep the doc small (every run is a full LLM pass).

Prereqs:
    docker compose up -d db        # Postgres on :5433
    make migrate                   # create the review_runs table
    # .env has ANTHROPIC_API_KEY (ZDR org), GOOGLE_SERVICE_ACCOUNT_FILE, DATABASE_URL

Start a fresh run (read -> analyze -> post -> persist), then print its status + id:
    uv run python scripts/manual_review_run.py --doc-id <DOC_ID>

Resume that run by id (re-reads fresh, re-analyzes, posts NOTHING already posted):
    uv run python scripts/manual_review_run.py --resume <RUN_ID>

Cap the cost of a pathological doc (run stops + is marked INCOMPLETE if exceeded):
    uv run python scripts/manual_review_run.py --doc-id <DOC_ID> --token-budget 50000
"""

import argparse
import uuid

import anthropic
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pagedoctor.adapters.clock import SystemClock
from pagedoctor.adapters.google.auth import build_docs_service, build_drive_service
from pagedoctor.adapters.google.comments_output import CommentsOutputAdapter
from pagedoctor.adapters.google.docs_source import GoogleDocsSource
from pagedoctor.adapters.llm.anthropic_provider import AnthropicLlmProvider
from pagedoctor.adapters.persistence.run_repository import PostgresRunRepository
from pagedoctor.config import Settings, load_settings
from pagedoctor.domain.models.config import BookType, CheckMode, ReviewConfig, Strictness
from pagedoctor.domain.models.run import ReviewRun
from pagedoctor.domain.services.engine import EditingEngine
from pagedoctor.domain.services.review_orchestrator import ReviewOrchestrator


def build_orchestrator(settings: Settings, token_budget: int | None) -> ReviewOrchestrator:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    provider = AnthropicLlmProvider(
        client, settings.anthropic_model, settings.anthropic_effort, token_budget
    )
    repository = PostgresRunRepository(sessionmaker(bind=create_engine(settings.database_url)))
    return ReviewOrchestrator(
        source=GoogleDocsSource(build_docs_service(settings)),
        engine=EditingEngine(provider),
        output=CommentsOutputAdapter(build_drive_service(settings)),
        repository=repository,
        clock=SystemClock(),
    )


def report(label: str, run: ReviewRun) -> None:
    print(f"{label}:")
    print(f"  run id            : {run.id}")
    print(f"  status            : {run.status.value}")
    print(f"  finding_count     : {run.finding_count}")
    print(f"  posted_key_count  : {len(run.posted_finding_keys)}")
    print(f"  started_at        : {run.started_at}")
    print(f"  finished_at       : {run.finished_at}")


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--doc-id", help="start a fresh run on this Doc id")
    group.add_argument("--resume", help="resume an existing run by its id")
    parser.add_argument("--token-budget", type=int, default=None)
    args = parser.parse_args()

    settings = load_settings()
    orchestrator = build_orchestrator(settings, args.token_budget)

    if args.resume is not None:
        print(
            f"Resuming run {args.resume} (re-reads the Doc fresh, re-analyzes, no double-post)..."
        )
        run = orchestrator.resume(uuid.UUID(args.resume))
        report("Resumed run", run)
        print("  open the Doc: the comment count should be UNCHANGED from the first run")
        return

    config = ReviewConfig(
        modes=frozenset({CheckMode.PROOFREADING, CheckMode.EDITING}),
        book_type=BookType.NOVEL_MEMOIR,
        strictness=Strictness.STANDARD,
    )
    print(f"Starting a review of Doc {args.doc_id} (read -> analyze -> post -> persist)...")
    run = orchestrator.start(args.doc_id, config, token_budget=args.token_budget)
    report("Completed run", run)
    print("\n  open the Doc to see Sophie's comments + the consistency report")
    print("  to prove resume never double-posts, run again:")
    print(f"    uv run python scripts/manual_review_run.py --resume {run.id}")


if __name__ == "__main__":
    main()
