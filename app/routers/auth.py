import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.i18n import resolve_lang, t
from app.models import Role, User
from app.plans import TRIAL_DAYS
from app.security import (
    CurrentUser,
    clear_login_failures,
    login_attempt_allowed,
    login_user,
    logout_user,
    record_login_failure,
    record_signup,
    signup_allowed,
    verify_csrf,
    verify_password,
)
from app.services.onboarding import create_restaurant_with_admin
from app.templating import templates

router = APIRouter(tags=["auth"])
log = logging.getLogger(__name__)


def home_url_for(user: User) -> str:
    return "/superadmin" if user.role is Role.superadmin else "/admin"


@router.get("/login")
def login_form(request: Request, user: CurrentUser):
    if user is not None:
        return RedirectResponse(home_url_for(user), status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request, "login.html", {"error": None, "lang": resolve_lang(request)}
    )


@router.post("/login", dependencies=[Depends(verify_csrf)])
def login(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    client_ip = request.client.host if request.client else "unknown"

    def failure(message: str):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": message, "lang": resolve_lang(request)},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if not login_attempt_allowed(db, client_ip):
        return failure("Juda ko'p urinish. Bir necha daqiqadan so'ng qayta urinib ko'ring.")

    user = db.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        record_login_failure(db, client_ip)
        return failure("Login yoki parol noto'g'ri")

    clear_login_failures(db, client_ip)
    login_user(request, user)
    return RedirectResponse(home_url_for(user), status.HTTP_303_SEE_OTHER)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/login", status.HTTP_303_SEE_OTHER)


@router.get("/signup")
def signup_form(request: Request, user: CurrentUser):
    if user is not None:
        return RedirectResponse(home_url_for(user), status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "signup.html",
        {"error": None, "trial_days": TRIAL_DAYS, "form": {}, "lang": resolve_lang(request)},
    )


@router.post("/signup", dependencies=[Depends(verify_csrf)])
def signup(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    name: Annotated[str, Form()],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    slug: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
):
    submitted = {
        "name": name,
        "slug": slug,
        "username": username,
        "phone": phone,
        "email": email,
    }

    client_ip = request.client.host if request.client else "unknown"
    if not signup_allowed(db, client_ip):
        return templates.TemplateResponse(
            request,
            "signup.html",
            {
                "error": t("signup_throttled", resolve_lang(request)),
                "trial_days": TRIAL_DAYS,
                "form": submitted,
                "lang": resolve_lang(request),
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    # Urinish natijasidan qat'i nazar sanaladi: maqsad xatoni ushlash emas,
    # bitta manbadan kelayotgan restoran oqimini cheklash
    record_signup(db, client_ip)

    try:
        restaurant = create_restaurant_with_admin(
            db,
            name=name,
            slug=slug,
            username=username,
            password=password,
            email=email,
            phone=phone,
            with_trial=True,
        )
    except HTTPException as error:
        # Xatoda forma to'ldirilgan holida qaytadi — hammasini qaytadan yozmasin
        return templates.TemplateResponse(
            request,
            "signup.html",
            {
                "error": error.detail,
                "trial_days": TRIAL_DAYS,
                "form": submitted,
                "lang": resolve_lang(request),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    log.info("Yangi restoran ro'yxatdan o'tdi: %s (%s)", restaurant.name, restaurant.slug)
    user = db.scalar(select(User).where(User.restaurant_id == restaurant.id))
    login_user(request, user)
    return RedirectResponse("/admin", status.HTTP_303_SEE_OTHER)
