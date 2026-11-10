from uuid import UUID

from pydantic import BaseModel, Field

from stockwise.app.api.stock_movements.schemas import MAX_QUANTITY


class CreateSaleItemRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(..., gt=0, le=MAX_QUANTITY)


class CreateSaleRequest(BaseModel):
    items: list[CreateSaleItemRequest] = Field(
        ...,
        min_length=1,
    )


class CreateReturnLineRequest(BaseModel):
    sale_item_id: UUID
    quantity: int = Field(..., gt=0, le=MAX_QUANTITY)


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


class SaleHistoryLineResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    quantity: int
    returned_quantity: int
    unit_sale_price: str
    subtotal: str


class SaleHistoryEntryResponse(BaseModel):
    id: UUID
    created_at: str
    total_amount: str
    total_cost: str
    gross_profit: str
    # Sum of refunds issued against this sale so far.
    refund_amount: str
    items: list[SaleHistoryLineResponse]


class SaleListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[SaleHistoryEntryResponse]


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