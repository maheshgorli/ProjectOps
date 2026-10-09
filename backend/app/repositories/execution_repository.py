"""Repository for managing mutable task execution states."""

from collections.abc import Sequence
from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.clock import Clock, SystemClock
from backend.app.domain.models import ProjectPlan, Task, TaskStatus
from backend.app.models.execution import TaskExecutionStateORM
from backend.app.schemas.task import TaskMergedResponse


class ExecutionRepository:
    """Provides queries and mutations for runtime task execution states."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_task_state(self, project_id: str, task_id: str) -> TaskExecutionStateORM | None:
        """Fetch the execution state row for a specific task within a project."""
        stmt = select(TaskExecutionStateORM).where(
            TaskExecutionStateORM.project_id == project_id,
            TaskExecutionStateORM.task_id == task_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_task_states(self, project_id: str) -> Sequence[TaskExecutionStateORM]:
        """List all task execution state rows for a project."""
        stmt = select(TaskExecutionStateORM).where(TaskExecutionStateORM.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert_task_state(
        self,
        project_id: str,
        task_id: str,
        status: str,
        actual_start: date | None = None,
        actual_finish: date | None = None,
        actual_hours: float | None = None,
        percent_complete: int | None = None,
        blocked_reason: str | None = None,
        updated_by: str = "system",
        updated_at: datetime | None = None,
    ) -> TaskExecutionStateORM:
        """Create or update the runtime execution state of a task."""
        state = await self.get_task_state(project_id, task_id)
        now = updated_at or datetime.now(UTC)

        if state is None:
            state = TaskExecutionStateORM(
                id=str(uuid4()),
                project_id=project_id,
                task_id=task_id,
                status=status,
                actual_start=actual_start,
                actual_finish=actual_finish,
                actual_hours=actual_hours or 0.0,
                percent_complete=percent_complete
                if percent_complete is not None
                else (100 if status == TaskStatus.COMPLETED.value else 0),
                blocked_reason=blocked_reason,
                updated_by=updated_by,
                updated_at=now,
            )
            self.session.add(state)
        else:
            state.status = status
            if actual_start is not None:
                state.actual_start = actual_start
            if actual_finish is not None:
                state.actual_finish = actual_finish
            if actual_hours is not None:
                state.actual_hours = actual_hours
            if percent_complete is not None:
                state.percent_complete = percent_complete
            elif status == TaskStatus.COMPLETED.value:
                state.percent_complete = 100
            if blocked_reason is not None:
                state.blocked_reason = blocked_reason
            state.updated_by = updated_by
            state.updated_at = now

        await self.session.flush()
        return state

    async def backfill_execution_states_from_plan(
        self, project_id: str, plan: ProjectPlan
    ) -> dict[str, TaskExecutionStateORM]:
        """Ensure every task in the active plan has a backing execution state row."""
        existing_states = {s.task_id: s for s in await self.list_task_states(project_id)}
        for task in plan.tasks.values():
            if task.id not in existing_states:
                new_state = await self.upsert_task_state(
                    project_id=project_id,
                    task_id=task.id,
                    status=task.status.value,
                    actual_hours=0.0,
                    percent_complete=100 if task.status == TaskStatus.COMPLETED else 0,
                    updated_by="system",
                )
                existing_states[task.id] = new_state
        return existing_states

    async def get_merged_tasks(
        self,
        project_id: str,
        plan: ProjectPlan,
        clock: Clock | None = None,
    ) -> list[TaskMergedResponse]:
        """Return all tasks from the active plan merged with runtime execution states."""
        clk = clock or SystemClock()
        states = await self.backfill_execution_states_from_plan(project_id, plan)

        # Build dependency lookup
        predecessors_by_task: dict[str, list[str]] = {t_id: [] for t_id in plan.tasks}
        for dep in plan.dependencies:
            if dep.successor_id in predecessors_by_task:
                predecessors_by_task[dep.successor_id].append(dep.predecessor_id)

        merged: list[TaskMergedResponse] = []
        for task in plan.tasks.values():
            state = states.get(task.id)
            current_status = state.status if state else task.status.value

            # OVERDUE is derived: non-completed task past due date
            is_overdue = False
            if current_status != TaskStatus.COMPLETED.value and task.due_date is not None:
                is_overdue = task.due_date < clk.now().date()

            merged.append(
                TaskMergedResponse(
                    id=task.id,
                    project_id=project_id,
                    title=task.title,
                    description=task.description,
                    status=current_status,
                    estimated_hours=task.estimated_hours,
                    assigned_to_id=task.assigned_to_id,
                    planned_start_date=task.start_date,
                    planned_due_date=task.due_date,
                    actual_start=state.actual_start if state else None,
                    actual_finish=state.actual_finish if state else None,
                    actual_hours=state.actual_hours if state else 0.0,
                    percent_complete=state.percent_complete if state else 0,
                    blocked_reason=state.blocked_reason if state else None,
                    is_overdue=is_overdue,
                    dependencies=predecessors_by_task.get(task.id, []),
                    updated_by=state.updated_by if state else "system",
                    updated_at=state.updated_at if state else datetime.now(UTC),
                )
            )

        return merged

    async def get_plan_with_execution_state(
        self,
        project_id: str,
        plan: ProjectPlan,
    ) -> ProjectPlan:
        """
        Return a ProjectPlan with runtime task execution states applied.

        Keeps domain calculations deterministic and truthful to execution reality.
        """
        states = await self.backfill_execution_states_from_plan(project_id, plan)
        merged_tasks: dict[str, Task] = {}

        for t_id, task in plan.tasks.items():
            state = states.get(t_id)
            if state:
                status_val = TaskStatus(state.status)
                completed_at = (
                    datetime.combine(state.actual_finish, datetime.min.time(), UTC)
                    if state.actual_finish
                    else task.completed_at
                )
                merged_tasks[t_id] = Task(
                    id=task.id,
                    title=task.title,
                    description=task.description,
                    status=status_val,
                    estimated_hours=task.estimated_hours,
                    duration_working_days=task.duration_working_days,
                    required_skills=list(task.required_skills),
                    assigned_to_id=task.assigned_to_id,
                    due_date=task.due_date,
                    start_date=state.actual_start or task.start_date,
                    completed_at=completed_at,
                )
            else:
                merged_tasks[t_id] = task

        return ProjectPlan(
            id=plan.id,
            project_id=plan.project_id,
            version=plan.version,
            name=plan.name,
            tasks=merged_tasks,
            dependencies=plan.dependencies,
            members=plan.members,
            target_completion_date=plan.target_completion_date,
            created_at=plan.created_at,
            created_by=plan.created_by,
        )
