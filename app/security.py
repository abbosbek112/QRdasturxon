import secrets
from datetime import datetime, timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LoginAttempt, Role, User, utcnow_naive

_hasher = PasswordHasher()

SESSION_USER_KEY = "user_id"
SESSION_CSRF_KEY = "csrf_token"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def login_user(request: Request, user: User) -> None:
    request.session.clear()
    request.session[SESSION_USER_KEY] = user.id


def logout_user(request: Request) -> None:
    request.session.clear()


def csrf_token(request: Request) -> str:
    token = request.session.get(SESSION_CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[SESSION_CSRF_KEY] = token
    return token


async def verify_csrf(request: Request) -> None:
    form = await request.form()
    submitted = form.get("csrf_token")
    expected = request.session.get(SESSION_CSRF_KEY)
    if not expected or not isinstance(submitted, str) or not secrets.compare_digest(submitted, expected):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF tekshiruvidan o'tmadi")


def get_current_user(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> User | None:
    user_id = request.session.get(SESSION_USER_KEY)
    if not user_id:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        request.session.clear()
        return None
    return user


CurrentUser = Annotated[User | None, Depends(get_current_user)]


def _redirect_to_login() -> HTTPException:
    return HTTPException(status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})


def require_user(user: CurrentUser) -> User:
    if user is None:
        raise _redirect_to_login()
    return user


def require_superadmin(user: CurrentUser) -> User:
    if user is None:
        raise _redirect_to_login()
    if user.role is not Role.superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ruxsat yo'q")
    return user


def require_restaurant_admin(user: CurrentUser) -> User:
    if user is None:
        raise _redirect_to_login()
    if user.role is not Role.restaurant_admin or user.restaurant_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ruxsat yo'q")
    return user


MAX_ATTEMPTS = 8
WINDOW_SECONDS = 300


def _window_start() -> datetime:
    return utcnow_naive() - timedelta(seconds=WINDOW_SECONDS)


def login_attempt_allowed(db: Session, client_ip: str) -> bool:
    recent = db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.ip == client_ip, LoginAttempt.created_at >= _window_start())
    )
    return (recent or 0) < MAX_ATTEMPTS


def record_login_failure(db: Session, client_ip: str) -> None:
    db.add(LoginAttempt(ip=client_ip))
    # Eskirgan yozuvlarni shu yerda tozalaymiz — alohida vazifa kerak bo'lmaydi
    db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < _window_start()))
    db.commit()


def clear_login_failures(db: Session, client_ip: str) -> None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.ip == client_ip))
    db.commit()
