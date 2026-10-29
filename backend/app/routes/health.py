from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.database import db_manager
from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
@router.get("/api/health", response_model=HealthResponse)
async def get_system_health():
    db_health = await db_manager.check_health()
    now_iso = datetime.now(timezone.utc).isoformat()
    return HealthResponse(
        status="ok",
        database=db_health["status"],
        engine=db_health.get("engine", "MongoDB"),
        timestamp=now_iso,
        version="1.0.0",
        details=db_health
    )
