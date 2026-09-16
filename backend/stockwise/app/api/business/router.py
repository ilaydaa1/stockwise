from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from stockwise.app.core.deps import (
    get_current_user,
    require_csrf,
    require_trusted_origin,
)
from stockwise.app.db.session import get_db
from stockwise.app.models.user import User
from stockwise.app.models.business import Business
from stockwise.app.api.business.schemas import (
    CreateBusinessRequest,
    BusinessResponse,
)

router = APIRouter(prefix="/businesses", tags=["businesses"])


def _business_to_response(business: Business) -> BusinessResponse:
    return BusinessResponse(
        id=str(business.id),
        owner_id=str(business.owner_id),
        name=business.name,
        currency=business.currency,
        timezone=business.timezone,
        created_at=business.created_at.isoformat(),
        updated_at=business.updated_at.isoformat(),
    )


@router.post("", response_model=BusinessResponse, status_code=201)
def create_business(
    body: CreateBusinessRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _origin: None = Depends(require_trusted_origin),
    _csrf: None = Depends(require_csrf),
) -> BusinessResponse:
    existing = db.query(Business).filter(Business.owner_id == user.id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Zaten bir işletme oluşturmuşsunuz",
        )

    business = Business(
        owner_id=user.id,
        name=body.name.strip(),
        currency=body.currency,
        timezone=body.timezone,
    )
    db.add(business)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Zaten bir işletme oluşturmuşsunuz",
        )
    db.refresh(business)

    return _business_to_response(business)


@router.get("/me", response_model=BusinessResponse)
def get_my_business(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BusinessResponse:
    business = db.query(Business).filter(Business.owner_id == user.id).first()
    if not business:
        raise HTTPException(
            status_code=404,
            detail="BUSINESS_NOT_FOUND",
        )

    return _business_to_response(business)
