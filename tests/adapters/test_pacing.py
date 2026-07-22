import random

from pagedoctor.adapters.pacing import MAX_TOTAL_SECONDS, MIN_TOTAL_SECONDS, HumanWorkPacer


def test_plan_spreads_the_session_over_the_two_hour_window() -> None:
    pacer = HumanWorkPacer(rng=random.Random(7))

    intervals = pacer.plan(12)

    assert len(intervals) == 12
    assert all(interval > 0 for interval in intervals)
    assert MIN_TOTAL_SECONDS <= sum(intervals) <= MAX_TOTAL_SECONDS


def test_plan_for_a_clean_manuscript_still_takes_one_pause() -> None:
    pacer = HumanWorkPacer(rng=random.Random(7))

    intervals = pacer.plan(0)

    assert len(intervals) == 1
    assert MIN_TOTAL_SECONDS <= intervals[0] <= MAX_TOTAL_SECONDS


def test_plans_are_randomized_between_runs() -> None:
    pacer = HumanWorkPacer(rng=random.Random(7))

    assert pacer.plan(5) != pacer.plan(5)


def test_pause_delegates_to_the_injected_sleep() -> None:
    slept: list[float] = []
    pacer = HumanWorkPacer(rng=random.Random(7), sleep=slept.append)

    pacer.pause(12.5)

    assert slept == [12.5]
