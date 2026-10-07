"""Property-based testing using Hypothesis for domain invariants."""

from datetime import UTC, date, datetime

from hypothesis import given
from hypothesis import strategies as st

from backend.app.domain.calendar import (
    add_working_days,
    calculate_task_finish_date,
    calculate_task_start_date,
    is_working_day,
    next_working_day,
)
from backend.app.domain.clock import FrozenClock
from backend.app.domain.graph import TaskGraph
from backend.app.domain.models import Dependency, ProjectPlan, Task
from backend.app.domain.scheduler import DeterministicScheduler

# Strategies
dates_strategy = st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31))
work_days_strategy = st.integers(min_value=-50, max_value=50)
duration_strategy = st.integers(min_value=1, max_value=60)


@given(d=dates_strategy, n=work_days_strategy)
def test_add_working_days_is_always_a_working_day(d: date, n: int):
    """Property: add_working_days always lands on a valid Monday-Friday working day."""
    result = add_working_days(d, n)
    assert is_working_day(result) is True
    assert result.weekday() not in (5, 6)


@given(d=dates_strategy, dur=duration_strategy)
def test_task_date_calculation_roundtrip(d: date, dur: int):
    """Property: start -> finish -> start roundtrip is invariant."""
    start = next_working_day(d)
    finish = calculate_task_finish_date(start, dur)
    assert is_working_day(finish) is True

    recomputed_start = calculate_task_start_date(finish, dur)
    assert recomputed_start == start


@given(
    num_nodes=st.integers(min_value=2, max_value=12),
    data=st.data(),
)
def test_topological_sort_preserves_dependency_order(num_nodes: int, data: st.DataObject):
    """Property: In any valid DAG, topological sort places predecessors before successors."""
    node_names = [f"T{i}" for i in range(num_nodes)]

    # Generate edges strictly from lower index to higher index to guarantee a DAG
    edges: list[Dependency] = []
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            if data.draw(st.booleans()):
                edges.append(Dependency(predecessor_id=node_names[i], successor_id=node_names[j]))

    graph = TaskGraph(tasks=node_names, dependencies=edges)
    assert graph.find_cycle() is None

    order = graph.topological_sort()
    pos = {name: idx for idx, name in enumerate(order)}

    for edge in edges:
        assert pos[edge.predecessor_id] < pos[edge.successor_id], (
            f"Predecessor {edge.predecessor_id} appeared after successor {edge.successor_id}"
        )


@given(
    num_tasks=st.integers(min_value=1, max_value=8),
    data=st.data(),
)
def test_scheduler_is_strictly_deterministic(num_tasks: int, data: st.DataObject):
    """Property: DeterministicScheduler produces identical results across runs."""
    tasks = {}
    for i in range(num_tasks):
        hrs = float(data.draw(st.integers(min_value=1, max_value=40)))
        tasks[f"T{i}"] = Task(id=f"T{i}", title=f"Task {i}", estimated_hours=hrs)

    # Generate forward-only dependencies to ensure DAG
    dependencies = []
    for i in range(num_tasks):
        for j in range(i + 1, num_tasks):
            if data.draw(st.booleans()):
                dependencies.append(Dependency(predecessor_id=f"T{i}", successor_id=f"T{j}"))

    plan = ProjectPlan(
        id="PROP_PLAN",
        project_id="PROJ_PROP",
        version=1,
        name="Property Plan",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        tasks=tasks,
        dependencies=dependencies,
    )

    clock = FrozenClock(date(2026, 10, 5))
    scheduler = DeterministicScheduler(clock)

    res1 = scheduler.schedule(plan)
    res2 = scheduler.schedule(plan)

    assert res1.project_start_date == res2.project_start_date
    assert res1.project_finish_date == res2.project_finish_date
    assert res1.critical_path == res2.critical_path
    assert res1.is_feasible == res2.is_feasible

    for t_id in tasks:
        assert res1.scheduled_tasks[t_id] == res2.scheduled_tasks[t_id]
