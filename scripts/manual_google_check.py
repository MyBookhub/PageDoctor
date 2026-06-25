"""Manual smoke test for the Google adapters (issue #4) against the real APIs.

NOT a unit test — it talks to Google. Use a throwaway Doc you created and shared as
editor with the Sophie service account. Prints metadata only (never manuscript text),
per the data-protection rule.

    uv run python scripts/manual_google_check.py --doc-id <DOC_ID>
    uv run python scripts/manual_google_check.py --doc-id <DOC_ID> --probe "ein Satz aus dem Doc"
    uv run python scripts/manual_google_check.py --doc-id <DOC_ID> --read-only
"""

import argparse
import uuid

from pagedoctor.adapters.google.auth import build_docs_service, build_drive_service
from pagedoctor.adapters.google.comments_output import CommentsOutputAdapter
from pagedoctor.adapters.google.docs_source import GoogleDocsSource
from pagedoctor.config import load_settings
from pagedoctor.domain.models.config import BookType, CheckMode, ReviewConfig, Strictness
from pagedoctor.domain.models.consistency import ConsistencyReport, RepetitionStat, TermVariant
from pagedoctor.domain.models.finding import Category, Finding, Priority, Suggestion
from pagedoctor.domain.models.run import ReviewRun, RunStatus


def sample_findings() -> list[Finding]:
    return [
        Finding(
            suggestion=Suggestion(
                original_text="Der Hund schläft.",
                proposed_change="Der Hund schläft tief.",
                reason_de="Präzisere Formulierung.",
            ),
            category=Category.EDITING,
            priority=Priority.EMPFEHLUNG,
        ),
        Finding(
            suggestion=Suggestion(
                original_text="Rezpet",
                proposed_change="Rezept",
                reason_de="Tippfehler.",
            ),
            category=Category.PROOFREADING,
            priority=Priority.FEHLER,
        ),
    ]


def sample_report() -> ConsistencyReport:
    return ConsistencyReport(
        term_variants=[
            TermVariant(canonical="Basilikum", variants=frozenset({"Baslikum"}), occurrences=3)
        ],
        spelling_variants=[],
        repetition_stats=[RepetitionStat(term="lecker", count=4, chapter="Kapitel 3")],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--doc-id", required=True, help="ID from the Doc URL .../document/d/<ID>/edit"
    )
    parser.add_argument("--probe", default=None, help="optional phrase to confirm it was read")
    parser.add_argument("--read-only", action="store_true", help="skip posting comments")
    args = parser.parse_args()

    settings = load_settings()
    docs = GoogleDocsSource(build_docs_service(settings))
    drive = CommentsOutputAdapter(build_drive_service(settings))

    print(f"Reading doc {args.doc_id} as the service account...")
    document = docs.read(args.doc_id)
    print(f"  ok: {len(document.text)} chars, {len(document.index_map.segments)} index segments")
    if args.probe is not None:
        print(f"  probe present in text: {args.probe in document.text}")

    if args.read_only:
        return

    run = ReviewRun(
        id=uuid.uuid4(),
        doc_id=args.doc_id,
        config=ReviewConfig(
            modes=frozenset({CheckMode.PROOFREADING, CheckMode.EDITING}),
            book_type=BookType.NOVEL_MEMOIR,
            strictness=Strictness.STANDARD,
        ),
        status=RunStatus.WRITING,
        correlation_id=uuid.uuid4().hex,
    )

    print("First write_findings (expect comments to appear in the Doc)...")
    drive.write_findings(run, sample_findings(), sample_report())
    print("  done — open the Doc and check the comment stream")

    print("Second write_findings with the SAME run (idempotency — expect NO new comments)...")
    drive.write_findings(run, sample_findings(), sample_report())
    print("  done — comment count in the Doc should be unchanged")


if __name__ == "__main__":
    main()
