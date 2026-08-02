from fastapi.templating import Jinja2Templates

from app import themes
from app.config import BASE_DIR, settings
from app.i18n import LANGUAGES, t, tr
from app.plans import trial_days_left
from app.security import csrf_token

templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")


def _asset_version() -> str:
    """Eng oxirgi o'zgargan static fayl vaqti.

    CSS/JS havolasiga ?v=... bo'lib qo'shiladi: fayl o'zgarmasa brauzer keshdan
    oladi, o'zgarsa yangisini yuklaydi. Busiz yangilanishdan keyin mijozda eski
    dizayn qolib ketadi.
    """
    static_dir = BASE_DIR / "app" / "static"
    newest = max(
        (path.stat().st_mtime for path in static_dir.rglob("*") if path.is_file()),
        default=0.0,
    )
    return format(int(newest), "x")


def theme_css(restaurant) -> str:
    """Restoran tanlagan uslub uchun CSS o'zgaruvchilari.

    Shablonlarda har safar themes modulini chaqirmaslik uchun global qilingan.
    """
    if restaurant is None:
        return ""
    return themes.css_variables(themes.get(restaurant.theme), restaurant.theme_color)


templates.env.globals.update(
    t=t,
    tr=tr,
    csrf_token=csrf_token,
    LANGUAGES=LANGUAGES,
    asset_v=_asset_version(),
    theme_css=theme_css,
    # Panel qobig'idagi ogohlantirish tasmasi shuni chaqiradi — marshrutlarga
    # tegmasdan har bir admin sahifasida ishlashi uchun global
    trial_days_left=trial_days_left,
    # Bosh sahifadagi ko'rgazma uslublarni restoransiz chizadi: har bir
    # namuna karta o'z palitrasini shu yerdan oladi
    css_variables=themes.css_variables,
    THEMES=themes.THEMES,
    # Havola kartochkasidagi manzillar MUTLAQ bo'lishi shart — Telegram va
    # Facebook nisbiy yo'lni tanimaydi
    BASE_URL=settings.base_url.rstrip("/"),
    CONTACT={
        "phone": settings.contact_phone,
        "phone_href": settings.contact_phone_href,
        "telegram": settings.contact_telegram,
    },
)


def format_price(value) -> str:
    return f"{int(value):,}".replace(",", " ")


templates.env.filters["price"] = format_price
