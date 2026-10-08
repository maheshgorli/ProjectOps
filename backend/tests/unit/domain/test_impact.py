"""Golden delay scenario test and impact analysis verification.

Scenario:
E-Commerce Application with 4 members, 16 tasks, and core critical chain:
T-DB-01 (Database Schema) -> T-BE-02 (Backend API) -> T-FE-03 (Frontend Integration)
-> T-QA-02 (Integration Testing) -> T-OPS-01 (Deployment).

Golden Test:
Delay 'Backend API' (T-BE-02) by 2 working days.
Assert:
- Directly affected tasks include Frontend Integration (T-FE-03).
- Indirectly affected tasks include Integration Testing (T-QA-02) and Deployment (T-OPS-01).
- The project end date shifts by exactly 2 working days.
"""

from backend.app.domain.calendar import working_days_between
from backend.app.domain.impact import calculate_delay_impact
from backend.app.domain.scheduler import schedule_project
from backend.tests.fixtures.ecommerce import (
    PROJECT_DEADLINE,
    PROJECT_START_DATE,
    get_ecommerce_dependencies,
    get_ecommerce_members,
    get_ecommerce_tasks,
)


def test_golden_ecommerce_backend_api_delay_scenario():
    """Hand-calculated mathematical verification of delay propagation:

    1. In the baseline schedule:
       - T-DB-01 (3d) finishes Wednesday Nov 4.
       - T-BE-01 (2d) finishes Friday Nov 6.
       - T-BE-02 (4d) starts Monday Nov 9 and finishes Thursday Nov 12.
       - T-FE-03 (4d, Frontend Integration) starts Friday Nov 13, finishing Wednesday Nov 18.
       - T-QA-02 (4d, Integration Testing) starts Thursday Nov 19, finishing Tuesday Nov 24.
       - Downstream E2E and Deployment chain finishes at baseline_end_date.

    2. Applying a +2 working days delay to T-BE-02 ('Backend API'):
       - T-BE-02 now takes 6 working days, finishing on Monday Nov 16 (+2 working days).
       - T-FE-03 ('Frontend Integration') is directly blocked and pushes out by +2 working days.
       - T-QA-02 ('Integration Testing') is transitively pushed out by +2 working days.
       - T-OPS-01 ('Deployment') is transitively pushed out by +2 working days.
       - Total shift in project end date = exactly 2 working days.
    """
    tasks = get_ecommerce_tasks()
    deps = get_ecommerce_dependencies()
    members = get_ecommerce_members()

    baseline_schedule = schedule_project(
        tasks=tasks,
        dependencies=deps,
        members=members,
        project_start_date=PROJECT_START_DATE,
        deadline=PROJECT_DEADLINE,
    )
    baseline_end_date = baseline_schedule.project_end_date

    # Run the delay impact analysis: delay 'T-BE-02' by 2 working days
    impact_report = calculate_delay_impact(
        task_id="T-BE-02",
        delay_working_days=2,
        tasks=tasks,
        dependencies=deps,
        members=members,
        project_start_date=PROJECT_START_DATE,
        deadline=PROJECT_DEADLINE,
    )

    # 1. Assert delayed task identification
    assert impact_report.delayed_task_id == "T-BE-02"
    assert impact_report.delay_days == 2

    # 2. Assert directly affected tasks include Frontend Integration (T-FE-03)
    assert "T-FE-03" in impact_report.directly_affected_task_ids

    # 3. Assert indirectly affected tasks include Integration Testing (T-QA-02)
    # and Deployment (T-OPS-01)
    assert "T-QA-02" in impact_report.indirectly_affected_task_ids
    assert "T-OPS-01" in impact_report.indirectly_affected_task_ids

    # 4. Assert affected team members include Bob, Alice, David
    assert "m-bob" in impact_report.affected_member_ids
    assert "m-alice" in impact_report.affected_member_ids
    assert "m-david" in impact_report.affected_member_ids

    # 5. Assert baseline and projected end dates match hand calculation
    assert impact_report.original_project_end_date == baseline_end_date
    assert impact_report.projected_project_end_date > baseline_end_date

    # 6. Assert exact end-date shift is 2 working days
    assert impact_report.end_date_shift_working_days == 2
    actual_shift = (
        working_days_between(
            impact_report.original_project_end_date,
            impact_report.projected_project_end_date,
        )
        - 1
    )
    assert actual_shift == 2
