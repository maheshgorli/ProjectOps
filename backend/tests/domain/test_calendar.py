"""Tests for working-day calendar calculations."""

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


def test_is_working_day():
    # 2026-10-05 is Monday, 2026-10-09 is Friday
    assert is_working_day(date(2026, 10, 5)) is True
    assert is_working_day(date(2026, 10, 6)) is True
    assert is_working_day(date(2026, 10, 7)) is True
    assert is_working_day(date(2026, 10, 8)) is True
    assert is_working_day(date(2026, 10, 9)) is True
    # Saturday and Sunday
    assert is_working_day(date(2026, 10, 10)) is False
    assert is_working_day(date(2026, 10, 11)) is False


def test_next_working_day():
    monday = date(2026, 10, 5)
    friday = date(2026, 10, 9)
    saturday = date(2026, 10, 10)
    sunday = date(2026, 10, 11)

    assert next_working_day(monday) == monday
    assert next_working_day(friday) == friday
    assert next_working_day(saturday) == date(2026, 10, 12)  # Next Monday
    assert next_working_day(sunday) == date(2026, 10, 12)  # Next Monday


def test_previous_working_day():
    monday = date(2026, 10, 5)
    saturday = date(2026, 10, 10)
    sunday = date(2026, 10, 11)

    assert previous_working_day(monday) == monday
    assert previous_working_day(saturday) == date(2026, 10, 9)  # Friday
    assert previous_working_day(sunday) == date(2026, 10, 9)  # Friday


def test_add_working_days_forward():
    monday = date(2026, 10, 5)
    # +0 days
    assert add_working_days(monday, 0) == monday
    # +1 day: Tuesday
    assert add_working_days(monday, 1) == date(2026, 10, 6)
    # +4 days: Friday
    assert add_working_days(monday, 4) == date(2026, 10, 9)
    # +5 days: Spans weekend, arrives on next Monday
    assert add_working_days(monday, 5) == date(2026, 10, 12)
    # Starting on Saturday with +1 day -> Monday rolls + 1 day = Tuesday
    assert add_working_days(date(2026, 10, 10), 1) == date(2026, 10, 13)


def test_add_working_days_backward():
    friday = date(2026, 10, 9)
    # -1 day: Thursday
    assert add_working_days(friday, -1) == date(2026, 10, 8)
    # -4 days: Monday
    assert add_working_days(friday, -4) == date(2026, 10, 5)
    # -5 days: Previous Friday (2026-10-02)
    assert add_working_days(friday, -5) == date(2026, 10, 2)


def test_calculate_task_finish_date():
    monday = date(2026, 10, 5)
    friday = date(2026, 10, 9)

    # 1-day task starting Monday finishes on Monday
    assert calculate_task_finish_date(monday, 1) == monday
    # 2-day task starting Monday finishes on Tuesday
    assert calculate_task_finish_date(monday, 2) == date(2026, 10, 6)
    # 5-day task starting Monday finishes on Friday
    assert calculate_task_finish_date(monday, 5) == friday
    # 2-day task starting Friday finishes on next Monday
    assert calculate_task_finish_date(friday, 2) == date(2026, 10, 12)


def test_calculate_task_start_date_inverse():
    monday = date(2026, 10, 5)
    # For tasks starting Monday with duration 1, 3, 5, 10
    for dur in [1, 2, 5, 8, 10]:
        finish = calculate_task_finish_date(monday, dur)
        start = calculate_task_start_date(finish, dur)
        assert start == monday, f"Mismatch for duration {dur}: expected {monday}, got {start}"


def test_working_days_between():
    mon = date(2026, 10, 5)
    tue = date(2026, 10, 6)
    fri = date(2026, 10, 9)
    next_mon = date(2026, 10, 12)

    assert working_days_between(mon, mon) == 1
    assert working_days_between(mon, tue) == 2
    assert working_days_between(mon, fri) == 5
    # Across weekend: Mon (5), Tue (6), Wed (7), Thu (8), Fri (9), Mon (12) -> 6 days
    assert working_days_between(mon, next_mon) == 6
    # Reversed
    assert working_days_between(fri, mon) == 0


def test_working_days_delta():
    mon = date(2026, 10, 5)
    tue = date(2026, 10, 6)
    fri = date(2026, 10, 9)

    assert working_days_delta(mon, mon) == 0
    assert working_days_delta(mon, tue) == 1
    assert working_days_delta(mon, fri) == 4
    assert working_days_delta(tue, mon) == -1
    assert working_days_delta(fri, mon) == -4


def test_hours_to_working_days():
    assert hours_to_working_days(0.0, 8.0) == 0
    assert hours_to_working_days(4.0, 8.0) == 1  # Minimum 1 day for positive hours
    assert hours_to_working_days(8.0, 8.0) == 1
    assert hours_to_working_days(9.0, 8.0) == 2  # Rounds up (ceil)
    assert hours_to_working_days(16.0, 8.0) == 2
    assert hours_to_working_days(20.0, 8.0) == 3
    # Custom 6-hour capacity
    assert hours_to_working_days(12.0, 6.0) == 2
