from decimal import Decimal

from pydantic import BaseModel, field_validator


class CreateProductRequest(BaseModel):
    name: str
    sku: str
    purchase_price: Decimal
    sale_price: Decimal
    stock_quantity: int = 0
    minimum_stock: int = 0

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        v = v.strip()

        if len(v) < 2:
            raise ValueError("Ürün adı en az 2 karakter olmalıdır")

        if len(v) > 150:
            raise ValueError("Ürün adı en fazla 150 karakter olmalıdır")

        return v

    @field_validator("sku")
    @classmethod
    def sku_must_be_valid(cls, v: str) -> str:
        v = v.strip().upper()

        if len(v) < 1:
            raise ValueError("SKU boş olamaz")

        if len(v) > 50:
            raise ValueError("SKU en fazla 50 karakter olmalıdır")

        return v

    @field_validator("purchase_price", "sale_price")
    @classmethod
    def prices_must_be_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Fiyat negatif olamaz")

        return v

    @field_validator("stock_quantity", "minimum_stock")
    @classmethod
    def stock_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Stok miktarı negatif olamaz")

        return v


class UpdateProductRequest(BaseModel):
    name: str | None = None
    sku: str | None = None
    purchase_price: Decimal | None = None
    sale_price: Decimal | None = None
    minimum_stock: int | None = None

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v

        v = v.strip()

        if len(v) < 2:
            raise ValueError("Ürün adı en az 2 karakter olmalıdır")

        if len(v) > 150:
            raise ValueError("Ürün adı en fazla 150 karakter olmalıdır")

        return v

    @field_validator("sku")
    @classmethod
    def sku_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v

        v = v.strip().upper()

        if len(v) < 1:
            raise ValueError("SKU boş olamaz")

        if len(v) > 50:
            raise ValueError("SKU en fazla 50 karakter olmalıdır")

        return v

    @field_validator("purchase_price", "sale_price")
    @classmethod
    def prices_must_be_non_negative(
        cls,
        v: Decimal | None,
    ) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("Fiyat negatif olamaz")

        return v

    @field_validator("minimum_stock")
    @classmethod
    def minimum_stock_must_be_non_negative(
        cls,
        v: int | None,
    ) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Minimum stok negatif olamaz")

        return v


class ProductResponse(BaseModel):
    id: str
    business_id: str
    name: str
    sku: str
    purchase_price: Decimal
    sale_price: Decimal
    stock_quantity: int
    minimum_stock: int
    is_active: bool
    created_at: str
    updated_at: str