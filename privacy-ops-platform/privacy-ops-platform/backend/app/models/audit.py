from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import UUIDPKMixin


class AuditLog(Base, UUIDPKMixin):
    """
    Append-only by design: no update()/delete() path exists anywhere in the
    app for this table, and the DB role the app connects as has REVOKE
    UPDATE, DELETE on this table at the Postgres level (see the initial
    Alembic migration). This is deliberate defense in depth — even a bug
    in application code cannot silently rewrite history.
    """
    __tablename__ = "audit_logs"

    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # CREATE/UPDATE/DELETE/APPROVE/EXPORT/...
    object_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    object_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    previous_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecordVersion(Base, UUIDPKMixin):
    __tablename__ = "record_versions"

    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    object_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
