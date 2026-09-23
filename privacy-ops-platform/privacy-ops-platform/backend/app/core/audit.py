"""
Append-only audit logging.

Every mutating action across the app must call `write_audit_log(...)`
inside the SAME transaction as the mutation it's recording, so a failed
audit write rolls back the change too (see docs/architecture.md,
Security Architecture: "Audit"). The database role the app connects as
has no UPDATE/DELETE grant on audit_logs (see alembic migration
0001_initial_schema.py) — this module has no update/delete function
by design, not by omission.
"""
import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


def _json_safe(value: Any) -> Any:
    """Best-effort JSON-safe serialization for audit diff payloads."""
    if value is None:
        return None
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


async def write_audit_log(
    db: AsyncSession,
    *,
    user_id: str,
    tenant_id: str,
    action: str,
    object_type: str,
    object_id: str,
    previous_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
    reason: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        previous_value=_json_safe(previous_value),
        new_value=_json_safe(new_value),
        ip_address=ip_address,
        reason=reason,
    )
    db.add(entry)
    # Deliberately no commit here — caller commits as part of its own
    # transaction so the mutation and its audit record are atomic.
