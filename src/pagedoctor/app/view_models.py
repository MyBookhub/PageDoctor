from collections.abc import Sequence

from fastapi import Request
from pydantic import BaseModel

from pagedoctor.app.auth import issue_csrf
from pagedoctor.domain.models.config import BookType, CheckMode, Strictness
from pagedoctor.domain.models.run import ReviewRun, RunStatus

_TERMINAL_STATUSES = {RunStatus.DONE, RunStatus.INCOMPLETE, RunStatus.FAILED}
# Resume is for recovery only: a run that stopped (failed or hit its budget). An in-flight
# PENDING/RUNNING/WRITING run must NOT offer resume, or a PM could launch a duplicate
# concurrent execution and burn tokens racing the one already running.
_RESUMABLE_STATUSES = {RunStatus.FAILED, RunStatus.INCOMPLETE}

_STATUS_LABELS = {
    RunStatus.PENDING: "In Warteschlange",
    RunStatus.RUNNING: "Analyse läuft",
    RunStatus.WRITING: "Kommentare werden geschrieben",
    RunStatus.DONE: "Fertig",
    RunStatus.INCOMPLETE: "Unvollständig (Token-Budget erreicht)",
    RunStatus.FAILED: "Fehlgeschlagen",
}

_STATUS_TONES = {
    RunStatus.PENDING: "neutral",
    RunStatus.RUNNING: "info",
    RunStatus.WRITING: "info",
    RunStatus.DONE: "success",
    RunStatus.INCOMPLETE: "warning",
    RunStatus.FAILED: "danger",
}

_MODE_LABELS = {
    CheckMode.PROOFREADING: "Korrektorat",
    CheckMode.EDITING: "Lektorat",
}

MODE_OPTIONS = [
    (CheckMode.PROOFREADING.value, "Korrektorat — Rechtschreibung, Grammatik, Zeichensetzung"),
    (CheckMode.EDITING.value, "Lektorat — Stil, Konsistenz, Wiederholungen, Lesbarkeit"),
]

BOOK_TYPE_OPTIONS = [
    (BookType.COOKBOOK.value, "Kochbuch"),
    (BookType.ADVICE.value, "Ratgeber"),
    (BookType.NOVEL_MEMOIR.value, "Roman / Memoir"),
    (BookType.CHILDRENS.value, "Kinderbuch"),
]

STRICTNESS_OPTIONS = [
    (Strictness.LIGHT.value, "Leicht — nur Fehler"),
    (Strictness.STANDARD.value, "Standard — Fehler, Stil, Konsistenz"),
    (Strictness.THOROUGH.value, "Gründlich — zusätzlich Lesbarkeit und Satzlänge"),
]


class RunView(BaseModel):
    id: str
    doc_id: str
    doc_url: str
    output_doc_url: str | None
    status_value: str
    status_label: str
    tone: str
    is_terminal: bool
    can_resume: bool
    finding_count: int
    started_at_label: str
    modes_label: str


def doc_url(doc_id: str) -> str:
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def run_view(run: ReviewRun) -> RunView:
    modes = ", ".join(_MODE_LABELS[mode] for mode in sorted(run.config.modes))
    started = run.started_at.strftime("%d.%m.%Y %H:%M") if run.started_at is not None else "—"
    return RunView(
        id=str(run.id),
        doc_id=run.doc_id,
        doc_url=doc_url(run.doc_id),
        output_doc_url=doc_url(run.output_doc_id) if run.output_doc_id else None,
        status_value=run.status.value,
        status_label=_STATUS_LABELS[run.status],
        tone=_STATUS_TONES[run.status],
        is_terminal=run.status in _TERMINAL_STATUSES,
        can_resume=run.status in _RESUMABLE_STATUSES,
        finding_count=run.finding_count,
        started_at_label=started,
        modes_label=modes,
    )


def form_context(request: Request, error: str | None = None) -> dict[str, object]:
    return {
        "csrf_token": issue_csrf(request),
        "mode_options": MODE_OPTIONS,
        "book_type_options": BOOK_TYPE_OPTIONS,
        "strictness_options": STRICTNESS_OPTIONS,
        "error": error,
    }


def progress_context(run: ReviewRun) -> dict[str, object]:
    return {"run": run_view(run)}


def runs_context(request: Request, runs: Sequence[ReviewRun]) -> dict[str, object]:
    return {"runs": [run_view(run) for run in runs], "csrf_token": issue_csrf(request)}
