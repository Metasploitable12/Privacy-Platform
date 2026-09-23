import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.audit import AuditLog
from app.schemas.ropa import ProcessingActivityCreate, ProcessingActivityUpdate
from app.services import ropa_service
from app.tests.conftest import make_user_with_role

pytestmark = pytest.mark.asyncio


async def test_create_ropa_writes_version_1_and_audit_entry(db_session, tenant_id):
    user = await make_user_with_role(db_session, tenant_id, "PRIVACY_ADMIN")

    activity = await ropa_service.create_processing_activity(
        db_session,
        tenant_id=tenant_id,
        user_id=user.id,
        data=ProcessingActivityCreate(name="Payroll Processing", purpose="Pay employees"),
    )

    assert activity.status == "DRAFT"
    assert activity.version == 1

    versions = await ropa_service.list_versions(db_session, tenant_id=tenant_id, activity_id=activity.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.object_id == activity.id, AuditLog.action == "CREATE")
    )
    assert result.scalar_one_or_none() is not None


async def test_approved_ropa_cannot_be_edited_in_place(db_session, tenant_id):
    user = await make_user_with_role(db_session, tenant_id, "PRIVACY_ADMIN")
    activity = await ropa_service.create_processing_activity(
        db_session, tenant_id=tenant_id, user_id=user.id, data=ProcessingActivityCreate(name="Marketing Emails")
    )
    activity = await ropa_service.change_status(
        db_session, tenant_id=tenant_id, user_id=user.id, activity_id=activity.id, new_status="IN_REVIEW"
    )
    activity = await ropa_service.change_status(
        db_session, tenant_id=tenant_id, user_id=user.id, activity_id=activity.id, new_status="APPROVED"
    )
    assert activity.status == "APPROVED"

    with pytest.raises(HTTPException) as exc_info:
        await ropa_service.update_processing_activity(
            db_session,
            tenant_id=tenant_id,
            user_id=user.id,
            activity_id=activity.id,
            data=ProcessingActivityUpdate(name="Changed without going through review"),
        )
    assert exc_info.value.status_code == 409


async def test_invalid_status_transition_is_rejected(db_session, tenant_id):
    user = await make_user_with_role(db_session, tenant_id, "PRIVACY_ADMIN")
    activity = await ropa_service.create_processing_activity(
        db_session, tenant_id=tenant_id, user_id=user.id, data=ProcessingActivityCreate(name="Vendor Onboarding")
    )

    # DRAFT -> APPROVED is not an allowed direct transition (must pass through IN_REVIEW)
    with pytest.raises(HTTPException) as exc_info:
        await ropa_service.change_status(
            db_session, tenant_id=tenant_id, user_id=user.id, activity_id=activity.id, new_status="APPROVED"
        )
    assert exc_info.value.status_code == 409


async def test_edit_increments_version_and_snapshots(db_session, tenant_id):
    user = await make_user_with_role(db_session, tenant_id, "PRIVACY_ADMIN")
    activity = await ropa_service.create_processing_activity(
        db_session, tenant_id=tenant_id, user_id=user.id, data=ProcessingActivityCreate(name="Support Tickets")
    )
    updated = await ropa_service.update_processing_activity(
        db_session,
        tenant_id=tenant_id,
        user_id=user.id,
        activity_id=activity.id,
        data=ProcessingActivityUpdate(description="Now includes chat transcripts"),
    )
    assert updated.version == 2
    versions = await ropa_service.list_versions(db_session, tenant_id=tenant_id, activity_id=activity.id)
    assert [v.version_number for v in versions] == [1, 2]
