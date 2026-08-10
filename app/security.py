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


def require_hall_access(user: CurrentUser) -> User:
    """Buyurtmalar taxtasi: afitsant va restoran egasi.

    Egasi ham kiritilgan — kichik kafeda ko'pincha o'zi zalda yuradi va
    buning uchun alohida hisob ochib o'tirishi kerak emas. Teskarisi esa
    ishlamaydi: afitsant `require_restaurant_admin` dan o'tolmaydi, ya'ni
    menyu va narxlarga umuman yaqinlasha olmaydi.
    """
    if user is None:
        raise _redirect_to_login()
    if user.role not in (Role.waiter, Role.restaurant_admin) or user.restaurant_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ruxsat yo'q")
    return user


# --- IP bo'yicha cheklov ----------------------------------------------------
#
# Ikki xil urinish bir jadvalda yotadi, lekin ALOHIDA sanaladi. Sabab
# quyidagi: muvaffaqiyatli login o'z IP'sining yozuvlarini tozalaydi. Agar
# signup ham shu hisobga qo'shilsa, chegaraga yetgan odam bitta login qilib
# hisoblagichni nolga tushirib olardi — cheklov umuman ishlamas edi.

LOGIN = "login"
SIGNUP = "signup"

# Login: parol terishda adashish normal, shuning uchun oyna qisqa va keng
MAX_ATTEMPTS = 8
WINDOW_SECONDS = 300

# Signup: maqsad boshqa — bitta IP nechta restoran ocha olishini cheklash.
# Bitta kafe wi-fi ortidan bir necha odam ro'yxatdan o'tsa ham yetadi,
# skript bilan yaxshi slug'larni band qilishga esa yetmaydi.
MAX_SIGNUPS = 5
SIGNUP_WINDOW_SECONDS = 3600


def _window_start(seconds: int = WINDOW_SECONDS) -> datetime:
    return utcnow_naive() - timedelta(seconds=seconds)


def attempt_allowed(db: Session, client_ip: str, kind: str, limit: int, window: int) -> bool:
    recent = db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.ip == client_ip,
            LoginAttempt.kind == kind,
            LoginAttempt.created_at >= _window_start(window),
        )
    )
    return (recent or 0) < limit


def record_attempt(db: Session, client_ip: str, kind: str, window: int) -> None:
    db.add(LoginAttempt(ip=client_ip, kind=kind))
    # Eskirgan yozuvlarni shu yerda tozalaymiz — alohida vazifa kerak bo'lmaydi
    db.execute(
        delete(LoginAttempt).where(
            LoginAttempt.kind == kind, LoginAttempt.created_at < _window_start(window)
        )
    )
    db.commit()


# --- login (yupqa qobiq) ---

def login_attempt_allowed(db: Session, client_ip: str) -> bool:
    return attempt_allowed(db, client_ip, LOGIN, MAX_ATTEMPTS, WINDOW_SECONDS)


def record_login_failure(db: Session, client_ip: str) -> None:
    record_attempt(db, client_ip, LOGIN, WINDOW_SECONDS)


def clear_login_failures(db: Session, client_ip: str) -> None:
    """Muvaffaqiyatli login'dan keyin — faqat LOGIN yozuvlari o'chadi."""
    db.execute(
        delete(LoginAttempt).where(
            LoginAttempt.ip == client_ip, LoginAttempt.kind == LOGIN
        )
    )
    db.commit()


# --- ro'yxatdan o'tish ---

def signup_allowed(db: Session, client_ip: str) -> bool:
    return attempt_allowed(db, client_ip, SIGNUP, MAX_SIGNUPS, SIGNUP_WINDOW_SECONDS)


def record_signup(db: Session, client_ip: str) -> None:
    """Login'dan farqi: HAR BIR urinish sanaladi, muvaffaqiyatlisi ham.

    Maqsad xatoni ushlash emas, bitta manbadan kelayotgan restoran oqimini
    cheklash — shuning uchun muvaffaqiyatli ro'yxat ham hisobga kiradi.
    """
    record_attempt(db, client_ip, SIGNUP, SIGNUP_WINDOW_SECONDS)
