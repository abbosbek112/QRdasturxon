from datetime import timedelta

from fastapi.templating import Jinja2Templates

from app import themes
from app.config import BASE_DIR, settings
from app.flash import pop_flash
from app.i18n import LANGUAGES, resolve_lang, t, tr
from app.plans import trial_days_left
from app.security import csrf_token

def _flash(request) -> dict:
    """Bir martalik xabar — ko'rsatilgach o'chadi (`app/flash.py`).

    Kontekst protsessori bo'lgani uchun har bir shablonda o'zi paydo bo'ladi
    va marshrutlarga uni qo'lda uzatish kerak emas.
    """
    return {"flash": pop_flash(request)}


def _language(request) -> dict:
    """Interfeys tili — har bir shablonga avtomatik qo'shiladi.

    Ataylab `lang` emas, `ui_lang`. Bular ikki xil narsa:

    * `lang` — menyu MAZMUNI qaysi tilda ko'rsatilishi. Uni marshrut beradi
      va tarif cheklashi mumkin (bepulda faqat o'zbekcha).
    * `ui_lang` — INTERFEYS tili: tugmalar, sarlavhalar, panel. Hech qachon
      cheklanmaydi.

    Nomlari bir xil bo'lsa, protsessor marshrut bergan qiymatni bosib
    qo'yardi (Starlette protsessorlarni kontekst USTIGA qo'llaydi) va bepul
    tarifdagi til cheklovi ishlamay qolardi.
    """
    return {"ui_lang": resolve_lang(request)}


templates = Jinja2Templates(
    directory=BASE_DIR / "app" / "templates",
    context_processors=[_language, _flash],
)


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


def seat_label(kind, label: str, lang: str) -> str:
    """O'tirish joyining mijoz ko'radigan nomi: "7-stol", "VIP 2", "3-xona".

    `kind` enum ham, oddiy matn ham bo'lishi mumkin: stol modelida u enum,
    buyurtmada esa nusxa sifatida matn bo'lib yotadi.
    """
    name = getattr(kind, "value", kind) or "stol"
    return t(f"kind_{name}", lang).replace("{n}", label)


def floor_label(floor: int, lang: str) -> str:
    """"2-qavat" yoki "1-yerto'la" — manfiy son yerto'la darajasini bildiradi.

    `0` eski ma'lumotda "yerto'la" degani edi; migratsiya uni `-1` ga
    o'tkazadi, lekin qaerdadir qolib ketgan bo'lsa ham to'g'ri o'qilsin.
    """
    if floor < 0:
        return t("floor_basement_n", lang).replace("{n}", str(-floor))
    if floor == 0:
        return t("floor_basement", lang)
    return t("floor_n", lang).replace("{n}", str(floor))


def new_order_count(restaurant) -> int:
    """Panel navigatsiyasidagi "javob kutayotgan buyurtma" soni.

    Marshrutlarga tegmaslik uchun global — tasma har bir admin sahifasida
    turadi. O'z sessiyasini ochadi, chunki shablonga baza ulanishi berilmagan.
    Buyurtma o'chirilgan restoranda so'rov umuman qilinmaydi.
    """
    if restaurant is None or not restaurant.orders_enabled:
        return 0
    from app.database import SessionLocal
    from app.services import orders

    with SessionLocal() as session:
        return orders.new_count(session, restaurant.id)


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
    # Navigatsiyadagi "javob kutayotgan buyurtma" belgisi
    new_order_count=new_order_count,
    # "7-stol" / "VIP 2" — turiga qarab
    seat_label=seat_label,
    floor_label=floor_label,
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


def localtime(value):
    """UTC vaqtni restoran mintaqasiga o'giradi (ekran uchun).

    Baza UTC saqlaydi va shundayligicha qolsin — taqqoslash shu bilan ishonchli.
    Lekin ekranda mahalliy vaqt turishi kerak: afitsant "06:14" ni ko'rib
    soatiga qarasa 11:14 turgan bo'lardi va buyurtma qachon kelganini
    tushunmasdi.
    """
    if value is None:
        return value
    return value + timedelta(hours=settings.utc_offset_hours)


templates.env.filters["price"] = format_price
templates.env.filters["localtime"] = localtime
