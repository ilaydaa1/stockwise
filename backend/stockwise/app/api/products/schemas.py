from decimal import Decimal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    model_validator,
)


def validate_price_value(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError(
            "Fiyat geçerli bir sayı olmalıdır"
        )

    if value < 0:
        raise ValueError(
            "Fiyat negatif olamaz"
        )

    exponent = value.as_tuple().exponent

    decimal_places = (
        max(-exponent, 0)
        if isinstance(exponent, int)
        else 0
    )

    if decimal_places > 2:
        raise ValueError(
            "Fiyat en fazla 2 ondalık basamak içerebilir"
        )

    normalized = value.copy_abs()

    if normalized == 0:
        integer_digits = 1
    else:
        adjusted = normalized.adjusted()
        integer_digits = max(adjusted + 1, 1)

    if integer_digits + decimal_places > 12:
        raise ValueError(
            "Fiyat toplamda en fazla 12 basamak içerebilir"
        )

    return value


NULLABLE_UPDATE_FIELDS = {"category_id", "supplier_id"}


class CreateProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    sku: str
    purchase_price: Decimal
    sale_price: Decimal
    stock_quantity: int = 0
    minimum_stock: int = 0
    category_id: UUID | None = None
    supplier_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "Ürün adı en az 2 karakter olmalıdır"
            )

        if len(value) > 150:
            raise ValueError(
                "Ürün adı en fazla 150 karakter olabilir"
            )

        return value

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, value: str) -> str:
        value = value.strip().upper()

        if not value:
            raise ValueError(
                "SKU boş olamaz"
            )

        if len(value) > 50:
            raise ValueError(
                "SKU en fazla 50 karakter olabilir"
            )

        return value

    @field_validator(
        "purchase_price",
        "sale_price",
    )
    @classmethod
    def validate_price(
        cls,
        value: Decimal,
    ) -> Decimal:
        return validate_price_value(value)

    @field_validator(
        "stock_quantity",
        "minimum_stock",
    )
    @classmethod
    def validate_stock(
        cls,
        value: int,
    ) -> int:
        if value < 0:
            raise ValueError(
                "Stok değeri negatif olamaz"
            )

        return value


class UpdateProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    sku: str | None = None
    purchase_price: Decimal | None = None
    sale_price: Decimal | None = None
    minimum_stock: int | None = None
    # Unlike the fields above, these may be set to null explicitly
    # to remove the category or supplier from a product.
    category_id: UUID | None = None
    supplier_id: UUID | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        for field_name in self.model_fields_set:
            if field_name in NULLABLE_UPDATE_FIELDS:
                continue

            if getattr(self, field_name) is None:
                raise ValueError(
                    f"{field_name} null olamaz"
                )

        return self

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "Ürün adı en az 2 karakter olmalıdır"
            )

        if len(value) > 150:
            raise ValueError(
                "Ürün adı en fazla 150 karakter olabilir"
            )

        return value

    @field_validator("sku")
    @classmethod
    def validate_sku(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return value

        value = value.strip().upper()

        if not value:
            raise ValueError(
                "SKU boş olamaz"
            )

        if len(value) > 50:
            raise ValueError(
                "SKU en fazla 50 karakter olabilir"
            )

        return value

    @field_validator(
        "purchase_price",
        "sale_price",
    )
    @classmethod
    def validate_price(
        cls,
        value: Decimal | None,
    ) -> Decimal | None:
        if value is None:
            return value

        return validate_price_value(value)

    @field_validator("minimum_stock")
    @classmethod
    def validate_minimum_stock(
        cls,
        value: int | None,
    ) -> int | None:
        if value is None:
            return value

        if value < 0:
            raise ValueError(
                "Minimum stok negatif olamaz"
            )

        return value


class ProductResponse(BaseModel):
    id: str
    business_id: str
    category_id: str | None = None
    supplier_id: str | None = None
    name: str
    sku: str
    purchase_price: Decimal
    sale_price: Decimal
    stock_quantity: int
    minimum_stock: int
    is_active: bool
    created_at: str
    updated_at: str