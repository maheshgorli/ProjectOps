"""Unit tests for injectable Clock protocol, SystemClock, and FixedClock."""

from datetime import UTC, date, datetime, timedelta

from backend.app.domain.clock import Clock, FixedClock, FrozenClock, SystemClock


def test_system_clock_returns_utc_time():
    clock = SystemClock()
    assert isinstance(clock, Clock)
    now = clock.now()
    today = clock.today()
    assert now.tzinfo is not None
    assert today == now.date()


def test_fixed_clock_initialization_and_advancement():
    start_date = date(2026, 11, 2)
    clock = FixedClock(start_date)

    assert clock.today() == start_date
    assert clock.now().date() == start_date

    # Advance by 3 days
    clock.advance_days(3)
    assert clock.today() == date(2026, 11, 5)

    # Advance with delta and hours
    clock.advance(days=1, hours=5)
    assert clock.today() == date(2026, 11, 6)

    # Explicit reset via set()
    new_date = date(2027, 1, 1)
    clock.set(new_date)
    assert clock.today() == new_date


def test_fixed_clock_datetime_precision():
    fixed_dt = datetime(2026, 10, 15, 14, 30, 0, tzinfo=UTC)
    clock = FixedClock(fixed_dt)
    assert clock.now() == fixed_dt
    assert clock.today() == date(2026, 10, 15)

    clock.advance(delta=timedelta(hours=2, minutes=15))
    assert clock.now() == datetime(2026, 10, 15, 16, 45, 0, tzinfo=UTC)


def test_frozen_clock_alias():
    clock = FrozenClock(date(2026, 1, 1))
    assert clock.today() == date(2026, 1, 1)
    clock.set_time(date(2026, 1, 2))
    assert clock.today() == date(2026, 1, 2)
