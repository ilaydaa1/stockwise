from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from stockwise.app.api.products.schemas import validate_price_value


class ManualMovementType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"


class MovementType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"
    SALE = "SALE"
    OPENING = "OPENING"
    RETURN = "RETURN"


class CreateStockMovementRequest(BaseModel):
    product_id: UUID
    movement_type: ManualMovementType
    quantity: int = Field(..., gt=0)
    # Price paid per unit. Only meaningful for IN; when omitted the
    # current purchase price of the product is used.
    unit_cost: Optional[Decimal] = None
    note: Optional[str] = Field(
        default=None,
        max_length=255,
    )

    @field_validator("unit_cost")
    @classmethod
    def validate_unit_cost(
        cls,
        value: Optional[Decimal],
    ) -> Optional[Decimal]:
        if value is None:
            return value

        return validate_price_value(value)

    @model_validator(mode="after")
    def unit_cost_only_for_stock_in(self):
        if (
            self.unit_cost is not None
            and self.movement_type != ManualMovementType.IN
        ):
            raise ValueError(
                "unit_cost yalnızca stok girişi (IN) için gönderilebilir"
            )

        return self


class StockMovementResponse(BaseModel):
    id: UUID
    business_id: UUID
    product_id: UUID
    movement_type: MovementType
    quantity: int
    stock_before: int
    stock_after: int
    unit_cost: Optional[str] = None
    sale_id: Optional[UUID] = None
    sale_return_id: Optional[UUID] = None
    note: Optional[str] = None
    created_at: str