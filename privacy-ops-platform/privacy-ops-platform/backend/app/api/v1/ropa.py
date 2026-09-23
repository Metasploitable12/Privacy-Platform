from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import require_permission
from app.core.tenancy import get_current_tenant_id
from app.models.user import User
from app.schemas.ropa import (
    ProcessingActivityCreate,
    ProcessingActivityOut,
    ProcessingActivityStatusChange,
    ProcessingActivityUpdate,
    RecordVersionOut,
)
from app.services import ropa_service

router = APIRouter(prefix="/ropa", tags=["ROPA"])


@router.get("", response_model=list[ProcessingActivityOut])
async def list_ropa(
    status_filter: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ROPA_VIEW")),
    db: AsyncSession = Depends(get_db),
):
    return await ropa_service.list_processing_activities(db, tenant_id=tenant_id, status_filter=status_filter)


@router.post("", response_model=ProcessingActivityOut, status_code=201)
async def create_ropa(
    payload: ProcessingActivityCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ROPA_CREATE")),
    db: AsyncSession = Depends(get_db),
):
    return await ropa_service.create_processing_activity(
        db, tenant_id=tenant_id, user_id=user.id, data=payload
    )


@router.get("/{activity_id}", response_model=ProcessingActivityOut)
async def get_ropa(
    activity_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ROPA_VIEW")),
    db: AsyncSession = Depends(get_db),
):
    return await ropa_service.get_processing_activity(db, tenant_id=tenant_id, activity_id=activity_id)


@router.put("/{activity_id}", response_model=ProcessingActivityOut)
async def update_ropa(
    activity_id: str,
    payload: ProcessingActivityUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ROPA_EDIT")),
    db: AsyncSession = Depends(get_db),
):
    return await ropa_service.update_processing_activity(
        db, tenant_id=tenant_id, user_id=user.id, activity_id=activity_id, data=payload
    )


@router.post("/{activity_id}/status", response_model=ProcessingActivityOut)
async def change_ropa_status(
    activity_id: str,
    payload: ProcessingActivityStatusChange,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ROPA_EDIT")),
    db: AsyncSession = Depends(get_db),
):
    # Approval specifically requires the stronger ROPA_APPROVE permission,
    # checked in addition to the base ROPA_EDIT dependency above.
    if payload.new_status == "APPROVED":
        await require_permission("ROPA_APPROVE")(user=user, db=db)
    return await ropa_service.change_status(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        activity_id=activity_id,
        new_status=payload.new_status,
        reason=payload.reason,
    )


@router.get("/{activity_id}/versions", response_model=list[RecordVersionOut])
async def get_ropa_versions(
    activity_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ROPA_VIEW")),
    db: AsyncSession = Depends(get_db),
):
    return await ropa_service.list_versions(db, tenant_id=tenant_id, activity_id=activity_id)
