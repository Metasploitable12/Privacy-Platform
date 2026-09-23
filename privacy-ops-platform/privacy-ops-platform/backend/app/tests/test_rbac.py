import uuid

import pytest
from fastapi import HTTPException

from app.core.rbac import get_user_permissions, require_permission
from app.schemas.ropa import ProcessingActivityCreate
from app.services import ropa_service
from app.tests.conftest import make_user_with_role

pytestmark = pytest.mark.asyncio


async def test_read_only_user_cannot_create_ropa(db_session, tenant_id):
    user = await make_user_with_role(db_session, tenant_id, "READ_ONLY_USER")
    perms = await get_user_permissions(db_session, user)
    assert "ROPA_CREATE" not in perms
    assert "ROPA_VIEW" in perms


async def test_privacy_analyst_can_create_but_not_approve(db_session, tenant_id):
    user = await make_user_with_role(db_session, tenant_id, "PRIVACY_ANALYST")
    perms = await get_user_permissions(db_session, user)
    assert "ROPA_CREATE" in perms
    assert "ROPA_APPROVE" not in perms


async def test_require_permission_denies_when_missing(db_session, tenant_id):
    user = await make_user_with_role(db_session, tenant_id, "READ_ONLY_USER")
    check = require_permission("ROPA_DELETE")
    with pytest.raises(HTTPException) as exc_info:
        await check(user=user, db=db_session)
    assert exc_info.value.status_code == 403


async def test_cross_tenant_ropa_is_not_visible(db_session, tenant_id):
    """
    Guards the Threat Model's "Information Disclosure" concern: a ROPA
    created under one tenant must be invisible (404, not leaked) when
    queried under a different tenant_id.
    """
    other_tenant_id = str(uuid.uuid4())
    user = await make_user_with_role(db_session, tenant_id, "PRIVACY_ADMIN")

    activity = await ropa_service.create_processing_activity(
        db_session,
        tenant_id=tenant_id,
        user_id=user.id,
        data=ProcessingActivityCreate(name="Customer Support Records"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await ropa_service.get_processing_activity(
            db_session, tenant_id=other_tenant_id, activity_id=activity.id
        )
    assert exc_info.value.status_code == 404
