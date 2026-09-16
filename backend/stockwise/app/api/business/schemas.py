from pydantic import BaseModel, field_validator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


VALID_CURRENCIES = {"TRY", "USD", "EUR"}


class CreateBusinessRequest(BaseModel):
    name: str
    currency: str = "TRY"
    timezone: str = "Europe/Istanbul"

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("İşletme adı en az 2 karakter olmalıdır")
        if len(v) > 100:
            raise ValueError("İşletme adı en fazla 100 karakter olmalıdır")
        return v

    @field_validator("currency")
    @classmethod
    def currency_must_be_valid(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in VALID_CURRENCIES:
            raise ValueError(f"Geçersiz para birimi: {v}. Geçerli değerler: TRY, USD, EUR")
        return v

    @field_validator("timezone")
    @classmethod
    def timezone_must_be_valid(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (KeyError, ZoneInfoNotFoundError):
            raise ValueError(f"Geçersiz saat dilimi: {v}")
        return v


class BusinessResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    currency: str
    timezone: str
    created_at: str
    updated_at: str
