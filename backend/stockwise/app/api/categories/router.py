from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from stockwise.app.api.categories.schemas import (
    CategoryResponse,
    CreateCategoryRequest,
)
from stockwise.app.core.deps import (
    get_current_business,
    require_csrf,
    require_trusted_origin,
)
from stockwise.app.db.session import get_db
from stockwise.app.models.business import Business
from stockwise.app.models.category import Category


router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> list[Category]:
    return (
        db.query(Category)
        .filter(Category.business_id == business.id)
        .order_by(Category.name.asc())
        .all()
    )


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    body: CreateCategoryRequest,
    _origin: None = Depends(require_trusted_origin),
    _csrf: None = Depends(require_csrf),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> Category:
    category = Category(
        business_id=business.id,
        name=body.name,
    )

    db.add(category)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="CATEGORY_ALREADY_EXISTS",
        )

    db.refresh(category)

    return category
