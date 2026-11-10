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