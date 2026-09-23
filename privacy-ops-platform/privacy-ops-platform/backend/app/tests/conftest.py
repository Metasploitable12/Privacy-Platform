"""
These tests run against a real Postgres instance (matching production
column types like UUID/JSONB — SQLite would silently diverge from prod
behavior, which defeats the point of testing RBAC/audit/versioning). Bring
up the stack with `docker compose up -d postgres` first, then run:

    cd backend
    DATABASE_URL=postgresql+asyncpg://privacy_app:change-me@localhost:5432/privacy_ops_test pytest

or simply `docker compose exec backend pytest` once the stack is running,
which already has DATABASE_URL pointed at the compose Postgres.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.config import get_settings
from app.core.rbac import seed_rbac_from_yaml
from app.models.user import User, UserRole
from app.models.rbac import Role

settings = get_settings()


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def tenant_id() -> str:
    return str(uuid.uuid4())


async def make_user_with_role(db: AsyncSession, tenant_id: str, role_name: str) -> User:
    await seed_rbac_from_yaml(db)
    result = await db.execute(Role.__table__.select().where(Role.name == role_name))
    role_row = result.first()
    assert role_row is not None, f"Role {role_name} not found — check rbac_matrix.yaml"

    user = User(tenant_id=tenant_id, email=f"{uuid.uuid4()}@example.com", display_name="Test User")
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role_row.id))
    await db.commit()
    await db.refresh(user)
    return user
