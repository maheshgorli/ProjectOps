"""Tests for injectable Clock."""

from datetime import UTC, date, datetime, timedelta

from backend.app.domain.clock import Clock, FrozenClock, SystemClock


def test_system_clock_returns_utc_time():
    clock = SystemClock()
    assert isinstance(clock, Clock)
    now = clock.now()
    today = clock.today()
    assert now.tzinfo == UTC
    assert today == now.date()


def test_frozen_clock_datetime():
    fixed_time = datetime(2026, 10, 5, 9, 30, 0, tzinfo=UTC)
    clock = FrozenClock(fixed_time)
    assert isinstance(clock, Clock)
    assert clock.now() == fixed_time
    assert clock.today() == date(2026, 10, 5)


def test_frozen_clock_from_date():
    fixed_date = date(2026, 10, 5)
    clock = FrozenClock(fixed_date)
    assert clock.today() == fixed_date
    assert clock.now() == datetime(2026, 10, 5, 0, 0, 0, tzinfo=UTC)


def test_frozen_clock_advance_and_set():
    clock = FrozenClock(datetime(2026, 10, 5, 10, 0, 0, tzinfo=UTC))
    clock.advance(timedelta(days=2, hours=3))
    assert clock.now() == datetime(2026, 10, 7, 13, 0, 0, tzinfo=UTC)
    assert clock.today() == date(2026, 10, 7)

    clock.advance(timedelta(days=-1))
    assert clock.today() == date(2026, 10, 6)

    clock.set_time(date(2026, 12, 1))
    assert clock.today() == date(2026, 12, 1)
