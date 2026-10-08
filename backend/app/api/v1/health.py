"""Health check API endpoint."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["system"])


@router.get("", summary="System health check")
async def health_check() -> dict[str, str]:
    """Return 200 OK indicating the API service is operational."""
    return {"status": "ok", "service": "ProjectOps"}
