from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from stockwise.app.api.sales.schemas import (
    CreateSaleRequest,
    SaleItemResponse,
    SaleResponse,
)
from stockwise.app.core.deps import (
    get_current_user,
    require_csrf,
    require_trusted_origin,
)
from stockwise.app.db.session import get_db
from stockwise.app.models.business import Business
from stockwise.app.models.sale import Sale
from stockwise.app.models.user import User
from stockwise.app.services.inventory import InsufficientStockError
from stockwise.app.services.sales import (
    DuplicateProductError,
    ProductNotFoundError,
    create_sale as create_sale_record,
)


router = APIRouter(
    prefix="/sales",
    tags=["sales"],
)


def _sale_to_response(
    sale: Sale,
    product_order: list,
) -> SaleResponse:
    items_by_product = {
        item.product_id: item
        for item in sale.items
    }

    # Lines are returned in the order the client sent them.
    items = [
        SaleItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name,
            product_sku=item.product.sku,
            quantity=item.quantity,
            unit_sale_price=str(item.unit_sale_price),
            unit_purchase_price=str(item.unit_purchase_price),
            subtotal=str(item.subtotal),
            cost=str(item.cost),
            gross_profit=str(item.gross_profit),
        )
        for item in (
            items_by_product[product_id]
            for product_id in product_order
        )
    ]

    return SaleResponse(
        id=sale.id,
        business_id=sale.business_id,
        total_amount=str(sale.total_amount),
        total_cost=str(sale.total_cost),
        gross_profit=str(sale.gross_profit),
        created_at=sale.created_at.isoformat(),
        items=items,
    )


@router.post(
    "",
    response_model=SaleResponse,
    status_code=201,
)
def create_sale(
    body: CreateSaleRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _origin: None = Depends(require_trusted_origin),
    _csrf: None = Depends(require_csrf),
) -> SaleResponse:
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

    product_order = [item.product_id for item in body.items]

    try:
        sale = create_sale_record(
            db,
            business_id=business.id,
            items=[
                (item.product_id, item.quantity)
                for item in body.items
            ],
        )

        db.commit()

    except DuplicateProductError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="DUPLICATE_PRODUCT",
        )

    except ProductNotFoundError:
        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="PRODUCT_NOT_FOUND",
        )

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

    db.refresh(sale)

    return _sale_to_response(sale, product_order)
