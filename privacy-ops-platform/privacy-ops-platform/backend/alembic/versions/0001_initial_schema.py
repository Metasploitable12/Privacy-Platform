"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-23

Creates every Phase 1 table (users, roles, permissions, processing
activities, data assets, evidence, audit logs, record versions) and, per
docs/architecture.md's Security Architecture, revokes UPDATE/DELETE on
audit_logs from the application's database role so the append-only
guarantee holds even against a bug in application code, not just against
missing application code paths.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
    )

    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column(
            "permission_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("permissions.id"), nullable=False
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("oidc_subject", sa.String(255), unique=True, nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_super_admin", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=False), nullable=True),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("roles.id"), nullable=False),
    )

    op.create_table(
        "processing_activities",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("business_function", sa.String(255), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("business_owner_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("processing_owner_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("privacy_owner_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("purpose", sa.Text, nullable=True),
        sa.Column("secondary_purpose", sa.Text, nullable=True),
        sa.Column("controller_type", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("last_reviewed_date", sa.Date, nullable=True),
        sa.Column("next_review_date", sa.Date, nullable=True),
        sa.Column("review_frequency_months", sa.Integer, nullable=True),
        sa.Column("data_subject_categories", sa.Text, nullable=True),
        sa.Column("personal_data_categories", sa.Text, nullable=True),
        sa.Column("legal_basis", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=False), nullable=True),
    )

    op.create_table(
        "data_assets",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("classification", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=False), nullable=True),
    )

    op.create_table(
        "asset_processing_activity",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("data_assets.id"), nullable=False),
        sa.Column(
            "processing_activity_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("processing_activities.id"),
            nullable=False,
        ),
    )

    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("evidence_type", sa.String(64), nullable=False),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("classification", sa.String(64), nullable=True),
        sa.Column("expiry_date", sa.Date, nullable=True),
        sa.Column("linked_object_type", sa.String(64), nullable=False),
        sa.Column("linked_object_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=False), nullable=True),
    )

    op.create_table(
        "record_versions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("object_type", sa.String(64), nullable=False, index=True),
        sa.Column("object_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("snapshot", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("object_type", sa.String(64), nullable=False, index=True),
        sa.Column("object_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("previous_value", postgresql.JSONB, nullable=True),
        sa.Column("new_value", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
    )

    # --- Append-only enforcement at the database level ---
    # NOTE: this assumes the app connects as a role named in DATABASE_URL
    # that is NOT the table owner. In a real deployment, provision a
    # dedicated `privacy_app` role (see .env.example) that owns no tables
    # itself, and run migrations as a separate, more privileged `migrator`
    # role. Adjust the role name below to match your deployment.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = current_user) THEN
            EXECUTE format('REVOKE UPDATE, DELETE ON audit_logs FROM %I', current_user);
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("record_versions")
    op.drop_table("evidence")
    op.drop_table("asset_processing_activity")
    op.drop_table("data_assets")
    op.drop_table("processing_activities")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
