from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from stockwise.app.api.sales.schemas import (
    CreateReturnRequest,
    CreateSaleRequest,
    SaleHistoryEntryResponse,
    SaleHistoryLineResponse,
    SaleItemResponse,
    SaleListResponse,
    SaleResponse,
    SaleReturnResponse,
)
from stockwise.app.core.deps import (
    get_current_business,
    get_current_user,
    require_csrf,
    require_trusted_origin,
)
from stockwise.app.db.session import get_db
from stockwise.app.models.business import Business
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.models.user import User
from stockwise.app.services.inventory import InsufficientStockError
from stockwise.app.services.returns import (
    DuplicateReturnLineError,
    ReturnExceedsSoldError,
    SaleItemNotFoundError,
    SaleNotFoundError,
    create_return,
)
from stockwise.app.services.sales import (
    DuplicateProductError,
    ProductNotFoundError,
    SaleTotalTooLargeError,
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


@router.get(
    "",
    response_model=SaleListResponse,
)
def list_sales(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> SaleListResponse:
    """Sales of the business, newest first, one page at a time.

    Each line reports how many units have already been returned, so
    a client knows how many can still be returned.
    """
    total = (
        db.query(func.count(Sale.id))
        .filter(Sale.business_id == business.id)
        .scalar()
        or 0
    )

    sales = (
        db.query(Sale)
        .options(joinedload(Sale.items).joinedload(SaleItem.product))
        .filter(Sale.business_id == business.id)
        .order_by(Sale.created_at.desc(), Sale.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    sale_item_ids = [item.id for sale in sales for item in sale.items]

    # One grouped query for the whole page instead of one per line.
    returned: dict = {}

    if sale_item_ids:
        returned = {
            sale_item_id: (int(quantity), refund)
            for sale_item_id, quantity, refund in (
                db.query(
                    SaleReturn.sale_item_id,
                    func.sum(SaleReturn.quantity),
                    func.sum(SaleReturn.refund_amount),
                )
                .filter(SaleReturn.sale_item_id.in_(sale_item_ids))
                .group_by(SaleReturn.sale_item_id)
                .all()
            )
        }

    entries = []

    for sale in sales:
        lines = sorted(sale.items, key=lambda item: item.product.name)

        entries.append(
            SaleHistoryEntryResponse(
                id=sale.id,
                created_at=sale.created_at.isoformat(),
                total_amount=str(sale.total_amount),
                total_cost=str(sale.total_cost),
                gross_profit=str(sale.gross_profit),
                refund_amount=str(
                    sum(
                        (
                            Decimal(returned[item.id][1])
                            for item in lines
                            if item.id in returned
                        ),
                        Decimal("0.00"),
                    ).quantize(Decimal("0.01"))
                ),
                items=[
                    SaleHistoryLineResponse(
                        id=item.id,
                        product_id=item.product_id,
                        product_name=item.product.name,
                        product_sku=item.product.sku,
                        quantity=item.quantity,
                        returned_quantity=(
                            returned[item.id][0]
                            if item.id in returned
                            else 0
                        ),
                        unit_sale_price=str(item.unit_sale_price),
                        subtotal=str(item.subtotal),
                    )
                    for item in lines
                ],
            )
        )

    return SaleListResponse(
        total=int(total),
        limit=limit,
        offset=offset,
        items=entries,
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

    except SaleTotalTooLargeError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="SALE_TOTAL_TOO_LARGE",
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="DATABASE_ERROR",
        )

    db.refresh(sale)

    return _sale_to_response(sale, product_order)


def _return_to_response(
    sale_return: SaleReturn,
    sale_id: UUID,
) -> SaleReturnResponse:
    return SaleReturnResponse(
        id=sale_return.id,
        sale_id=sale_id,
        sale_item_id=sale_return.sale_item_id,
        product_id=sale_return.sale_item.product_id,
        quantity=sale_return.quantity,
        refund_amount=str(sale_return.refund_amount),
        cost_amount=str(sale_return.cost_amount),
        reason=sale_return.reason,
        created_at=sale_return.created_at.isoformat(),
    )


@router.post(
    "/{sale_id}/returns",
    response_model=list[SaleReturnResponse],
    status_code=201,
)
def create_sale_return(
    sale_id: UUID,
    body: CreateReturnRequest,
    _origin: None = Depends(require_trusted_origin),
    _csrf: None = Depends(require_csrf),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> list[SaleReturnResponse]:
    try:
        sale_returns = create_return(
            db,
            business_id=business.id,
            sale_id=sale_id,
            lines=[
                (item.sale_item_id, item.quantity)
                for item in body.items
            ],
            reason=body.reason,
        )

        db.commit()

    except SaleNotFoundError:
        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="SALE_NOT_FOUND",
        )

    except SaleItemNotFoundError:
        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="SALE_ITEM_NOT_FOUND",
        )

    except DuplicateReturnLineError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="DUPLICATE_SALE_ITEM",
        )

    except ReturnExceedsSoldError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="RETURN_EXCEEDS_SOLD",
        )

    return [
        _return_to_response(sale_return, sale_id)
        for sale_return in sale_returns
    ]


@router.get(
    "/{sale_id}/returns",
    response_model=list[SaleReturnResponse],
)
def list_sale_returns(
    sale_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> list[SaleReturnResponse]:
    sale = (
        db.query(Sale.id)
        .filter(
            Sale.id == sale_id,
            Sale.business_id == business.id,
        )
        .first()
    )

    if not sale:
        raise HTTPException(
            status_code=404,
            detail="SALE_NOT_FOUND",
        )

    sale_returns = (
        db.query(SaleReturn)
        .join(SaleItem, SaleItem.id == SaleReturn.sale_item_id)
        .filter(SaleItem.sale_id == sale_id)
        .order_by(SaleReturn.created_at.asc(), SaleReturn.id.asc())
        .all()
    )

    return [
        _return_to_response(sale_return, sale_id)
        for sale_return in sale_returns
    ]
