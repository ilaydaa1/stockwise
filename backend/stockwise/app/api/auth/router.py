from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy.orm import Session

from stockwise.app.core.config import settings
from stockwise.app.core.limiter import limiter
from stockwise.app.core.security import hash_password, verify_password
from stockwise.app.core.deps import (
    create_session,
    destroy_session,
    get_current_user,
    require_csrf,
    require_trusted_origin,
)
from stockwise.app.db.session import get_db
from stockwise.app.models.user import User
from stockwise.app.api.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse, status_code=201)
@limiter.limit(settings.rate_limit_register)
def register(
    request: Request,
    body: RegisterRequest,
    db: Session = Depends(get_db),
    _origin: None = Depends(require_trusted_origin),
) -> MessageResponse:
    normalized_email = body.email.strip().lower()

    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Bu e-posta adresi zaten kayıtlı",
        )

    user = User(
        email=normalized_email,
        name=body.name.strip(),
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Bu e-posta adresi zaten kayıtlı",
        )
    db.refresh(user)

    return MessageResponse(message="Kayıt başarılı")


@router.post("/login", response_model=UserResponse)
@limiter.limit(settings.rate_limit_login)
def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Session = Depends(get_db),
    _origin: None = Depends(require_trusted_origin),
) -> UserResponse:
    normalized_email = body.email.strip().lower()

    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="E-posta veya şifre hatalı",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Hesap devre dışı bırakılmış",
        )

    create_session(response, db, user)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        created_at=user.created_at.isoformat(),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_csrf),
) -> MessageResponse:
    destroy_session(request, response, db)
    return MessageResponse(message="Çıkış yapıldı")


@router.get("/me", response_model=UserResponse)
def me(
    user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        created_at=user.created_at.isoformat(),
    )
