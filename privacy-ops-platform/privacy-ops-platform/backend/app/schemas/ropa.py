from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ProcessingActivityBase(BaseModel):
    name: str
    description: str | None = None
    business_function: str | None = None
    department_id: str | None = None
    business_owner_id: str | None = None
    processing_owner_id: str | None = None
    privacy_owner_id: str | None = None
    purpose: str | None = None
    secondary_purpose: str | None = None
    controller_type: str | None = None
    data_subject_categories: str | None = None
    personal_data_categories: str | None = None
    legal_basis: str | None = None
    review_frequency_months: int | None = None


class ProcessingActivityCreate(ProcessingActivityBase):
    pass


class ProcessingActivityUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    business_function: str | None = None
    department_id: str | None = None
    business_owner_id: str | None = None
    processing_owner_id: str | None = None
    privacy_owner_id: str | None = None
    purpose: str | None = None
    secondary_purpose: str | None = None
    controller_type: str | None = None
    data_subject_categories: str | None = None
    personal_data_categories: str | None = None
    legal_basis: str | None = None
    review_frequency_months: int | None = None


class ProcessingActivityStatusChange(BaseModel):
    new_status: str
    reason: str | None = None


class ProcessingActivityOut(ProcessingActivityBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    status: str
    version: int
    last_reviewed_date: date | None = None
    next_review_date: date | None = None
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None


class RecordVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    object_type: str
    object_id: str
    version_number: int
    snapshot: dict
    created_at: datetime
    created_by: str | None = None
