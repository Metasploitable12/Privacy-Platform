from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditColumnsMixin, TenantScopedMixin, UUIDPKMixin

ROPA_STATUSES = ("DRAFT", "IN_REVIEW", "APPROVED", "REJECTED", "RETIRED")


class ProcessingActivity(Base, UUIDPKMixin, TenantScopedMixin, AuditColumnsMixin):
    """
    The central ROPA record. Field set is a deliberate Phase-1 subset of the
    full ROPA schema in docs/architecture.md — additional field groups
    (transfers, retention, security, recipients as first-class linked
    tables) land as those modules are built, without breaking this table.
    """
    __tablename__ = "processing_activities"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_function: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    business_owner_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    processing_owner_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    privacy_owner_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    secondary_purpose: Mapped[str | None] = mapped_column(Text, nullable=True)

    controller_type: Mapped[str | None] = mapped_column(String(64), nullable=True)  # controller/joint/processor

    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    last_reviewed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    next_review_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    review_frequency_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Free-text/JSON-ish fields kept simple in Phase 1; normalize into
    # linked tables (data_categories, legal_bases, recipients, etc.) as
    # those modules are built per the phased plan.
    data_subject_categories: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated for now
    personal_data_categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_basis: Mapped[str | None] = mapped_column(String(128), nullable=True)
