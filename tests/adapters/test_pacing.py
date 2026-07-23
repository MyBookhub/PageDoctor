import random

from pagedoctor.adapters.pacing import HumanWorkPacer


def test_default_session_spreads_over_the_two_hour_window() -> None:
    pacer = HumanWorkPacer(rng=random.Random(7))

    intervals = pacer.plan(12)

    assert len(intervals) == 12
    assert all(interval > 0 for interval in intervals)
    assert 105 * 60 <= sum(intervals) <= 120 * 60


def test_configured_minutes_shrink_the_window() -> None:
    pacer = HumanWorkPacer(total_minutes=10, rng=random.Random(7))

    intervals = pacer.plan(5)

    assert pacer.min_total_seconds == 525.0
    assert pacer.max_total_seconds == 600
    assert 525 <= sum(intervals) <= 600


def test_plan_for_a_clean_manuscript_still_takes_one_pause() -> None:
    pacer = HumanWorkPacer(rng=random.Random(7))

    intervals = pacer.plan(0)

    assert len(intervals) == 1
    assert pacer.min_total_seconds <= intervals[0] <= pacer.max_total_seconds


def test_plans_are_randomized_between_runs() -> None:
    pacer = HumanWorkPacer(rng=random.Random(7))

    assert pacer.plan(5) != pacer.plan(5)


def test_pause_delegates_to_the_injected_sleep() -> None:
    slept: list[float] = []
    pacer = HumanWorkPacer(rng=random.Random(7), sleep=slept.append)

    pacer.pause(12.5)

    assert slept == [12.5]
