import random
import time
from collections.abc import Callable

# The session total lands in [87.5%, 100%] of the configured target, so the copy appears
# "after about N minutes" without being suspiciously exact (120 min -> 105-120 min).
WINDOW_LOWER_FRACTION = 0.875
DEFAULT_TOTAL_MINUTES = 120


class HumanWorkPacer:
    # Paces the write phase like a human editor's session (issue #34): one randomized
    # pause before each comment, summing to the planned total. Deliberately inefficient —
    # that is the feature. Sleeping is injected so tests never actually wait.

    def __init__(
        self,
        total_minutes: int = DEFAULT_TOTAL_MINUTES,
        rng: random.Random | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.max_total_seconds = total_minutes * 60
        self.min_total_seconds = self.max_total_seconds * WINDOW_LOWER_FRACTION
        self._rng = rng or random.Random()
        self._sleep = sleep

    def plan(self, pause_count: int) -> list[float]:
        # One interval per pause, never fewer than one — even a clean manuscript takes
        # reading time before the copy appears.
        total = self._rng.uniform(self.min_total_seconds, self.max_total_seconds)
        weights = [self._rng.random() + 0.05 for _ in range(max(1, pause_count))]
        scale = total / sum(weights)
        return [weight * scale for weight in weights]

    def pause(self, seconds: float) -> None:
        self._sleep(seconds)
