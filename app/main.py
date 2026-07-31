from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, settings
from app.i18n import resolve_lang, t
from app.routers import admin, auth, public, superadmin
from app.templating import templates

app = FastAPI(title="QRdasturxon", debug=settings.debug)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=not settings.debug,
    same_site="lax",
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


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
