from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_
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
from stockwise.app.models.product import Product
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.models.user import User
from stockwise.app.services.inventory import (
    InsufficientStockError,
    StockLimitExceededError,
    apply_stock_change,
    lock_products,
)


DEFAULT_PAGE_SIZE = 200
MAX_PAGE_SIZE = 500


router = APIRouter(
    prefix="/stock-movements",
    tags=["stock-movements"],
)


def _movement_to_response(
    movement: StockMovement,
) -> StockMovementResponse:
    return StockMovementResponse(
        id=str(movement.id),
        business_id=str(movement.business_id),
        product_id=str(movement.product_id),
        movement_type=movement.movement_type,
        quantity=movement.quantity,
        stock_before=movement.stock_before,
        stock_after=movement.stock_after,
        unit_cost=(
            str(movement.unit_cost)
            if movement.unit_cost is not None
            else None
        ),
        sale_id=movement.sale_id,
        sale_return_id=movement.sale_return_id,
        note=movement.note,
        created_at=movement.created_at.isoformat(),
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
            unit_cost=body.unit_cost,
            note=body.note,
        )

        db.commit()

    except InsufficientStockError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="INSUFFICIENT_STOCK",
        )

    except StockLimitExceededError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="STOCK_LIMIT_EXCEEDED",
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="DATABASE_ERROR",
        )

    db.refresh(movement)

    return _movement_to_response(movement)


@router.get(
    "",
    response_model=list[StockMovementResponse],
)
def list_stock_movements(
    response: Response,
    product_id: Optional[str] = None,
    q: Optional[str] = Query(default=None, max_length=100),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StockMovementResponse]:
    """Stock movements, newest first, one page at a time.

    The total number of matching movements is returned in the
    X-Total-Count header, so the body stays a plain list.
    """
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

    search = (q or "").strip()

    if search:
        # Escape the wildcard characters so they match literally.
        pattern = (
            "%"
            + search.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
            + "%"
        )

        query = query.join(
            Product,
            Product.id == StockMovement.product_id,
        ).filter(
            or_(
                Product.name.ilike(pattern, escape="\\"),
                Product.sku.ilike(pattern, escape="\\"),
                StockMovement.note.ilike(pattern, escape="\\"),
            )
        )

    total = query.with_entities(func.count(StockMovement.id)).scalar() or 0

    movements = (
        query
        .order_by(
            StockMovement.created_at.desc(),
            StockMovement.id.desc(),
        )
        .limit(limit)
        .offset(offset)
        .all()
    )

    response.headers["X-Total-Count"] = str(total)

    return [
        _movement_to_response(movement)
        for movement in movements
    ]
