import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, settings
from app.i18n import resolve_lang, t
from app.logging_setup import configure_logging
from app.routers import admin, auth, public, superadmin
from app.templating import templates

configure_logging(settings.debug)
log = logging.getLogger("qrdasturxon")

app = FastAPI(title="QRdasturxon", debug=settings.debug)

# Barcha JS tashqi fayllarda — shuning uchun script-src 'self' qo'yish mumkin,
# bu XSS xavfini keskin kamaytiradi. style-src'da 'unsafe-inline' qoladi:
# shablonlarda inline style= ko'p va restoran rangi ham inline <style> orqali beriladi.
CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'"
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=not settings.debug,
    same_site="lax",
    max_age=settings.session_max_age,
)

settings.media_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
app.mount("/media", StaticFiles(directory=settings.media_path), name="media")

app.include_router(auth.router)
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(superadmin.router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    location = (exc.headers or {}).get("Location")
    if location:
        return RedirectResponse(location, status_code=exc.status_code)
    if request.url.path.startswith("/media"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    lang = resolve_lang(request)
    return templates.TemplateResponse(
        request,
        "error.html",
        {"lang": lang, "status_code": exc.status_code, "message": exc.detail or t("not_found", lang)},
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Kutilmagan xato — logga to'liq yoziladi, mijozga esa oddiy sahifa."""
    log.exception("So'rovda kutilmagan xato: %s %s", request.method, request.url.path)
    lang = resolve_lang(request)
    return templates.TemplateResponse(
        request,
        "error.html",
        {"lang": lang, "status_code": 500, "message": t("not_found", lang)},
        status_code=500,
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
