from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, User
from app.security import (
    CurrentUser,
    clear_login_failures,
    login_attempt_allowed,
    login_user,
    logout_user,
    record_login_failure,
    verify_csrf,
    verify_password,
)
from app.templating import templates

router = APIRouter(tags=["auth"])


def home_url_for(user: User) -> str:
    return "/superadmin" if user.role is Role.superadmin else "/admin"


@router.get("/login")
def login_form(request: Request, user: CurrentUser):
    if user is not None:
        return RedirectResponse(home_url_for(user), status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", {"error": None})


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
            request, "login.html", {"error": message}, status_code=status.HTTP_401_UNAUTHORIZED
        )

    if not login_attempt_allowed(client_ip):
        return failure("Juda ko'p urinish. Bir necha daqiqadan so'ng qayta urinib ko'ring.")

    user = db.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        record_login_failure(client_ip)
        return failure("Login yoki parol noto'g'ri")

    clear_login_failures(client_ip)
    login_user(request, user)
    return RedirectResponse(home_url_for(user), status.HTTP_303_SEE_OTHER)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/login", status.HTTP_303_SEE_OTHER)
