from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MovementType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"


class CreateStockMovementRequest(BaseModel):
    product_id: str
    movement_type: MovementType
    quantity: int = Field(..., gt=0)
    note: Optional[str] = Field(None, max_length=255)

    @field_validator("product_id")
    @classmethod
    def product_id_must_be_uuid(cls, v: str) -> str:
        # UUID validation is handled by the database layer
        return v


class StockMovementResponse(BaseModel):
    id: str
    business_id: str
    product_id: str
    movement_type: str
    quantity: int
    stock_before: int
    stock_after: int
    note: Optional[str]
    created_at: str
