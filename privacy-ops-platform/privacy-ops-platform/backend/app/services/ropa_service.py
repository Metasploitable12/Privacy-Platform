"""
ROPA business logic: status-transition rules, version snapshotting, and the
audit-log write, all inside one DB transaction per operation. Routes call
into this layer rather than touching the ORM directly, so this is the one
place transition rules and audit/version behavior live.
"""
from dataclasses import asdict, is_dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.models.audit import RecordVersion
from app.models.ropa import ROPA_STATUSES, ProcessingActivity
from app.schemas.ropa import ProcessingActivityCreate, ProcessingActivityUpdate

# Allowed status transitions — mirrors docs/architecture.md Section 3
# ("Draft, Review, Approval, Rejection, Revision, Retirement, Versioning").
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"IN_REVIEW"},
    "IN_REVIEW": {"APPROVED", "REJECTED", "DRAFT"},
    "APPROVED": {"IN_REVIEW", "RETIRED"},  # re-review for a new version, or retire
    "REJECTED": {"DRAFT"},
    "RETIRED": set(),
}


def _snapshot(activity: ProcessingActivity) -> dict:
    return {
        "name": activity.name,
        "description": activity.description,
        "business_function": activity.business_function,
        "department_id": activity.department_id,
        "business_owner_id": activity.business_owner_id,
        "processing_owner_id": activity.processing_owner_id,
        "privacy_owner_id": activity.privacy_owner_id,
        "purpose": activity.purpose,
        "secondary_purpose": activity.secondary_purpose,
        "controller_type": activity.controller_type,
        "status": activity.status,
        "version": activity.version,
        "data_subject_categories": activity.data_subject_categories,
        "personal_data_categories": activity.personal_data_categories,
        "legal_basis": activity.legal_basis,
    }


async def create_processing_activity(
    db: AsyncSession, *, tenant_id: str, user_id: str, data: ProcessingActivityCreate
) -> ProcessingActivity:
    activity = ProcessingActivity(
        tenant_id=tenant_id,
        created_by=user_id,
        updated_by=user_id,
        status="DRAFT",
        version=1,
        **data.model_dump(),
    )
    db.add(activity)
    await db.flush()  # get activity.id before writing dependent rows

    db.add(
        RecordVersion(
            tenant_id=tenant_id,
            object_type="processing_activity",
            object_id=activity.id,
            version_number=1,
            snapshot=_snapshot(activity),
            created_by=user_id,
        )
    )
    await write_audit_log(
        db,
        user_id=user_id,
        tenant_id=tenant_id,
        action="CREATE",
        object_type="processing_activity",
        object_id=activity.id,
        new_value=_snapshot(activity),
    )
    await db.commit()
    await db.refresh(activity)
    return activity


async def get_processing_activity(
    db: AsyncSession, *, tenant_id: str, activity_id: str
) -> ProcessingActivity:
    result = await db.execute(
        select(ProcessingActivity).where(
            ProcessingActivity.id == activity_id,
            ProcessingActivity.tenant_id == tenant_id,  # tenant scoping enforced here, not optional
        )
    )
    activity = result.scalar_one_or_none()
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing activity not found")
    return activity


async def list_processing_activities(
    db: AsyncSession, *, tenant_id: str, status_filter: str | None = None
) -> list[ProcessingActivity]:
    stmt = select(ProcessingActivity).where(ProcessingActivity.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(ProcessingActivity.status == status_filter)
    result = await db.execute(stmt.order_by(ProcessingActivity.updated_at.desc()))
    return list(result.scalars().all())


async def update_processing_activity(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    activity_id: str,
    data: ProcessingActivityUpdate,
) -> ProcessingActivity:
    activity = await get_processing_activity(db, tenant_id=tenant_id, activity_id=activity_id)

    if activity.status == "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approved records cannot be edited in place — move to IN_REVIEW to create a new version.",
        )

    previous_snapshot = _snapshot(activity)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(activity, field, value)
    activity.updated_by = user_id
    activity.version += 1

    await db.flush()
    db.add(
        RecordVersion(
            tenant_id=tenant_id,
            object_type="processing_activity",
            object_id=activity.id,
            version_number=activity.version,
            snapshot=_snapshot(activity),
            created_by=user_id,
        )
    )
    await write_audit_log(
        db,
        user_id=user_id,
        tenant_id=tenant_id,
        action="UPDATE",
        object_type="processing_activity",
        object_id=activity.id,
        previous_value=previous_snapshot,
        new_value=_snapshot(activity),
    )
    await db.commit()
    await db.refresh(activity)
    return activity


async def change_status(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    activity_id: str,
    new_status: str,
    reason: str | None = None,
) -> ProcessingActivity:
    if new_status not in ROPA_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    activity = await get_processing_activity(db, tenant_id=tenant_id, activity_id=activity_id)
    allowed = ALLOWED_TRANSITIONS.get(activity.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from {activity.status} to {new_status}",
        )

    previous_snapshot = _snapshot(activity)
    activity.status = new_status
    activity.updated_by = user_id

    await db.flush()
    db.add(
        RecordVersion(
            tenant_id=tenant_id,
            object_type="processing_activity",
            object_id=activity.id,
            version_number=activity.version,
            snapshot=_snapshot(activity),
            created_by=user_id,
        )
    )
    await write_audit_log(
        db,
        user_id=user_id,
        tenant_id=tenant_id,
        action=f"STATUS_CHANGE:{new_status}",
        object_type="processing_activity",
        object_id=activity.id,
        previous_value=previous_snapshot,
        new_value=_snapshot(activity),
        reason=reason,
    )
    await db.commit()
    await db.refresh(activity)
    return activity


async def list_versions(
    db: AsyncSession, *, tenant_id: str, activity_id: str
) -> list[RecordVersion]:
    result = await db.execute(
        select(RecordVersion)
        .where(
            RecordVersion.tenant_id == tenant_id,
            RecordVersion.object_type == "processing_activity",
            RecordVersion.object_id == activity_id,
        )
        .order_by(RecordVersion.version_number.asc())
    )
    return list(result.scalars().all())
