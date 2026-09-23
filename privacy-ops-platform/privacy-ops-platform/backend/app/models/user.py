from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditColumnsMixin, TenantScopedMixin, UUIDPKMixin


class User(Base, UUIDPKMixin, TenantScopedMixin, AuditColumnsMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    oidc_subject: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    department_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Break-glass flag for initial bootstrap only; day-to-day authorization
    # should flow through roles/permissions, not this flag. Kept narrow and
    # logged whenever it's the deciding factor (see core/rbac.py).
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UserRole(Base, UUIDPKMixin):
    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("roles.id"), nullable=False)
