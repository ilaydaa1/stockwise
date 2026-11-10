from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from stockwise.app.api.products.schemas import (
    CreateProductRequest,
    UpdateProductRequest,
    ProductResponse,
)
from stockwise.app.core.deps import (
    get_current_user,
    require_csrf,
    require_trusted_origin,
)
from stockwise.app.db.session import get_db
from stockwise.app.models.business import Business
from stockwise.app.models.category import Category
from stockwise.app.models.product import Product
from stockwise.app.models.supplier import Supplier
from stockwise.app.models.user import User
from stockwise.app.services.inventory import apply_stock_change


router = APIRouter(
    prefix="/products",
    tags=["products"],
)


def _product_to_response(
    product: Product,
) -> ProductResponse:
    return ProductResponse(
        id=str(product.id),
        business_id=str(product.business_id),
        category_id=(
            str(product.category_id)
            if product.category_id
            else None
        ),
        supplier_id=(
            str(product.supplier_id)
            if product.supplier_id
            else None
        ),
        name=product.name,
        sku=product.sku,
        purchase_price=product.purchase_price,
        sale_price=product.sale_price,
        average_cost=product.average_cost,
        stock_quantity=product.stock_quantity,
        minimum_stock=product.minimum_stock,
        is_active=product.is_active,
        created_at=product.created_at.isoformat(),
        updated_at=product.updated_at.isoformat(),
    )


def _ensure_references_belong_to_business(
    db: Session,
    business_id: UUID,
    category_id: UUID | None,
    supplier_id: UUID | None,
) -> None:
    # The database enforces the same rule with composite foreign
    # keys; checking here gives the client a clear error instead.
    if category_id is not None:
        category = (
            db.query(Category.id)
            .filter(
                Category.id == category_id,
                Category.business_id == business_id,
            )
            .first()
        )

        if not category:
            raise HTTPException(
                status_code=404,
                detail="CATEGORY_NOT_FOUND",
            )

    if supplier_id is not None:
        supplier = (
            db.query(Supplier.id)
            .filter(
                Supplier.id == supplier_id,
                Supplier.business_id == business_id,
            )
            .first()
        )

        if not supplier:
            raise HTTPException(
                status_code=404,
                detail="SUPPLIER_NOT_FOUND",
            )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=201,
)
def create_product(
    body: CreateProductRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _origin: None = Depends(require_trusted_origin),
    _csrf: None = Depends(require_csrf),
) -> ProductResponse:
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

    existing_product = (
        db.query(Product)
        .filter(
            Product.business_id == business.id,
            Product.sku == body.sku,
        )
        .first()
    )

    if existing_product:
        raise HTTPException(
            status_code=409,
            detail="Bu SKU ile kayıtlı bir ürün zaten mevcut",
        )

    _ensure_references_belong_to_business(
        db,
        business.id,
        body.category_id,
        body.supplier_id,
    )

    product = Product(
        business_id=business.id,
        category_id=body.category_id,
        supplier_id=body.supplier_id,
        name=body.name,
        sku=body.sku,
        purchase_price=body.purchase_price,
        sale_price=body.sale_price,
        average_cost=body.purchase_price,
        stock_quantity=0,
        minimum_stock=body.minimum_stock,
    )

    db.add(product)

    try:
        db.flush()

        # Opening stock enters through the ledger like any other
        # change, so movements always add up to the stock level.
        if body.stock_quantity > 0:
            apply_stock_change(
                db,
                product=product,
                movement_type="OPENING",
                quantity=body.stock_quantity,
                unit_cost=body.purchase_price,
                note="Açılış stoku",
            )

        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Bu SKU ile kayıtlı bir ürün zaten mevcut",
        )

    db.refresh(product)

    return _product_to_response(product)


@router.get(
    "",
    response_model=list[ProductResponse],
)
def list_products(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProductResponse]:
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

    products = (
        db.query(Product)
        .filter(
            Product.business_id == business.id,
            Product.is_active.is_(True),
        )
        .order_by(Product.created_at.desc())
        .all()
    )

    return [
        _product_to_response(product)
        for product in products
    ]


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProductResponse:
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
            Product.id == product_id,
            Product.business_id == business.id,
            Product.is_active.is_(True),
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="PRODUCT_NOT_FOUND",
        )

    return _product_to_response(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    product_id: UUID,
    body: UpdateProductRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _origin: None = Depends(require_trusted_origin),
    _csrf: None = Depends(require_csrf),
) -> ProductResponse:
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
            Product.id == product_id,
            Product.business_id == business.id,
            Product.is_active.is_(True),
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="PRODUCT_NOT_FOUND",
        )

    changes = body.model_dump(exclude_unset=True)

    if "sku" in changes:
        duplicate_product = (
            db.query(Product)
            .filter(
                Product.business_id == business.id,
                Product.sku == changes["sku"],
                Product.id != product.id,
            )
            .first()
        )

        if duplicate_product:
            raise HTTPException(
                status_code=409,
                detail="Bu SKU ile kayıtlı bir ürün zaten mevcut",
            )

    _ensure_references_belong_to_business(
        db,
        business.id,
        changes.get("category_id"),
        changes.get("supplier_id"),
    )

    for field, value in changes.items():
        setattr(product, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Bu SKU ile kayıtlı bir ürün zaten mevcut",
        )

    db.refresh(product)

    return _product_to_response(product)


@router.delete(
    "/{product_id}",
    status_code=204,
)
def delete_product(
    product_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _origin: None = Depends(require_trusted_origin),
    _csrf: None = Depends(require_csrf),
) -> None:
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
            Product.id == product_id,
            Product.business_id == business.id,
            Product.is_active.is_(True),
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="PRODUCT_NOT_FOUND",
        )

    product.is_active = False

    db.commit()