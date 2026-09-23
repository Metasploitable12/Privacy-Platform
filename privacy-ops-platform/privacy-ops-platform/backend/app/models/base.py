import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def gen_uuid() -> str:
    return str(uuid.uuid4())


class UUIDPKMixin:
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)


class TenantScopedMixin:
    """
    Every major table carries tenant_id. Repository/service code must
    always filter by tenant_id — this is a schema-level reminder, not an
    automatic enforcement (SQLAlchemy doesn't do row-level security by
    itself); see docs/architecture.md Threat Model, "Information Disclosure"
    for why this matters and app/tests/test_rbac.py for a cross-tenant test.
    """
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)


class AuditColumnsMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
