from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import require_permission
from app.core.tenancy import get_current_tenant_id
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    timestamp: datetime
    action: str
    object_type: str
    object_id: str
    previous_value: dict | None = None
    new_value: dict | None = None
    reason: str | None = None


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    object_type: str | None = None,
    object_id: str | None = None,
    limit: int = Query(default=100, le=500),
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("AUDIT_LOG_VIEW")),
    db: AsyncSession = Depends(get_db),
):
    """
    Answers "who changed this ROPA and what changed?" (docs/architecture.md
    Section 21). Always tenant-scoped and always read-only — there is no
    write endpoint here by design.
    """
    stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if object_type:
        stmt = stmt.where(AuditLog.object_type == object_type)
    if object_id:
        stmt = stmt.where(AuditLog.object_id == object_id)
    stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
