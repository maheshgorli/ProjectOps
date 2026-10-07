"""Working-day calendar and capacity calculations.

Rules:
- Mon-Fri are working days; Saturday and Sunday are non-working days.
- All date and calendar math lives strictly in this module.
- Pure Python: no I/O, no DB, no LLM.
"""

import math
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Final

DEFAULT_DAILY_CAPACITY_HOURS: Final[float] = 8.0
WEEKDAY_SATURDAY: Final[int] = 5
WEEKDAY_SUNDAY: Final[int] = 6


def is_working_day(d: date, holidays: Iterable[date] | None = None) -> bool:
    """Return True if `d` is a Monday through Friday and not in holidays."""
    if d.weekday() in (WEEKDAY_SATURDAY, WEEKDAY_SUNDAY):
        return False
    return not (holidays and d in holidays)


def next_working_day(d: date, holidays: Iterable[date] | None = None) -> date:
    """Return `d` if it is already a working day; otherwise roll forward to next working day."""
    curr = d
    holiday_set = set(holidays) if holidays else set()
    while not is_working_day(curr, holiday_set):
        curr += timedelta(days=1)
    return curr


def previous_working_day(d: date, holidays: Iterable[date] | None = None) -> date:
    """Return `d` if it is a working day; otherwise roll backward to previous working day."""
    curr = d
    holiday_set = set(holidays) if holidays else set()
    while not is_working_day(curr, holiday_set):
        curr -= timedelta(days=1)
    return curr


def add_working_days(
    start_date: date,
    working_days: int,
    holidays: Iterable[date] | None = None,
) -> date:
    """
    Advance (or rewind if negative) by `working_days` count.

    If `start_date` is on a weekend/holiday, it first rolls to the nearest working day:
    forward if working_days >= 0, backward if working_days < 0.
    """
    holiday_set = set(holidays) if holidays else set()
    if working_days == 0:
        return next_working_day(start_date, holiday_set)

    step = 1 if working_days > 0 else -1
    remaining = abs(working_days)
    curr = (
        next_working_day(start_date, holiday_set)
        if step > 0
        else previous_working_day(start_date, holiday_set)
    )

    while remaining > 0:
        curr += timedelta(days=step)
        if is_working_day(curr, holiday_set):
            remaining -= 1

    return curr


def calculate_task_finish_date(
    start_date: date,
    duration_working_days: int,
    holidays: Iterable[date] | None = None,
) -> date:
    """
    Given an inclusive start date and duration in working days:
    - If duration == 0: finishes on start_date (or next working day).
    - If duration == 1: finishes on the same day (start_date).
    - If duration == N (> 1): finishes (N - 1) working days after start_date.
    """
    holiday_set = set(holidays) if holidays else set()
    curr_start = next_working_day(start_date, holiday_set)
    if duration_working_days <= 1:
        return curr_start
    return add_working_days(curr_start, duration_working_days - 1, holiday_set)


def calculate_task_start_date(
    finish_date: date,
    duration_working_days: int,
    holidays: Iterable[date] | None = None,
) -> date:
    """
    Given an inclusive finish date and duration in working days:
    - If duration <= 1: starts on finish_date.
    - If duration == N (> 1): starts (N - 1) working days before finish_date.
    """
    holiday_set = set(holidays) if holidays else set()
    curr_finish = previous_working_day(finish_date, holiday_set)
    if duration_working_days <= 1:
        return curr_finish
    return add_working_days(curr_finish, -(duration_working_days - 1), holiday_set)


def working_days_between(
    start_date: date,
    end_date: date,
    holidays: Iterable[date] | None = None,
) -> int:
    """
    Calculate the count of working days in the closed interval [start_date, end_date].
    Returns 0 if end_date < start_date.
    """
    if end_date < start_date:
        return 0

    holiday_set = set(holidays) if holidays else set()
    count = 0
    curr = start_date
    while curr <= end_date:
        if is_working_day(curr, holiday_set):
            count += 1
        curr += timedelta(days=1)
    return count


def working_days_delta(
    d1: date,
    d2: date,
    holidays: Iterable[date] | None = None,
) -> int:
    """
    Signed working-day difference from d1 to d2.
    Positive if d2 > d1, 0 if d1 == d2, negative if d2 < d1.
    """
    if d1 == d2:
        return 0
    if d1 < d2:
        days = working_days_between(d1, d2, holidays)
        # If both are working days, count of interval is (delta + 1)
        # e.g., Mon to Mon is 1 working day in interval, delta is 0
        # Mon to Tue is 2 working days in interval, delta is +1
        return max(0, days - 1)
    else:
        days = working_days_between(d2, d1, holidays)
        return -max(0, days - 1)


def hours_to_working_days(
    estimated_hours: float,
    daily_capacity_hours: float = DEFAULT_DAILY_CAPACITY_HOURS,
) -> int:
    """
    Convert estimated work hours to integer working days using daily capacity.
    Rule: 0 hours = 0 days. Any positive hours rounds up (ceil) to at least 1 working day.
    """
    if estimated_hours <= 0.0:
        return 0
    capacity = max(1.0, daily_capacity_hours)
    return max(1, math.ceil(estimated_hours / capacity))
