"""Unit tests for CPM forward/backward pass, float calculations, and critical path."""

from datetime import date

from backend.app.domain.critical_path import calculate_critical_path
from backend.app.domain.models import Dependency, Task


def test_linear_critical_path():
    """T1 (2 days) -> T2 (3 days) -> T3 (1 day).

    All tasks must be on the critical path with 0 slack.
    """
    tasks = {
        "T1": Task(id="T1", title="T1", duration_working_days=2),
        "T2": Task(id="T2", title="T2", duration_working_days=3),
        "T3": Task(id="T3", title="T3", duration_working_days=1),
    }
    deps = [
        Dependency("T1", "T2"),
        Dependency("T2", "T3"),
    ]
    start_date = date(2026, 11, 2)  # Monday
    cpm_results, critical_path = calculate_critical_path(tasks, deps, start_date)

    assert critical_path == ["T1", "T2", "T3"]
    assert cpm_results["T1"].total_slack == 0
    assert cpm_results["T2"].total_slack == 0
    assert cpm_results["T3"].total_slack == 0

    assert cpm_results["T1"].early_start == date(2026, 11, 2)
    assert cpm_results["T1"].early_finish == date(2026, 11, 3)
    assert cpm_results["T2"].early_start == date(2026, 11, 4)
    assert cpm_results["T2"].early_finish == date(2026, 11, 6)
    assert cpm_results["T3"].early_start == date(2026, 11, 9)
    assert cpm_results["T3"].early_finish == date(2026, 11, 9)


def test_parallel_branches_slack_calculation():
    """Branch A: T_Start (1d) -> T_Long (5d) -> T_End (1d) -> Total 7 days
    Branch B: T_Start (1d) -> T_Short (2d) -> T_End (1d) -> T_Short has 3 days slack!
    """
    tasks = {
        "T_Start": Task(id="T_Start", title="Start", duration_working_days=1),
        "T_Long": Task(id="T_Long", title="Long", duration_working_days=5),
        "T_Short": Task(id="T_Short", title="Short", duration_working_days=2),
        "T_End": Task(id="T_End", title="End", duration_working_days=1),
    }
    deps = [
        Dependency("T_Start", "T_Long"),
        Dependency("T_Start", "T_Short"),
        Dependency("T_Long", "T_End"),
        Dependency("T_Short", "T_End"),
    ]
    start_date = date(2026, 11, 2)
    cpm_results, critical_path = calculate_critical_path(tasks, deps, start_date)

    assert set(critical_path) == {"T_Start", "T_Long", "T_End"}
    assert "T_Short" not in critical_path
    assert cpm_results["T_Short"].total_slack == 3
    assert cpm_results["T_Long"].total_slack == 0
