"""Tests for TaskGraph, cycle detection, and topological sorting."""

import pytest

from backend.app.domain.graph import (
    CycleDetectedError,
    TaskGraph,
    TaskNotFoundError,
)
from backend.app.domain.models import Dependency, Task


def test_missing_task_raises_task_not_found():
    tasks = [Task(id="T1", title="Task 1")]
    deps = [Dependency(predecessor_id="T1", successor_id="T2")]
    with pytest.raises(TaskNotFoundError, match="Task 'T2'"):
        TaskGraph(tasks=tasks, dependencies=deps)

    deps_pred_missing = [Dependency(predecessor_id="T0", successor_id="T1")]
    with pytest.raises(TaskNotFoundError, match="Task 'T0'"):
        TaskGraph(tasks=tasks, dependencies=deps_pred_missing)


def test_linear_dag_topological_sort():
    tasks = ["A", "B", "C", "D"]
    deps = [
        Dependency(predecessor_id="A", successor_id="B"),
        Dependency(predecessor_id="B", successor_id="C"),
        Dependency(predecessor_id="C", successor_id="D"),
    ]
    graph = TaskGraph(tasks=tasks, dependencies=deps)
    assert graph.find_cycle() is None
    order = graph.topological_sort()
    assert order == ["A", "B", "C", "D"]


def test_branching_dag_topological_sort():
    tasks = ["A", "B", "C", "D"]
    # A -> B, A -> C, B -> D, C -> D
    deps = [
        Dependency(predecessor_id="A", successor_id="B"),
        Dependency(predecessor_id="A", successor_id="C"),
        Dependency(predecessor_id="B", successor_id="D"),
        Dependency(predecessor_id="C", successor_id="D"),
    ]
    graph = TaskGraph(tasks=tasks, dependencies=deps)
    assert graph.find_cycle() is None
    order = graph.topological_sort()
    # A must come before B and C; B and C before D. Tie-breaking gives B before C alphabetically.
    assert order == ["A", "B", "C", "D"]


def test_two_node_cycle():
    tasks = ["A", "B"]
    deps = [
        Dependency(predecessor_id="A", successor_id="B"),
        Dependency(predecessor_id="B", successor_id="A"),
    ]
    graph = TaskGraph(tasks=tasks, dependencies=deps)
    cycle = graph.find_cycle()
    assert cycle is not None
    assert cycle == ["A", "B", "A"] or cycle == ["B", "A", "B"]

    with pytest.raises(CycleDetectedError) as exc_info:
        graph.topological_sort()
    assert "Circular dependency detected" in str(exc_info.value)


def test_three_node_cycle():
    tasks = ["A", "B", "C", "D"]
    # A -> B -> C -> B (cycle between B and C)
    deps = [
        Dependency(predecessor_id="A", successor_id="B"),
        Dependency(predecessor_id="B", successor_id="C"),
        Dependency(predecessor_id="C", successor_id="B"),
        Dependency(predecessor_id="C", successor_id="D"),
    ]
    graph = TaskGraph(tasks=tasks, dependencies=deps)
    cycle = graph.find_cycle()
    assert cycle is not None
    assert cycle == ["B", "C", "B"] or cycle == ["C", "B", "C"]

    with pytest.raises(CycleDetectedError):
        graph.topological_sort()


def test_self_dependency_cycle():
    tasks = ["A"]
    deps = [Dependency(predecessor_id="A", successor_id="A")]
    graph = TaskGraph(tasks=tasks, dependencies=deps)
    cycle = graph.find_cycle()
    assert cycle == ["A", "A"]

    with pytest.raises(CycleDetectedError):
        graph.topological_sort()


def test_disconnected_graph_with_cycle():
    tasks = ["A", "B", "X", "Y"]
    # A -> B (valid), X -> Y -> X (cycle)
    deps = [
        Dependency(predecessor_id="A", successor_id="B"),
        Dependency(predecessor_id="X", successor_id="Y"),
        Dependency(predecessor_id="Y", successor_id="X"),
    ]
    graph = TaskGraph(tasks=tasks, dependencies=deps)
    cycle = graph.find_cycle()
    assert cycle is not None
    assert "X" in cycle and "Y" in cycle

    with pytest.raises(CycleDetectedError):
        graph.topological_sort()
