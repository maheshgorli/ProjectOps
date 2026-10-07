"""Injectable Clock interface and implementations for deterministic time handling."""

from datetime import UTC, date, datetime, timedelta
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Protocol for time sources, enabling deterministic testing and simulation."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC datetime."""
        ...

    def today(self) -> date:
        """Return the current UTC date."""
        ...


class SystemClock:
    """Real system clock using UTC timezone."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return datetime.now(UTC).date()


class FrozenClock:
    """Deterministic, freeze-frame clock for tests, replan simulations, and time traveling."""

    def __init__(self, current: datetime | date) -> None:
        if isinstance(current, date) and not isinstance(current, datetime):
            self._current = datetime(current.year, current.month, current.day, 0, 0, 0, tzinfo=UTC)
        elif current.tzinfo is None:
            self._current = current.replace(tzinfo=UTC)
        else:
            self._current = current

    def now(self) -> datetime:
        return self._current

    def today(self) -> date:
        return self._current.date()

    def advance(self, delta: timedelta) -> None:
        """Advance the frozen time forward or backward."""
        self._current += delta

    def set_time(self, new_time: datetime | date) -> None:
        """Explicitly reset the frozen clock to a specific timestamp."""
        if isinstance(new_time, date) and not isinstance(new_time, datetime):
            self._current = datetime(
                new_time.year, new_time.month, new_time.day, 0, 0, 0, tzinfo=UTC
            )
        elif new_time.tzinfo is None:
            self._current = new_time.replace(tzinfo=UTC)
        else:
            self._current = new_time
