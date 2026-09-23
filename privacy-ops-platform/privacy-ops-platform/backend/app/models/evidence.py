from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditColumnsMixin, TenantScopedMixin, UUIDPKMixin


class Evidence(Base, UUIDPKMixin, TenantScopedMixin, AuditColumnsMixin):
    __tablename__ = "evidence"

    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)  # object storage pointer, never a blob
    owner_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    classification: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expiry_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    linked_object_type: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "processing_activity"
    linked_object_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
