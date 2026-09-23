"""
Tenant-scoping helper.

Phase 1 runs single-tenant, but every major table carries `tenant_id` from
day one (see docs/architecture.md, Multi-Tenancy) so cross-tenant isolation
is a schema fact, not a future migration. This module centralizes "which
tenant is this request for" so repository code never has to guess.
"""
from fastapi import Depends

from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.user import User

settings = get_settings()


def get_current_tenant_id(user: User = Depends(get_current_user)) -> str:
    """
    Resolve the tenant for the current request from the authenticated user.
    In a future multi-tenant deployment this would also validate that the
    user is permitted to act within the requested tenant context (e.g. via
    a tenant-switch header), not just default to their home tenant.
    """
    return str(user.tenant_id)
