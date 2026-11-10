from decimal import Decimal
from uuid import UUID

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
from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.models.user import User


router = APIRouter(
    prefix="/sales",
    tags=["sales"],
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

    # Aynı ürünün satış isteğinde birden fazla kez
    # gönderilmesini engelliyoruz.
    product_ids = [item.product_id for item in body.items]

    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=400,
            detail="DUPLICATE_PRODUCT",
        )

    # Ürünleri UUID olarak normalize ediyoruz.
    requested_items = {
        UUID(str(item.product_id)): item.quantity
        for item in body.items
    }

    requested_product_ids = list(requested_items.keys())

    # Satış sırasında stokların başka bir işlem tarafından
    # eş zamanlı değiştirilmesini önlemek için satırları kilitliyoruz.
    products = (
        db.query(Product)
        .filter(
            Product.id.in_(requested_product_ids),
            Product.business_id == business.id,
            Product.is_active.is_(True),
        )
        .order_by(Product.id)
        .with_for_update()
        .all()
    )

    # İstenen ürünlerden biri bulunamadıysa satışın
    # hiçbir kısmını gerçekleştirmiyoruz.
    if len(products) != len(requested_product_ids):
        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="PRODUCT_NOT_FOUND",
        )

    products_by_id = {
        product.id: product
        for product in products
    }

    # Önce bütün stokları kontrol ediyoruz.
    # Böylece bir ürün yetersizse diğer ürünlerin stokları da değişmez.
    for product_id, quantity in requested_items.items():
        product = products_by_id[product_id]

        if product.stock_quantity < quantity:
            db.rollback()

            raise HTTPException(
                status_code=400,
                detail="INSUFFICIENT_STOCK",
            )

    total_amount = Decimal("0.00")
    total_cost = Decimal("0.00")
    total_gross_profit = Decimal("0.00")

    # Önce toplamları server-side hesaplıyoruz.
    for product_id, quantity in requested_items.items():
        product = products_by_id[product_id]

        unit_sale_price = Decimal(product.sale_price)
        unit_purchase_price = Decimal(product.purchase_price)

        subtotal = unit_sale_price * quantity
        cost = unit_purchase_price * quantity
        gross_profit = subtotal - cost

        total_amount += subtotal
        total_cost += cost
        total_gross_profit += gross_profit

    sale = Sale(
        business_id=business.id,
        total_amount=total_amount,
        total_cost=total_cost,
        gross_profit=total_gross_profit,
    )

    db.add(sale)

    try:
        # Sale ID'sinin oluşması için flush ediyoruz.
        # Henüz transaction commit edilmez.
        db.flush()

        response_items: list[SaleItemResponse] = []

        for item in body.items:
            product_id = UUID(str(item.product_id))
            quantity = item.quantity
            product = products_by_id[product_id]

            unit_sale_price = Decimal(product.sale_price)
            unit_purchase_price = Decimal(product.purchase_price)

            subtotal = unit_sale_price * quantity
            cost = unit_purchase_price * quantity
            gross_profit = subtotal - cost

            stock_before = product.stock_quantity
            stock_after = stock_before - quantity

            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=quantity,
                unit_sale_price=unit_sale_price,
                unit_purchase_price=unit_purchase_price,
                subtotal=subtotal,
                cost=cost,
                gross_profit=gross_profit,
            )

            db.add(sale_item)

            product.stock_quantity = stock_after

            stock_movement = StockMovement(
                business_id=business.id,
                product_id=product.id,
                movement_type="SALE",
                quantity=quantity,
                stock_before=stock_before,
                stock_after=stock_after,
                note=f"Sale {sale.id}",
            )

            db.add(stock_movement)

            # SaleItem ID'sinin response için oluşmasını sağlıyoruz.
            db.flush()

            response_items.append(
                SaleItemResponse(
                    id=sale_item.id,
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    quantity=quantity,
                    unit_sale_price=str(unit_sale_price),
                    unit_purchase_price=str(unit_purchase_price),
                    subtotal=str(subtotal),
                    cost=str(cost),
                    gross_profit=str(gross_profit),
                )
            )

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="DATABASE_ERROR",
        )

    db.refresh(sale)

    return SaleResponse(
        id=sale.id,
        business_id=sale.business_id,
        total_amount=str(sale.total_amount),
        total_cost=str(sale.total_cost),
        gross_profit=str(sale.gross_profit),
        created_at=sale.created_at.isoformat(),
        items=response_items,
    )