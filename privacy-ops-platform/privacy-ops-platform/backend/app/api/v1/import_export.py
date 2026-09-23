import csv
import io
import uuid

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.rbac import require_permission
from app.core.tenancy import get_current_tenant_id
from app.models.user import User
from app.schemas.ropa import ProcessingActivityCreate
from app.services import ropa_service

router = APIRouter(prefix="/ropa/import-export", tags=["Import/Export"])

REQUIRED_COLUMNS = {"name"}
IMPORTABLE_COLUMNS = {
    "name",
    "description",
    "business_function",
    "purpose",
    "secondary_purpose",
    "controller_type",
    "data_subject_categories",
    "personal_data_categories",
    "legal_basis",
}


class ImportPreviewRow(BaseModel):
    row_number: int
    data: dict
    errors: list[str]


class ImportPreviewResult(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    preview: list[ImportPreviewRow]


class ImportConfirmResult(BaseModel):
    imported_count: int
    skipped_count: int
    import_batch_id: str


def _validate_row(row: dict, row_number: int) -> ImportPreviewRow:
    errors = []
    for col in REQUIRED_COLUMNS:
        if not row.get(col, "").strip():
            errors.append(f"Missing required field: {col}")
    unknown_cols = set(row.keys()) - IMPORTABLE_COLUMNS
    if unknown_cols:
        errors.append(f"Unrecognized columns (ignored on import): {', '.join(sorted(unknown_cols))}")
    return ImportPreviewRow(row_number=row_number, data=row, errors=errors)


@router.post("/preview", response_model=ImportPreviewResult)
async def preview_import(
    file: UploadFile,
    user: User = Depends(require_permission("ROPA_CREATE")),
):
    """
    Step 1 of import: parse + validate only. Nothing is written to the
    database here — matches the "validate, show errors, preview, never
    silently overwrite" requirement in docs/architecture.md Section 24.
    """
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    rows = [_validate_row(row, i + 1) for i, row in enumerate(reader)]
    valid = [r for r in rows if not r.errors]
    invalid = [r for r in rows if r.errors]
    return ImportPreviewResult(
        total_rows=len(rows), valid_rows=len(valid), invalid_rows=len(invalid), preview=rows[:50]
    )


@router.post("/confirm", response_model=ImportConfirmResult)
async def confirm_import(
    file: UploadFile,
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ROPA_CREATE")),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: re-validates (never trusts a client-held "it was valid before")
    and only then creates records — one row = one new ROPA in DRAFT status,
    each getting its own version 1 + audit CREATE entry via the normal
    service function, so imported records are indistinguishable from
    manually created ones in the audit trail except for the import_batch_id
    reason note.
    """
    batch_id = str(uuid.uuid4())
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    imported = 0
    skipped = 0
    for row in reader:
        if not row.get("name", "").strip():
            skipped += 1
            continue
        clean_row = {k: v for k, v in row.items() if k in IMPORTABLE_COLUMNS and v}
        activity = await ropa_service.create_processing_activity(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            data=ProcessingActivityCreate(**clean_row),
        )
        await write_audit_log(
            db,
            user_id=user.id,
            tenant_id=tenant_id,
            action="IMPORT",
            object_type="processing_activity",
            object_id=activity.id,
            reason=f"CSV import batch {batch_id}",
        )
        imported += 1

    await db.commit()
    return ImportConfirmResult(imported_count=imported, skipped_count=skipped, import_batch_id=batch_id)


@router.get("/export.csv")
async def export_csv(
    tenant_id: str = Depends(get_current_tenant_id),
    user: User = Depends(require_permission("ROPA_EXPORT")),
    db: AsyncSession = Depends(get_db),
):
    activities = await ropa_service.list_processing_activities(db, tenant_id=tenant_id)

    output = io.StringIO()
    fieldnames = ["id", "name", "status", "version", "purpose", "legal_basis", "business_function"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for a in activities:
        writer.writerow(
            {
                "id": a.id,
                "name": a.name,
                "status": a.status,
                "version": a.version,
                "purpose": a.purpose or "",
                "legal_basis": a.legal_basis or "",
                "business_function": a.business_function or "",
            }
        )

    await write_audit_log(
        db,
        user_id=user.id,
        tenant_id=tenant_id,
        action="EXPORT",
        object_type="processing_activity",
        object_id="bulk",
        reason=f"CSV export of {len(activities)} records",
    )
    await db.commit()

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ropa_export.csv"},
    )
