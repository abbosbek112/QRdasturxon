import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, settings
from app.flash import set_flash
from app.i18n import resolve_lang, t
from app.logging_setup import configure_logging
from app.routers import admin, api, auth, hall, public, superadmin
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


# Kirish talab qiladigan bo'limlar. Ular brauzer keshiga tushmasligi kerak.
#
# Sabab: chiqishdan keyin "orqaga" bosilsa brauzer saqlangan sahifani
# ekranga qaytaradi va oldingi odamning paneli ko'rinib qoladi. Kafedagi
# umumiy planshetda yoki afitsantning telefonida bu haqiqiy muammo.
#
# Yangi so'rov baribir kirish sahifasiga yuboriladi — lekin ekranda turgan
# ma'lumot allaqachon ko'ringan bo'lardi.
XAVFSIZ_YOLLAR = ("/admin", "/superadmin", "/zal", "/api/")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)

    if request.url.path.startswith(XAVFSIZ_YOLLAR):
        # `no-store` — saqlama; `must-revalidate` eski brauzerlar uchun.
        # bfcache ("orqaga" tugmasi) aynan shu sarlavhaga qaraydi.
        response.headers.setdefault(
            "Cache-Control", "no-store, no-cache, must-revalidate, private"
        )
        response.headers.setdefault("Pragma", "no-cache")
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
app.include_router(api.router)
app.include_router(hall.root)  # /sw.js — ildizdan berilishi shart
app.include_router(hall.router)
app.include_router(superadmin.router)


def _way_back(request: Request) -> str:
    """Xato sahifasidagi "Orqaga" qayerga olib borsin.

    Avval doim "/" edi — panelda ishlayotgan odam xatoga uchrasa reklama
    sahifasiga tashlanardi. Endi kelgan sahifasiga qaytadi.

    Referer FAQAT o'z saytimizniki bo'lsa ishlatiladi: u brauzerdan keladi,
    ya'ni begona manzil qo'yib yuborish mumkin va busiz sahifamiz boshqa
    saytga yo'naltirish quroliga aylanardi.
    """
    referer = request.headers.get("referer") or ""
    here = str(request.base_url).rstrip("/")
    if referer.startswith(here + "/") and referer != str(request.url):
        return referer
    # Referer yo'q bo'lsa ham panelda ishlayotgan odam reklama
    # sahifasiga tushib qolmasin
    if request.url.path.startswith("/admin"):
        return "/admin"
    return "/"


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    location = (exc.headers or {}).get("Location")
    if location:
        return RedirectResponse(location, status_code=exc.status_code)
    # Ilova va media JSON kutadi — ularga HTML xato sahifasi yuborilsa
    # ilova uni o'qiy olmay "noma'lum xato" ko'rsatardi
    if request.url.path.startswith(("/media", "/api/")):
        return JSONResponse(
            {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
        )

    # Panelda forma to'ldirayotgan odam xato tufayli BO'SH sahifaga
    # tushib qolmasin.
    #
    # Haqiqiy holat: egasi kategoriya nomini uch tilda yozib, rasm
    # tanlaydi va yuboradi. Rasm iPhone formatida bo'lgani uchun rad
    # etiladi va u "400 — Fayl rasm emas" degan yalang'och sahifaga
    # tushadi. Yozganlarining hammasi yo'qoladi va nima qilishi
    # ham tushunarsiz.
    #
    # Endi o'sha sahifaga qaytariladi va xabar tepasida chiqadi.
    # Faqat FOYDALANUVCHI xatosi shunday ishlanadi: 403 (CSRF) va 404
    # o'z holicha qoladi, chunki ularni yumshoq xabarga aylantirish
    # haqiqiy muammoni yashirardi.
    if (
        request.method == "POST"
        and request.url.path.startswith("/admin")
        and exc.status_code in (400, 413)
    ):
        set_flash(request, exc.detail)
        return RedirectResponse(_way_back(request), status_code=303)
    lang = resolve_lang(request)
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "lang": lang,
            "status_code": exc.status_code,
            "message": exc.detail or t("not_found", lang),
            "back_url": _way_back(request),
        },
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Kutilmagan xato — logga to'liq yoziladi, mijozga esa oddiy sahifa."""
    log.exception("So'rovda kutilmagan xato: %s %s", request.method, request.url.path)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Server xatosi"}, status_code=500)
    lang = resolve_lang(request)
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "lang": lang,
            "status_code": 500,
            "message": t("not_found", lang),
            "back_url": _way_back(request),
        },
        status_code=500,
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
