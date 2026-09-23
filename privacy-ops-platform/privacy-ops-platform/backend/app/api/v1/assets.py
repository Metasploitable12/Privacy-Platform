from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.rbac import require_permission
from app.core.tenancy import get_current_tenant_id
from app.models.asset import AssetProcessingActivityLink, DataAsset
from app.models.user import User

router = APIRouter(prefix="/assets", tags=["Data Inventory"])


class DataAssetCreate(BaseModel):
    name: str
    asset_type: str
    owner_id: str | None = None
    classification: str | None = None


class DataAssetOut(DataAssetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class AssetLinkCreate(BaseModel):
    processing_activity_id: str


@router.get("", response_model=list[DataAssetOut])
async def list_assets(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ASSET_VIEW")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DataAsset).where(DataAsset.tenant_id == tenant_id))
    return list(result.scalars().all())


@router.post("", response_model=DataAssetOut, status_code=201)
async def create_asset(
    payload: DataAssetCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ASSET_CREATE")),
    db: AsyncSession = Depends(get_db),
):
    asset = DataAsset(tenant_id=tenant_id, created_by=user.id, updated_by=user.id, **payload.model_dump())
    db.add(asset)
    await db.flush()
    await write_audit_log(
        db,
        user_id=user.id,
        tenant_id=tenant_id,
        action="CREATE",
        object_type="data_asset",
        object_id=asset.id,
        new_value=payload.model_dump(),
    )
    await db.commit()
    await db.refresh(asset)
    return asset


@router.post("/{asset_id}/link-ropa", status_code=201)
async def link_asset_to_ropa(
    asset_id: str,
    payload: AssetLinkCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ASSET_EDIT")),
    db: AsyncSession = Depends(get_db),
):
    link = AssetProcessingActivityLink(
        asset_id=asset_id, processing_activity_id=payload.processing_activity_id
    )
    db.add(link)
    await db.flush()
    await write_audit_log(
        db,
        user_id=user.id,
        tenant_id=tenant_id,
        action="LINK",
        object_type="asset_processing_activity",
        object_id=link.id,
        new_value={"asset_id": asset_id, "processing_activity_id": payload.processing_activity_id},
    )
    await db.commit()
    return {"status": "linked", "asset_id": asset_id, "processing_activity_id": payload.processing_activity_id}
