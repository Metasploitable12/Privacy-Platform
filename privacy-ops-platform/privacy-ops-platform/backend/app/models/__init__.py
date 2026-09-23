"""
Import every model module here so Alembic's autogenerate and Base.metadata
see the full schema when this package is imported.
"""
from app.models import asset, audit, evidence, rbac, ropa, user  # noqa: F401
