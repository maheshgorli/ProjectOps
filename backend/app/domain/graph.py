"""Directed Acyclic Graph (DAG) operations, cycle detection, and topological sorting.

Pure Python, completely deterministic with tie-breaking on task IDs.
"""

from collections import defaultdict, deque
from collections.abc import Iterable, Sequence

from backend.app.domain.models import Dependency, Task


class GraphError(Exception):
    """Base exception for graph validation errors."""

    pass


class TaskNotFoundError(GraphError):
    """Raised when a dependency references a task not present in the plan."""

    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task '{task_id}' referenced in dependency does not exist in graph.")
        self.task_id = task_id


class CycleDetectedError(GraphError):
    """Raised when a circular dependency is detected in the task graph."""

    def __init__(self, cycle_path: Sequence[str]) -> None:
        formatted_path = " -> ".join(cycle_path)
        super().__init__(f"Circular dependency detected in graph: {formatted_path}")
        self.cycle_path = list(cycle_path)


class TaskGraph:
    """Directed graph representing task dependencies."""

    def __init__(
        self,
        tasks: Iterable[Task | str],
        dependencies: Iterable[Dependency],
    ) -> None:
        self.task_ids: set[str] = set()
        for item in tasks:
            if isinstance(item, Task):
                self.task_ids.add(item.id)
            else:
                self.task_ids.add(item)

        self.successors: dict[str, list[str]] = defaultdict(list)
        self.predecessors: dict[str, list[str]] = defaultdict(list)
        self.dependencies: list[Dependency] = list(dependencies)

        for dep in dependencies:
            if dep.predecessor_id not in self.task_ids:
                raise TaskNotFoundError(dep.predecessor_id)
            if dep.successor_id not in self.task_ids:
                raise TaskNotFoundError(dep.successor_id)

            self.successors[dep.predecessor_id].append(dep.successor_id)
            self.predecessors[dep.successor_id].append(dep.predecessor_id)

        # Sort adjacency lists for deterministic traversal
        for succ_list in self.successors.values():
            succ_list.sort()
        for pred_list in self.predecessors.values():
            pred_list.sort()

    def find_cycle(self) -> list[str] | None:
        """
        Detect any cycle in the graph using DFS with 3-state coloring:
        0 = unvisited, 1 = visiting (in recursion stack), 2 = visited.

        Returns the cycle path as a list of task IDs [A, B, C, A], or None if DAG.
        """
        visited: dict[str, int] = {t_id: 0 for t_id in self.task_ids}
        parent: dict[str, str | None] = {t_id: None for t_id in self.task_ids}

        # Deterministic order
        sorted_nodes = sorted(self.task_ids)

        for start_node in sorted_nodes:
            if visited[start_node] != 0:
                continue

            stack: list[tuple[str, int]] = [(start_node, 0)]
            visited[start_node] = 1

            while stack:
                u, succ_idx = stack[-1]
                neighbors = self.successors[u]

                if succ_idx < len(neighbors):
                    v = neighbors[succ_idx]
                    # Update index on stack for next iteration
                    stack[-1] = (u, succ_idx + 1)

                    if visited[v] == 1:
                        # Cycle detected! Reconstruct the cycle path
                        cycle: list[str] = [v]
                        curr = u
                        while curr != v:
                            cycle.append(curr)
                            curr = parent[curr]  # type: ignore
                        cycle.append(v)
                        cycle.reverse()
                        return cycle

                    elif visited[v] == 0:
                        visited[v] = 1
                        parent[v] = u
                        stack.append((v, 0))
                else:
                    visited[u] = 2
                    stack.pop()

        return None

    def validate_dag(self) -> None:
        """Raise CycleDetectedError if the graph contains any cycle."""
        cycle = self.find_cycle()
        if cycle:
            raise CycleDetectedError(cycle)

    def topological_sort(self) -> list[str]:
        """
        Produce a deterministic topological ordering using Kahn's algorithm
        with a sorted priority/tie-break queue.

        Raises CycleDetectedError if the graph has a cycle.
        """
        in_degree: dict[str, int] = {t_id: len(self.predecessors[t_id]) for t_id in self.task_ids}

        # Zero in-degree nodes sorted alphabetically for deterministic output
        zero_in_degree = sorted([t_id for t_id, deg in in_degree.items() if deg == 0])
        queue = deque(zero_in_degree)

        sorted_order: list[str] = []

        while queue:
            # Pop smallest node alphabetically among available nodes
            # To ensure strict alphabetical tie breaking when new 0 in-degree nodes appear:
            queue_list = sorted(list(queue))
            u = queue_list.pop(0)
            queue = deque(queue_list)

            sorted_order.append(u)

            for v in self.successors[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        if len(sorted_order) != len(self.task_ids):
            # Graph has cycle
            self.validate_dag()
            # If for some reason validate_dag didn't raise, raise generic
            raise CycleDetectedError(["cycle"])

        return sorted_order
