from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MovementType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"


class CreateStockMovementRequest(BaseModel):
    product_id: UUID
    movement_type: MovementType
    quantity: int = Field(..., gt=0)
    note: Optional[str] = Field(
        default=None,
        max_length=255,
    )


class StockMovementResponse(BaseModel):
    id: UUID
    business_id: UUID
    product_id: UUID
    movement_type: MovementType
    quantity: int
    stock_before: int
    stock_after: int
    note: Optional[str] = None
    created_at: str