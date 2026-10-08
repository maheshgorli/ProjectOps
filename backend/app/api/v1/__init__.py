"""API v1 router assembly."""

from fastapi import APIRouter

from backend.app.api.v1.agent_loop import router as agent_loop_router
from backend.app.api.v1.ai import router as ai_router
from backend.app.api.v1.approvals import router as approvals_router
from backend.app.api.v1.github import router as github_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.history import router as history_router
from backend.app.api.v1.plans import router as plans_router
from backend.app.api.v1.projects import router as projects_router
from backend.app.api.v1.risks import router as risks_router
from backend.app.api.v1.schedule import router as schedule_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(plans_router)
api_v1_router.include_router(schedule_router)
api_v1_router.include_router(risks_router)
api_v1_router.include_router(history_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(approvals_router)
api_v1_router.include_router(github_router)
api_v1_router.include_router(agent_loop_router)

__all__ = ["api_v1_router"]
