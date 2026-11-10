from datetime import datetime, timezone, timedelta

from fastapi import Request, Response, HTTPException, Depends
from sqlalchemy.orm import Session

from stockwise.app.core.config import settings
from stockwise.app.core.security import generate_session_token, hash_token
from stockwise.app.db.session import get_db
from stockwise.app.models.business import Business
from stockwise.app.models.user import User
from stockwise.app.models.session import AuthSession

SESSION_COOKIE_NAME = "sw_session"
CSRF_COOKIE_NAME = "sw_csrf"
CSRF_HEADER_NAME = "x-csrf-token"


def _get_session_cookie_settings(remember_me: bool = False) -> dict:
    cookie_settings = {
        "httponly": True,
        "secure": settings.session_cookie_secure,
        "samesite": settings.session_cookie_same_site,
        "path": "/",
    }

    if remember_me:
        cookie_settings["max_age"] = settings.session_cookie_max_age

    return cookie_settings


def _get_csrf_cookie_settings(remember_me: bool = False) -> dict:
    cookie_settings = {
        "httponly": False,
        "secure": settings.session_cookie_secure,
        "samesite": settings.session_cookie_same_site,
        "path": "/",
    }

    if remember_me:
        cookie_settings["max_age"] = settings.session_cookie_max_age

    return cookie_settings


def require_trusted_origin(request: Request) -> None:
    origin = request.headers.get("origin")

    if origin is None:
        return

    if origin not in settings.allowed_cors_origins:
        raise HTTPException(
            status_code=403,
            detail="Origin not allowed",
        )


def create_session(
    response: Response,
    db: Session,
    user: User,
    remember_me: bool = False,
) -> AuthSession:
    token = generate_session_token()
    token_hash = hash_token(token)

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(seconds=settings.session_cookie_max_age)
    )

    session = AuthSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        **_get_session_cookie_settings(remember_me),
    )

    csrf_token = generate_session_token()

    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        **_get_csrf_cookie_settings(remember_me),
    )

    return session


def destroy_session(
    request: Request,
    response: Response,
    db: Session,
) -> None:
    token = request.cookies.get(SESSION_COOKIE_NAME)

    if token:
        token_hash = hash_token(token)

        session = (
            db.query(AuthSession)
            .filter(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
            )
            .first()
        )

        if session:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()

    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
    )

    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path="/",
    )


def _validate_csrf(request: Request) -> None:
    cookie_value = request.cookies.get(CSRF_COOKIE_NAME)
    header_value = request.headers.get(CSRF_HEADER_NAME)

    if not cookie_value or not header_value:
        raise HTTPException(
            status_code=403,
            detail="CSRF token missing",
        )

    if cookie_value != header_value:
        raise HTTPException(
            status_code=403,
            detail="CSRF token mismatch",
        )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    token_hash = hash_token(token)
    now = datetime.now(timezone.utc)

    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid",
        )

    user = (
        db.query(User)
        .filter(
            User.id == session.user_id,
            User.is_active.is_(True),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive",
        )

    return user


def require_csrf(request: Request) -> None:
    _validate_csrf(request)


def get_current_business(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Business:
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

    return business