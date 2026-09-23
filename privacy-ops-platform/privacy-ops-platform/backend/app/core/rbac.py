"""
RBAC enforcement.

CRITICAL: authorization is enforced HERE, server-side, on every route via
`require_permission(...)` as a FastAPI dependency. The frontend may also
hide/disable UI based on permissions, but that is a UX convenience only —
it is never the security boundary. Never add a route without an explicit
permission requirement (or an explicit, reviewed decision that a route is
intentionally public, e.g. health checks).
"""
from pathlib import Path

import yaml
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.rbac import Permission, Role, RolePermission
from app.models.user import User, UserRole

RBAC_MATRIX_PATH = Path(__file__).resolve().parents[3] / "rbac_matrix.yaml"


async def get_user_permissions(db: AsyncSession, user: User) -> set[str]:
    """Resolve the full set of permission names granted to a user via their roles."""
    stmt = (
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.all()}


def require_permission(permission_name: str):
    """
    FastAPI dependency factory. Usage on a route:

        @router.post("/ropa", dependencies=[Depends(require_permission("ROPA_CREATE"))])

    Raises 403 if the current user lacks the permission. This check happens
    before the route handler body runs — no handler should assume it was
    reached legitimately without this guard.
    """

    async def _check(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        granted = await get_user_permissions(db, user)
        if permission_name not in granted and not user.is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission_name}",
            )
        return user

    return _check


def load_rbac_matrix() -> dict:
    with open(RBAC_MATRIX_PATH) as f:
        return yaml.safe_load(f)


async def seed_rbac_from_yaml(db: AsyncSession) -> None:
    """
    Idempotent seed: ensures every role/permission/role-permission mapping
    in rbac_matrix.yaml exists in the database. Run on backend startup.
    Editing the YAML and restarting is how admins change the matrix in
    Phase 1 — a Phase 2+ admin UI can later write to these same tables.
    """
    matrix = load_rbac_matrix()

    existing_roles = {r.name: r for r in (await db.execute(select(Role))).scalars().all()}
    for role_name in matrix["roles"]:
        if role_name not in existing_roles:
            role = Role(name=role_name)
            db.add(role)
            existing_roles[role_name] = role
    await db.flush()

    existing_perms = {p.name: p for p in (await db.execute(select(Permission))).scalars().all()}
    for perm_name in matrix["permissions"]:
        if perm_name not in existing_perms:
            perm = Permission(name=perm_name)
            db.add(perm)
            existing_perms[perm_name] = perm
    await db.flush()

    existing_mappings = {
        (rp.role_id, rp.permission_id)
        for rp in (await db.execute(select(RolePermission))).scalars().all()
    }
    for perm_name, role_names in matrix["permissions"].items():
        perm = existing_perms[perm_name]
        for role_name in role_names:
            role = existing_roles[role_name]
            key = (role.id, perm.id)
            if key not in existing_mappings:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                existing_mappings.add(key)

    await db.commit()
