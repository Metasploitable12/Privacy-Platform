from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditColumnsMixin, TenantScopedMixin, UUIDPKMixin


class DataAsset(Base, UUIDPKMixin, TenantScopedMixin, AuditColumnsMixin):
    __tablename__ = "data_assets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)  # app/db/saas/cloud/storage/endpoint
    owner_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    classification: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AssetProcessingActivityLink(Base, UUIDPKMixin):
    __tablename__ = "asset_processing_activity"

    asset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("data_assets.id"), nullable=False
    )
    processing_activity_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("processing_activities.id"), nullable=False
    )
