from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from stockwise.app.api.suppliers.schemas import (
    CreateSupplierRequest,
    SupplierResponse,
    UpdateSupplierRequest,
)
from stockwise.app.core.deps import (
    get_current_business,
    require_csrf,
    require_trusted_origin,
)
from stockwise.app.db.session import get_db
from stockwise.app.models.business import Business
from stockwise.app.models.supplier import Supplier


router = APIRouter(
    prefix="/suppliers",
    tags=["suppliers"],
)


@router.get("", response_model=list[SupplierResponse])
def list_suppliers(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> list[Supplier]:
    return (
        db.query(Supplier)
        .filter(Supplier.business_id == business.id)
        .order_by(Supplier.name.asc())
        .all()
    )


@router.post("", response_model=SupplierResponse, status_code=201)
def create_supplier(
    body: CreateSupplierRequest,
    _origin: None = Depends(require_trusted_origin),
    _csrf: None = Depends(require_csrf),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> Supplier:
    supplier = Supplier(
        business_id=business.id,
        name=body.name,
        lead_time_days=body.lead_time_days,
    )

    db.add(supplier)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="SUPPLIER_ALREADY_EXISTS",
        )

    db.refresh(supplier)

    return supplier


@router.patch("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: UUID,
    body: UpdateSupplierRequest,
    _origin: None = Depends(require_trusted_origin),
    _csrf: None = Depends(require_csrf),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> Supplier:
    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.id == supplier_id,
            Supplier.business_id == business.id,
        )
        .first()
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="SUPPLIER_NOT_FOUND",
        )

    changes = body.model_dump(exclude_unset=True, exclude_none=True)

    for field, value in changes.items():
        setattr(supplier, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="SUPPLIER_ALREADY_EXISTS",
        )

    db.refresh(supplier)

    return supplier
