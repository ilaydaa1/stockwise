from uuid import UUID

from pydantic import BaseModel, Field


class CreateSaleItemRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(..., gt=0)


class CreateSaleRequest(BaseModel):
    items: list[CreateSaleItemRequest] = Field(
        ...,
        min_length=1,
    )


class CreateReturnLineRequest(BaseModel):
    sale_item_id: UUID
    quantity: int = Field(..., gt=0)


class CreateReturnRequest(BaseModel):
    items: list[CreateReturnLineRequest] = Field(
        ...,
        min_length=1,
    )
    reason: str | None = Field(
        default=None,
        max_length=255,
    )


class SaleReturnResponse(BaseModel):
    id: UUID
    sale_id: UUID
    sale_item_id: UUID
    product_id: UUID
    quantity: int
    refund_amount: str
    cost_amount: str
    reason: str | None
    created_at: str


class SaleItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    quantity: int
    unit_sale_price: str
    unit_purchase_price: str
    subtotal: str
    cost: str
    gross_profit: str


class SaleResponse(BaseModel):
    id: UUID
    business_id: UUID
    total_amount: str
    total_cost: str
    gross_profit: str
    created_at: str
    items: list[SaleItemResponse]