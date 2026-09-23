from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import require_permission
from app.core.tenancy import get_current_tenant_id
from app.models.ropa import ProcessingActivity
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class DashboardMetrics(BaseModel):
    total_processing_activities: int
    draft_count: int
    in_review_count: int
    approved_count: int
    retired_count: int
    approved_percentage: float


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ROPA_VIEW")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ProcessingActivity.status, func.count())
        .where(ProcessingActivity.tenant_id == tenant_id)
        .group_by(ProcessingActivity.status)
    )
    result = await db.execute(stmt)
    counts = {status: count for status, count in result.all()}

    total = sum(counts.values())
    approved = counts.get("APPROVED", 0)

    return DashboardMetrics(
        total_processing_activities=total,
        draft_count=counts.get("DRAFT", 0),
        in_review_count=counts.get("IN_REVIEW", 0),
        approved_count=approved,
        retired_count=counts.get("RETIRED", 0),
        approved_percentage=round((approved / total * 100), 1) if total else 0.0,
    )
