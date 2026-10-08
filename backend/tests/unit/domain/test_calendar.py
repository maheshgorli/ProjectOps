"""Unit tests for Mon-Fri working-day calendar date arithmetic."""

from datetime import date

from backend.app.domain.calendar import (
    add_working_days,
    calculate_task_finish_date,
    calculate_task_start_date,
    hours_to_working_days,
    is_working_day,
    next_working_day,
    previous_working_day,
    working_days_between,
    working_days_delta,
)


def test_is_working_day_mon_to_fri():
    monday = date(2026, 11, 2)
    tuesday = date(2026, 11, 3)
    friday = date(2026, 11, 6)
    saturday = date(2026, 11, 7)
    sunday = date(2026, 11, 8)

    assert is_working_day(monday) is True
    assert is_working_day(tuesday) is True
    assert is_working_day(friday) is True
    assert is_working_day(saturday) is False
    assert is_working_day(sunday) is False


def test_next_and_previous_working_day():
    friday = date(2026, 11, 6)
    saturday = date(2026, 11, 7)
    sunday = date(2026, 11, 8)
    monday = date(2026, 11, 9)

    assert next_working_day(friday) == friday
    assert next_working_day(saturday) == monday
    assert next_working_day(sunday) == monday

    assert previous_working_day(friday) == friday
    assert previous_working_day(saturday) == friday
    assert previous_working_day(sunday) == friday


def test_add_working_days_forward_and_backward():
    friday = date(2026, 11, 6)
    monday = date(2026, 11, 9)
    wednesday = date(2026, 11, 11)

    # 1 working day forward from Friday is Monday
    assert add_working_days(friday, 1) == monday
    # 3 working days forward from Friday is Wednesday
    assert add_working_days(friday, 3) == wednesday

    # Backward arithmetic
    assert add_working_days(monday, -1) == friday
    assert add_working_days(wednesday, -3) == friday

    # 0 working days on weekend rolls to next working day
    saturday = date(2026, 11, 7)
    assert add_working_days(saturday, 0) == monday


def test_calculate_task_finish_date():
    monday = date(2026, 11, 2)
    # 1-day task starting Monday finishes Monday
    assert calculate_task_finish_date(monday, 1) == monday

    # 5-day task starting Monday finishes Friday (same week)
    friday = date(2026, 11, 6)
    assert calculate_task_finish_date(monday, 5) == friday

    # 6-day task starting Monday finishes next Monday
    next_monday = date(2026, 11, 9)
    assert calculate_task_finish_date(monday, 6) == next_monday


def test_calculate_task_start_date():
    friday = date(2026, 11, 6)
    monday = date(2026, 11, 2)

    assert calculate_task_start_date(friday, 1) == friday
    assert calculate_task_start_date(friday, 5) == monday


def test_working_days_between():
    monday = date(2026, 11, 2)
    friday = date(2026, 11, 6)
    next_monday = date(2026, 11, 9)

    # Same day inclusive is 1 working day
    assert working_days_between(monday, monday) == 1
    # Monday to Friday is 5 working days
    assert working_days_between(monday, friday) == 5
    # Monday to next Monday is 6 working days
    assert working_days_between(monday, next_monday) == 6
    # Inverted interval returns 0
    assert working_days_between(friday, monday) == 0


def test_working_days_delta():
    monday = date(2026, 11, 2)
    friday = date(2026, 11, 6)
    assert working_days_delta(monday, monday) == 0
    assert working_days_delta(monday, friday) == 4
    assert working_days_delta(friday, monday) == -4


def test_hours_to_working_days():
    assert hours_to_working_days(0.0, 8.0) == 0
    assert hours_to_working_days(4.0, 8.0) == 1
    assert hours_to_working_days(8.0, 8.0) == 1
    assert hours_to_working_days(9.0, 8.0) == 2
    assert hours_to_working_days(16.0, 8.0) == 2
