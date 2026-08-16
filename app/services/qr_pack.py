"""Restoranning barcha QR kodlari — bitta arxivda.

Ilgari egasi har stolning QR'ini alohida yuklab olardi: o'ttiz stol uchun
o'ttiz marta bosish, va brauzer fayllarni `qr.png`, `qr (1).png`, `qr (2).png`
deb saqlab qo'yardi — qaysi biri qaysi stolniki ekani yo'qolardi. Chop
etishdan oldin ularni bittalab ochib tekshirishga to'g'ri kelardi.

Endi bitta tugma butun binoni beradi. Arxiv ichida qavat va bo'lim
papkalari bor, fayl nomi esa o'tirish joyining o'zi:

    menyu.png
    1-qavat/Asosiy-zal/1-stol.png
    2-qavat/VIP/11-stol.png
    bolimsiz/5-stol.png

Uch ko'rinishda beriladi: yalang'och QR, chop etishga tayyor kartochka va
egasining o'z rasmiga qo'yilgan QR.
"""

import re
import unicodedata
import zipfile
from io import BytesIO
from typing import Iterator, NamedTuple

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from app.models import Restaurant, Table, Zone
from app.services import areas, qr, tables
from app.templating import floor_label, seat_label

# Arxivdagi ko'rinishlar. Qiymatlar formadan keladi, shuning uchun qisqa.
QR_ONLY = "qr"
CARD = "karta"
OWN_IMAGE = "rasm"
STYLES = (QR_ONLY, CARD, OWN_IMAGE)

# Egasining rasmida QR qayerga tushadi
POSITIONS = ("markaz", "yuqori", "past")

# A6, 300 dpi — stol ustidagi kartochkaning odatdagi o'lchami
CARD_SIZE = (1240, 1748)

# Egasining rasmi shundan kattaroq bo'lsa kichraytiriladi: 200 ta stol
# uchun 200 marta ishlanadi va xotira cheklangan bo'lishi kerak
MAX_BACKGROUND_WIDTH = 2000

# Kichik rasm kattalashtiriladi. Egasi logotipini yuklab qo'yishi mumkin
# va 100x100 rasmga QR ham, stol yozuvi ham sig'masdi — chizish tashqariga
# chiqib ketib, sahifa 500 bilan yiqilardi.
MIN_BACKGROUND_SIDE = 700

# Kattalashtirishning yuqori chegarasi. Cho'zilgan rasmda qisqa tomonni
# 700 ga yetkazish uchun uzun tomon ancha o'sadi; 4000 dan nari
# ketmasligi har kartochkaga ketadigan ishni chegarada ushlab turadi.
MAX_BACKGROUND_LONG = 4000

# Bundan ingichka rasmda skanerlanadigan QR va uning ostidagi yozuv
# jismonan sig'maydi. Bunday faylni jimgina qabul qilib, foydasiz
# lentalar chiqarib berishdan ko'ra ochiq aytgan ma'qul.
MIN_USABLE_SIDE = 300


class Entry(NamedTuple):
    """Arxivdagi bitta fayl."""

    path: str
    data: bytes


class TooNarrow(ValueError):
    """Egasining rasmi QR sig'maydigan darajada ingichka."""


# ---------------------------------------------------------------- fayl nomi

# Kirill yozuvi lotinga o'giriladi. Sabab: ZIP nomlari UTF-8 bo'lishi
# mumkin, lekin Windows Explorer'ning eski nusxalari ularni buzib
# ko'rsatadi va egasi papkalarni o'qiy olmay qoladi.
_CYRILLIC = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    # o'zbek kirilligi
    "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
}

# Apostrof ajratuvchi emas, harfning bir qismi: `o'` va `g'` o'zbek
# alifbosidagi alohida harflar. Uni chiziqchaga almashtirsak "Yerto'la"
# "Yerto-la" bo'lib ketardi, shuning uchun butunlay tashlanadi.
_APOSTROPHE = re.compile(r"['‘’ʻʼʹ`´]")

# Nomda ruxsat etilgan belgilar. Ro'yxat ATAYLAB tor: `/` va `\` bu yerga
# tushmasligi arxivni ochganda fayl boshqa papkaga chiqib ketmasligini
# kafolatlaydi. Bo'lim nomini egasi yozadi, ya'ni bu ishonchsiz matn.
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")
_DASHES = re.compile(r"-{2,}")
_MAX_NAME = 48


def _to_latin(ch: str) -> str:
    """Bitta kirill harfini lotinga o'giradi, katta-kichikligini saqlab."""
    mapped = _CYRILLIC.get(ch.lower())
    if mapped is None:
        return ch
    return mapped.capitalize() if ch.isupper() else mapped


def safe_name(text: str, fallback: str = "nomsiz") -> str:
    """Matnni istalgan tizimda ochiladigan fayl nomiga aylantiradi.

    Uch ish qiladi: kirillni lotinga o'giradi, urg'u belgilarini tashlaydi
    (`é` → `e`) va qolgan hamma narsani chiziqchaga almashtiradi. Natijada
    faqat `A-Za-z0-9._-` qoladi.

    Nom bo'sh chiqsa yoki faqat nuqtadan iborat bo'lsa zaxira nom
    ishlatiladi — `..` degan nom arxivni ochganda yuqoridagi papkaga
    chiqib ketishga urinish bo'lardi.
    """
    latin = "".join(_to_latin(ch) for ch in text)
    # `NFKD` urg'uni harfdan ajratadi, keyin ajralgan belgilar tashlanadi
    stripped = unicodedata.normalize("NFKD", latin)
    stripped = "".join(ch for ch in stripped if not unicodedata.combining(ch))

    cleaned = _SAFE.sub("-", _APOSTROPHE.sub("", stripped))
    cleaned = _DASHES.sub("-", cleaned).strip("-.")[:_MAX_NAME].strip("-.")

    if not cleaned or not cleaned.strip("."):
        return fallback
    return cleaned


def _unique(path: str, taken: set[str]) -> str:
    """Bir xil nom ikki marta chiqmasin.

    Nomlar lotinga o'girilgandan keyin to'qnashishi mumkin: "Зал" va "Zal"
    ikkalasi ham `Zal` bo'ladi. ZIP takroriy nomga e'tiroz bildirmaydi —
    u shunchaki ikkita fayl yozadi va ochilganda biri yo'qoladi.
    """
    if path not in taken:
        taken.add(path)
        return path

    # `rpartition` nuqta topmasa hamma narsani OXIRGI bo'lakka soladi:
    # "menyu" uchun stem bo'sh, suffix "menyu" bo'lib, nom "-2.menyu"
    # bo'lib chiqardi. Hozir har yo'l kengaytma bilan tugaydi, lekin bu
    # shartga tayanib qolmaslik kerak.
    stem, nuqta, suffix = path.rpartition(".")
    if not nuqta:
        stem, suffix = path, ""

    def nomla(counter: int) -> str:
        return f"{stem}-{counter}.{suffix}" if suffix else f"{stem}-{counter}"

    counter = 2
    while nomla(counter) in taken:
        counter += 1
    numbered = nomla(counter)
    taken.add(numbered)
    return numbered


def table_path(table: Table, zone: Zone | None, lang: str, extension: str) -> str:
    """Stolning arxiv ichidagi to'liq yo'li: `2-qavat/VIP/11-stol.png`."""
    seat = safe_name(seat_label(table.kind, table.label, lang), f"stol-{table.id}")

    if zone is None:
        # Bo'limi yo'q stollar ham chiqadi — ular ham chop etilishi kerak
        return f"{safe_name(_no_zone_folder(lang))}/{seat}.{extension}"

    floor = safe_name(floor_label(zone.floor, lang), "qavat")
    return f"{floor}/{safe_name(zone.name, f'bolim-{zone.id}')}/{seat}.{extension}"


def _no_zone_folder(lang: str) -> str:
    return {"ru": "bez-razdela", "en": "no-section"}.get(lang, "bolimsiz")


# ------------------------------------------------------------------ shrift

# Kartochkadagi yozuv uchun. `python:3.13-slim` da shrift yo'q, shuning
# uchun Dockerfile `fonts-dejavu-core` o'rnatadi. Topilmasa Pillow'ning
# ichki shrifti ishlatiladi: xunukroq, lekin sahifa yiqilmaydi.
_FONT_FILES = {
    True: "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    False: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
}
_font_cache: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


def _font(size: int, bold: bool = False):
    key = (size, bold)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(_FONT_FILES[bold], size)
        except OSError:
            _font_cache[key] = ImageFont.load_default(size=size)
    return _font_cache[key]


def _centered(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill, width: int) -> int:
    """Matnni gorizontal markazga qo'yadi va egallagan balandligini qaytaradi."""
    if not text:
        return 0
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text(((width - (right - left)) / 2 - left, y - top), text, font=font, fill=fill)
    return bottom - top


def _fit(text: str, font_size: int, max_width: int, bold: bool) -> ImageFont.FreeTypeFont:
    """Uzun nom kartochkaning chetidan chiqib ketmasin — shrift kichrayadi."""
    size = font_size
    while size > 16:
        font = _font(size, bold)
        if font.getlength(text) <= max_width:
            return font
        size -= 4
    return _font(16, bold)


# -------------------------------------------------------------- ko'rinishlar


def _qr_image(url: str, box_size: int = 10) -> Image.Image:
    return Image.open(BytesIO(qr.png_bytes(url, box_size))).convert("RGB")


def _as_png(image: Image.Image) -> bytes:
    """Kartochkani kulrang PNG qilib saqlaydi.

    Kartochka ATAYLAB oq-qora: nusxa ko'chirish do'konida arzon chiqadi va
    QR ranglardan foyda ko'rmaydi. Ya'ni kulrangga o'tkazishda hech narsa
    yo'qolmaydi, lekin fayl RGB'dan ikki barobar kichrayadi.

    Palitrali (`P`) ko'rinish yana bir oz kichikroq chiqardi, lekin uning
    ranglarni tanlashi 200 ta stol uchun 23 soniya qo'shardi — bir xil
    natijaga o'n barobar qimmat yo'l. `optimize` ham shu sababdan
    o'chirilgan: 3 KB tejash uchun har kartochkaga 18 ms.
    """
    buffer = BytesIO()
    image.convert("L").save(buffer, "PNG")
    return buffer.getvalue()


def _as_jpeg(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=88, optimize=True)
    return buffer.getvalue()


def render_card(url: str, title: str, caption: str, hint: str) -> bytes:
    """Qirqmasdan chop etishga tayyor kartochka.

    Tepada restoran nomi, o'rtada QR, ostida katta harflar bilan stol
    yozuvi. Stol yozuvi ataylab yirik: ofitsiant ham, mijoz ham qaysi
    stolda o'tirganini bir qarashda bilishi kerak.
    """
    width, height = CARD_SIZE
    card = Image.new("RGB", CARD_SIZE, "white")
    draw = ImageDraw.Draw(card)

    ink = (17, 24, 39)
    muted = (107, 114, 128)
    margin = 90
    inner = width - margin * 2

    y = 120
    y += _centered(draw, y, title, _fit(title, 68, inner, True), ink, width) + 70

    code = _qr_image(url, 12)
    side = min(inner, height - y - 380)
    code = code.resize((side, side), Image.NEAREST)
    card.paste(code, ((width - side) // 2, y))
    y += side + 80

    y += _centered(draw, y, caption, _fit(caption, 104, inner, True), ink, width) + 46
    _centered(draw, y, hint, _fit(hint, 40, inner, False), muted, width)

    return _as_png(card)


def _big_enough(background: Image.Image) -> Image.Image:
    """Juda kichik rasmni QR sig'adigan darajaga kattalashtiradi.

    Egasi logotipini yuklab qo'yishi mumkin. 100x100 rasmda QR ham, uning
    ostidagi yozuv ham joyiga sig'masdi va chizish rasmdan tashqariga
    chiqib, so'rov 500 bilan tugardi.

    Kattalashtirish uzun tomon bo'yicha CHEKLANGAN: 60x900 kabi cho'zilgan
    rasm aks holda 700x10500 ga o'sib, har kartochkaga yetti megapiksel
    ishlov berishga majbur qilardi.

    Cheklovdan keyin ham qisqa tomon juda ingichka qolsa — masalan 3000x70
    lenta — QR va yozuv jismonan sig'maydi. Bunday fayl RAD ETILADI:
    ilgari u chizishni rasmdan chiqarib yuborib, so'rovni 500 bilan
    tugatardi va egasi sababini bilmasdi.
    """
    width, height = background.size
    qisqa, uzun = min(width, height), max(width, height)
    kattalik = min(MIN_BACKGROUND_SIDE / qisqa, MAX_BACKGROUND_LONG / uzun)

    if qisqa < MIN_BACKGROUND_SIDE and kattalik > 1:
        yirik = background.resize(
            (round(width * kattalik), round(height * kattalik)), Image.LANCZOS
        )
    else:
        yirik = background.copy()

    if min(yirik.size) < MIN_USABLE_SIDE:
        raise TooNarrow(
            "Rasm juda ingichka — QR va stol raqami sig'maydi. "
            "Kvadratga yaqinroq yoki bo'yiga cho'zilgan rasm yuklang."
        )
    return yirik


# QR o'lchamining chegaralari, eng qisqa tomonga nisbatan foizda.
#
# Standart 38% ATAYLAB. QR rasmining chetida majburiy bo'sh hoshiya bor
# va SKANERLANADIGAN kvadrat rasmning o'zidan ~10% kichik chiqadi: 34%
# qo'yilganda haqiqiy kvadrat 31% ga tushib qoladi. Buni test o'lchaydi
# (`test_the_qr_is_big_enough_to_scan_from_print`) — u aynan shu
# kamchilikni ushlagan.
#
# Pastki chegara 20%: undan kichik QR stol kartochkasida bir qarich
# masofadan ham o'qilmaydi va egasi buni faqat restoranda, mijoz
# uddalay olmaganda bilib qolardi.
MIN_QR_PERCENT = 20
MAX_QR_PERCENT = 60
DEFAULT_QR_PERCENT = 38

# Tayyor joylar — JS ishlamaganda ishlatiladi. Qiymat: (x, y) markazi,
# rasm o'lchamiga nisbatan foizda.
POSITION_POINTS = {
    "markaz": (50, 46),
    "yuqori": (50, 22),
    "past": (50, 74),
}


def render_on_background(
    background: Image.Image,
    url: str,
    caption: str,
    position: str = "markaz",
    spot: tuple[float, float] | None = None,
    percent: int = DEFAULT_QR_PERCENT,
) -> bytes:
    """Egasining o'z rasmiga QR va stol yozuvini qo'yadi.

    Joyni egasi TANLAYDI: `spot` — QR markazining rasmga nisbatan
    o'rni, foizda. Ilgari faqat uchta qo'pol joy bor edi va QR ko'pincha
    taomning ustiga tushib, rasmni ham, o'zini ham buzardi.

    `spot` berilmasa tayyor joylardan biri olinadi — JS ishlamaganda
    forma shu yo'l bilan ishlaydi.

    O'lchami ham egasida, lekin chegara bilan: juda kichik QR bir
    metrdan skanerlanmaydi va buni egasi faqat restoranda, mijoz
    uddalay olmaganda bilib qolardi.

    Yozuv oq to'rtburchak ustiga tushadi, chunki rasmning rangi oldindan
    noma'lum va qora yozuv qora fonda ko'rinmay qolardi.
    """
    canvas = _big_enough(background)
    width, height = canvas.size

    percent = max(MIN_QR_PERCENT, min(int(percent or DEFAULT_QR_PERCENT), MAX_QR_PERCENT))
    side = int(min(width, height) * percent / 100)

    code = _qr_image(url, 12).resize((side, side), Image.NEAREST)

    if spot is None:
        spot = POSITION_POINTS.get(position, POSITION_POINTS["markaz"])
    cx, cy = spot
    x = int(width * cx / 100) - side // 2
    y = int(height * cy / 100) - side // 2

    # Rasmdan chiqib ketmasin: egasi chetga surib qo'ysa QR yarmi
    # qirqilib, umuman skanerlanmay qolardi
    x = max(10, min(x, width - side - 10))
    y = max(10, min(y, height - side - 10))

    # QR ostidagi oq hoshiya: rangli fonda ham kamera aniq o'qisin
    pad = max(8, side // 24)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([x - pad, y - pad, x + side + pad, y + side + pad], fill="white")
    canvas.paste(code, (x, y))

    font = _fit(caption, max(20, side // 7), side + pad * 2, True)
    left, top, right, bottom = draw.textbbox((0, 0), caption, font=font)
    text_w, text_h = right - left, bottom - top
    box_h = text_h + pad

    #
    # Yozuv odatda QR OSTIDA turadi. Lekin egasi QR'ni pastga surib
    # qo'ysa u yerda joy qolmaydi — unda yozuv QR USTIGA chiqadi.
    #
    # Ilgari bunday tekshiruv yo'q edi va to'rtburchakning pastki cheti
    # yuqorigisidan baland bo'lib qolib, Pillow "y1 must be greater than
    # y0" deb yiqilardi. Ya'ni egasi QR'ni pastga qo'ysa butun arxiv
    # yaratilmasdi.
    #
    oraliq = max(6, side // 30)
    box_top = y + side + pad + oraliq
    if box_top + box_h > height - 4:
        box_top = y - pad - oraliq - box_h
    # Tepada ham sig'masa (juda past rasm) — QR ichiga, pastki chetiga
    box_top = max(4, min(box_top, height - box_h - 4))

    qr_markaz = x + side / 2
    draw.rectangle(
        [qr_markaz - text_w / 2 - pad, box_top,
         qr_markaz + text_w / 2 + pad, box_top + box_h],
        fill="white",
    )
    draw.text(
        (qr_markaz - text_w / 2 - left, box_top + pad / 2 - top),
        caption, font=font, fill=(17, 24, 39),
    )

    return _as_jpeg(canvas)


def prepare_background(raw: bytes) -> Image.Image:
    """Yuklangan rasmni tayyorlaydi va yaroqliligini SHU YERDA tekshiradi.

    Tekshiruv ataylab shu yerda: rasm yaroqsiz bo'lsa bu haqda birinchi
    kartochka chizilishidan oldin bilish kerak. Aks holda xato butun arxiv
    yasalayotgan paytda chiqib, egasi tushunarli xabar o'rniga 500 ni
    ko'rardi.
    """
    from PIL import ImageOps

    with Image.open(BytesIO(raw)) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        if image.width > MAX_BACKGROUND_WIDTH:
            new_height = round(image.height * MAX_BACKGROUND_WIDTH / image.width)
            image = image.resize((MAX_BACKGROUND_WIDTH, new_height), Image.LANCZOS)
        return _big_enough(image)


# --------------------------------------------------------------- arxiv


def entries(
    db: Session,
    restaurant: Restaurant,
    lang: str = "uz",
    style: str = QR_ONLY,
    background: Image.Image | None = None,
    position: str = "markaz",
    hint: str = "",
    spot: tuple[float, float] | None = None,
    percent: int = DEFAULT_QR_PERCENT,
) -> Iterator[Entry]:
    """Arxivga tushadigan fayllar.

    Menyu QR'i HAR DOIM birinchi bo'lib chiqadi — buyurtma tizimini
    yoqmagan restoranda stol umuman bo'lmaydi va arxiv bo'sh chiqib
    ketardi. Menyu QR'i esa bunday restoranga aynan kerak bo'lgan narsa.
    """
    if style == OWN_IMAGE and background is None:
        style = CARD

    extension = "jpg" if style == OWN_IMAGE else "png"
    taken: set[str] = set()

    menu_url = qr.menu_url(restaurant.slug)
    menu_caption = restaurant.name
    if style == QR_ONLY:
        menu_data = qr.png_bytes(menu_url)
    elif style == OWN_IMAGE:
        menu_data = render_on_background(background, menu_url, menu_caption, position, spot, percent)
    else:
        menu_data = render_card(menu_url, restaurant.name, menu_caption, hint)
    yield Entry(_unique(f"menyu.{extension}", taken), menu_data)

    if not restaurant.orders_enabled:
        return

    # Bo'limlar bir marta olinadi. `table.zone` orqali yurish har stol uchun
    # alohida so'rov bo'lardi — 200 ta stolda bu 200 ta ortiqcha so'rov.
    zones = {zone.id: zone for zone in areas.list_zones(db, restaurant.id)}

    for table in tables.list_for(db, restaurant.id):
        url = qr.table_url(restaurant.slug, table.code)
        caption = seat_label(table.kind, table.label, lang)
        if style == QR_ONLY:
            data = qr.png_bytes(url)
        elif style == OWN_IMAGE:
            data = render_on_background(background, url, caption, position, spot, percent)
        else:
            data = render_card(url, restaurant.name, caption, hint)
        path = table_path(table, zones.get(table.zone_id), lang, extension)
        yield Entry(_unique(path, taken), data)


def build(
    db: Session,
    restaurant: Restaurant,
    lang: str = "uz",
    style: str = QR_ONLY,
    background: Image.Image | None = None,
    position: str = "markaz",
    hint: str = "",
    spot: tuple[float, float] | None = None,
    percent: int = DEFAULT_QR_PERCENT,
) -> bytes:
    """Tayyor ZIP arxivi."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry in entries(db, restaurant, lang, style, background, position, hint, spot, percent):
            archive.writestr(entry.path, entry.data)
    return buffer.getvalue()


def filename(restaurant: Restaurant) -> str:
    """Yuklab olinadigan arxivning nomi."""
    return f"{safe_name(restaurant.slug, 'restoran')}-qr.zip"


__all__ = [
    "CARD", "OWN_IMAGE", "QR_ONLY", "STYLES", "POSITIONS",
    "TooNarrow",
    "build", "entries", "filename", "prepare_background", "safe_name", "table_path",
]
