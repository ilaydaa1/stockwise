from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from stockwise.app.api.stock_movements.schemas import (
    CreateStockMovementRequest,
    StockMovementResponse,
)
from stockwise.app.core.deps import (
    get_current_user,
    require_csrf,
    require_trusted_origin,
)
from stockwise.app.db.session import get_db
from stockwise.app.models.business import Business
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.models.user import User
from stockwise.app.services.inventory import (
    InsufficientStockError,
    apply_stock_change,
    lock_products,
)


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

    product = lock_products(
        db,
        business_id=business.id,
        product_ids=[body.product_id],
    ).get(body.product_id)

    if not product:
        raise HTTPException(
            status_code=404,
            detail="PRODUCT_NOT_FOUND",
        )

    try:
        movement = apply_stock_change(
            db,
            product=product,
            movement_type=body.movement_type.value,
            quantity=body.quantity,
            note=body.note,
        )

        db.commit()

    except InsufficientStockError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="INSUFFICIENT_STOCK",
        )

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
        try:
            product_uuid = UUID(product_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422,
                detail="INVALID_PRODUCT_ID",
            )

        query = query.filter(
            StockMovement.product_id == product_uuid
        )

    movements = (
        query
        .order_by(StockMovement.created_at.desc())
        .all()
    )

    return [
        StockMovementResponse(
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
        for movement in movements
    ]