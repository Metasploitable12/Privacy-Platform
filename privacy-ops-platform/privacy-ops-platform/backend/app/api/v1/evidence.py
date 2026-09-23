import uuid

import boto3
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rbac import require_permission
from app.core.tenancy import get_current_tenant_id
from app.models.evidence import Evidence
from app.models.user import User

router = APIRouter(prefix="/evidence", tags=["Evidence"])
settings = get_settings()


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.object_storage_endpoint,
        aws_access_key_id=settings.object_storage_access_key,
        aws_secret_access_key=settings.object_storage_secret_key,
        region_name=settings.object_storage_region,
    )


class EvidenceUploadRequest(BaseModel):
    file_name: str
    evidence_type: str
    linked_object_type: str
    linked_object_id: str
    classification: str | None = None


class EvidenceUploadResponse(BaseModel):
    evidence_id: str
    upload_url: str
    storage_key: str


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    evidence_type: str
    file_name: str
    linked_object_type: str
    linked_object_id: str
    classification: str | None = None


@router.post("/upload-url", response_model=EvidenceUploadResponse)
async def request_upload_url(
    payload: EvidenceUploadRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("EVIDENCE_UPLOAD")),
    db: AsyncSession = Depends(get_db),
):
    """
    Two-step upload: the backend never proxies file bytes. It creates the
    metadata record and hands back a pre-signed PUT URL; the client uploads
    directly to object storage. Keeps large files off the API process and
    matches the "evidence stored outside the DB" architecture decision.
    """
    storage_key = f"{tenant_id}/{payload.linked_object_type}/{payload.linked_object_id}/{uuid.uuid4()}-{payload.file_name}"

    evidence = Evidence(
        tenant_id=tenant_id,
        created_by=user.id,
        updated_by=user.id,
        evidence_type=payload.evidence_type,
        file_name=payload.file_name,
        storage_key=storage_key,
        classification=payload.classification,
        linked_object_type=payload.linked_object_type,
        linked_object_id=payload.linked_object_id,
    )
    db.add(evidence)
    await db.flush()
    await write_audit_log(
        db,
        user_id=user.id,
        tenant_id=tenant_id,
        action="CREATE",
        object_type="evidence",
        object_id=evidence.id,
        new_value={"file_name": payload.file_name, "linked_object_id": payload.linked_object_id},
    )
    await db.commit()

    upload_url = _s3_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.object_storage_bucket, "Key": storage_key},
        ExpiresIn=600,
    )

    return EvidenceUploadResponse(evidence_id=evidence.id, upload_url=upload_url, storage_key=storage_key)


@router.get("", response_model=list[EvidenceOut])
async def list_evidence(
    linked_object_type: str | None = None,
    linked_object_id: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("EVIDENCE_VIEW")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Evidence).where(Evidence.tenant_id == tenant_id)
    if linked_object_type:
        stmt = stmt.where(Evidence.linked_object_type == linked_object_type)
    if linked_object_id:
        stmt = stmt.where(Evidence.linked_object_id == linked_object_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
