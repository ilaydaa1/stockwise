from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_LEAD_TIME_DAYS = 365


def _validate_supplier_name(value: str) -> str:
    value = value.strip()

    if len(value) < 2:
        raise ValueError("Tedarikçi adı en az 2 karakter olmalıdır")

    if len(value) > 100:
        raise ValueError("Tedarikçi adı en fazla 100 karakter olabilir")

    return value


class CreateSupplierRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    lead_time_days: int = Field(..., ge=0, le=MAX_LEAD_TIME_DAYS)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_supplier_name(value)


class UpdateSupplierRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    lead_time_days: int | None = Field(
        default=None,
        ge=0,
        le=MAX_LEAD_TIME_DAYS,
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value

        return _validate_supplier_name(value)


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    name: str
    lead_time_days: int
    created_at: datetime
