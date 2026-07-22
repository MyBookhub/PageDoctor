import random
import time
from collections.abc import Callable

# The simulated working session lands in a 105–120 minute window, so the finished copy
# appears "after about two hours" without being suspiciously exact.
MIN_TOTAL_SECONDS = 105 * 60
MAX_TOTAL_SECONDS = 120 * 60


class HumanWorkPacer:
    # Paces the write phase like a human editor's session (issue #34): one randomized
    # pause before each comment, summing to the planned total. Deliberately inefficient —
    # that is the feature. Sleeping is injected so tests never actually wait.

    def __init__(
        self,
        rng: random.Random | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._rng = rng or random.Random()
        self._sleep = sleep

    def plan(self, pause_count: int) -> list[float]:
        # One interval per pause, never fewer than one — even a clean manuscript takes
        # reading time before the copy appears.
        total = self._rng.uniform(MIN_TOTAL_SECONDS, MAX_TOTAL_SECONDS)
        weights = [self._rng.random() + 0.05 for _ in range(max(1, pause_count))]
        scale = total / sum(weights)
        return [weight * scale for weight in weights]

    def pause(self, seconds: float) -> None:
        self._sleep(seconds)
