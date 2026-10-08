"""Unit tests for TaskGraph, cycle detection, self-loops, and topological sorting."""

import pytest

from backend.app.domain.graph import (
    CycleDetectedError,
    SelfDependencyError,
    TaskGraph,
    TaskNotFoundError,
)
from backend.app.domain.models import Dependency, Task


def test_empty_graph():
    graph = TaskGraph(tasks=[], dependencies=[])
    assert graph.topological_sort() == []
    assert graph.find_cycle() is None


def test_single_task():
    graph = TaskGraph(tasks=["T1"], dependencies=[])
    assert graph.topological_sort() == ["T1"]
    assert graph.find_cycle() is None
    assert graph.get_upstream("T1") == set()
    assert graph.get_downstream("T1") == set()


def test_diamond_dependencies_and_transitive_traversal():
    r"""Diamond DAG:
        A
       / \
      B   C
       \ /
        D
    """
    tasks = [
        Task(id="A", title="A"),
        Task(id="B", title="B"),
        Task(id="C", title="C"),
        Task(id="D", title="D"),
    ]
    deps = [
        Dependency("A", "B"),
        Dependency("A", "C"),
        Dependency("B", "D"),
        Dependency("C", "D"),
    ]
    graph = TaskGraph(tasks=tasks, dependencies=deps)
    topo = graph.topological_sort()

    assert topo[0] == "A"
    assert topo[3] == "D"
    assert set(topo[1:3]) == {"B", "C"}

    # Direct lookups
    assert graph.get_downstream("A", transitive=False) == {"B", "C"}
    assert graph.get_upstream("D", transitive=False) == {"B", "C"}

    # Transitive lookups
    assert graph.get_downstream("A", transitive=True) == {"B", "C", "D"}
    assert graph.get_upstream("D", transitive=True) == {"A", "B", "C"}


def test_cycle_detection_returns_exact_cycle_path():
    tasks = ["A", "B", "C"]
    deps = [
        Dependency("A", "B"),
        Dependency("B", "C"),
        Dependency("C", "A"),
    ]
    graph = TaskGraph(tasks, deps)
    cycle = graph.find_cycle()
    assert cycle is not None
    # Path forms a complete loop
    assert cycle[0] == cycle[-1]
    assert len(cycle) == 4

    with pytest.raises(CycleDetectedError) as exc_info:
        graph.validate_dag()
    assert exc_info.value.cycle_path == cycle


def test_self_dependency_rejected():
    graph = TaskGraph(["A"], [Dependency("A", "A")])
    assert graph.find_cycle() == ["A", "A"]
    with pytest.raises(SelfDependencyError):
        graph.validate_dag()


def test_missing_task_in_dependency():
    with pytest.raises(TaskNotFoundError) as exc_info:
        TaskGraph(["A"], [Dependency("A", "NON_EXISTENT")])
    assert "NON_EXISTENT" in str(exc_info.value)
