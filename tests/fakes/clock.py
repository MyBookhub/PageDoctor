from datetime import UTC, datetime, timedelta


class FakeClock:
    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        current = self._now
        # Advance on each read so started_at and finished_at differ in tests.
        self._now = self._now + timedelta(seconds=1)
        return current
