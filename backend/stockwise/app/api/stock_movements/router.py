from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from stockwise.app.api.stock_movements.schemas import (
    CreateStockMovementRequest,
    MovementType,
    StockMovementResponse,
)
from stockwise.app.core.deps import (
    get_current_user,
    require_csrf,
    require_trusted_origin,
)
from stockwise.app.db.session import get_db
from stockwise.app.models.business import Business
from stockwise.app.models.product import Product
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.models.user import User


router = APIRouter(
    prefix="/stock-movements",
    tags=["stock-movements"],
)


@router.post(
    "",
    response_model=StockMovementResponse,
    status_code=201,
)
def create_stock_movement(
    body: CreateStockMovementRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _origin: None = Depends(require_trusted_origin),
    _csrf: None = Depends(require_csrf),
) -> StockMovementResponse:
    business = (
        db.query(Business)
        .filter(Business.owner_id == user.id)
        .first()
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="BUSINESS_NOT_FOUND",
        )

    product = (
        db.query(Product)
        .filter(
            Product.id == body.product_id,
            Product.business_id == business.id,
            Product.is_active.is_(True),
        )
        .with_for_update()
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="PRODUCT_NOT_FOUND",
        )

    if body.movement_type in (MovementType.IN, MovementType.ADJUSTMENT_IN):
        stock_after = product.stock_quantity + body.quantity
    else:  # OUT, ADJUSTMENT_OUT
        if product.stock_quantity < body.quantity:
            raise HTTPException(
                status_code=400,
                detail="INSUFFICIENT_STOCK",
            )
        stock_after = product.stock_quantity - body.quantity

    stock_before = product.stock_quantity
    product.stock_quantity = stock_after

    movement = StockMovement(
        business_id=business.id,
        product_id=product.id,
        movement_type=body.movement_type.value,
        quantity=body.quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        note=body.note,
    )

    db.add(movement)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="DATABASE_ERROR",
        )

    db.refresh(movement)

    return StockMovementResponse(
        id=str(movement.id),
        business_id=str(movement.business_id),
        product_id=str(movement.product_id),
        movement_type=movement.movement_type,
        quantity=movement.quantity,
        stock_before=movement.stock_before,
        stock_after=movement.stock_after,
        note=movement.note,
        created_at=movement.created_at.isoformat(),
    )


@router.get(
    "",
    response_model=list[StockMovementResponse],
)
def list_stock_movements(
    product_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StockMovementResponse]:
    business = (
        db.query(Business)
        .filter(Business.owner_id == user.id)
        .first()
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="BUSINESS_NOT_FOUND",
        )

    query = db.query(StockMovement).filter(
        StockMovement.business_id == business.id,
    )

    if product_id:
        query = query.filter(StockMovement.product_id == product_id)

    movements = query.order_by(StockMovement.created_at.desc()).all()

    return [
        StockMovementResponse(
            id=str(m.id),
            business_id=str(m.business_id),
            product_id=str(m.product_id),
            movement_type=m.movement_type,
            quantity=m.quantity,
            stock_before=m.stock_before,
            stock_after=m.stock_after,
            note=m.note,
            created_at=m.created_at.isoformat(),
        )
        for m in movements
    ]
