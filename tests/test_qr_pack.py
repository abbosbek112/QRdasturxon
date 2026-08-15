"""Barcha QR'larni bitta arxivda yuklab olish.

Egasi o'ttiz stolning QR'ini bittalab yuklab olardi va brauzer ularni
`qr.png`, `qr (1).png` deb saqlab, qaysi biri qaysi stolniki ekanini
yo'qotardi. Endi bitta so'rov butun binoni beradi.

Ikki narsa alohida sinaladi, chunki ikkalasi ham jimgina buziladigan
turdan: arxivda BOSHQA restoranning stoli chiqib qolishi va bo'lim nomi
orqali fayl arxivdan tashqariga yozilishi.
"""

import io
import zipfile

import pytest
from PIL import Image

from app.models import Table, Zone
from app.services import qr_pack

from tests.conftest import csrf, login


def zip_of(response) -> zipfile.ZipFile:
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    return zipfile.ZipFile(io.BytesIO(response.content))


def download(client, **fields) -> object:
    token = csrf(client, "/admin/tables")
    return client.post("/admin/tables/qr-pack", data={"csrf_token": token, **fields})


@pytest.fixture
def bino(db, tenant_a):
    """Ikki qavatli restoran: yerto'la, birinchi qavat va bo'limsiz stol."""
    restaurant, _ = tenant_a
    restaurant.orders_enabled = True

    zal = Zone(restaurant_id=restaurant.id, name="Asosiy zal", floor=1)
    vip = Zone(restaurant_id=restaurant.id, name="VIP xonalar", floor=2)
    yerto = Zone(restaurant_id=restaurant.id, name="Yerto'la", floor=-1)
    db.add_all([zal, vip, yerto])
    db.flush()

    db.add_all([
        Table(restaurant_id=restaurant.id, label="1", code="kod-bir", zone_id=zal.id),
        Table(restaurant_id=restaurant.id, label="2", code="kod-ikki", zone_id=zal.id),
        Table(restaurant_id=restaurant.id, label="7", code="kod-yetti", zone_id=vip.id),
        Table(restaurant_id=restaurant.id, label="9", code="kod-toqqiz", zone_id=yerto.id),
        # Bo'limi yo'q stol ham chop etilishi kerak
        Table(restaurant_id=restaurant.id, label="30", code="kod-ottiz"),
    ])
    db.commit()
    return restaurant


# --------------------------------------------------------------- tegishlilik


def test_archive_holds_only_this_restaurants_tables(client, db, bino, tenant_b):
    """Eng muhim tekshiruv: qo'shni restoranning stoli tushib qolmasin.

    Arxiv butun binoni oladi, ya'ni bu yerda `restaurant_id` bo'yicha
    filtr yo'qolsa hech qanday xato chiqmaydi — egasi shunchaki begona
    stollarning QR'larini ham olib qo'ya qoladi.
    """
    boshqa, _ = tenant_b
    boshqa.orders_enabled = True
    db.add(Table(restaurant_id=boshqa.id, label="1", code="begona-kod"))
    db.commit()

    login(client, "osh", "adminpass123")
    archive = zip_of(download(client))

    hammasi = b"".join(archive.read(name) for name in archive.namelist())
    assert b"begona-kod" not in hammasi

    # 5 ta stol + menyu QR'i
    assert len(archive.namelist()) == 6


def test_another_owner_cannot_download_someone_elses(client, db, bino, tenant_b):
    """Qo'shni restoran egasi kirsa — o'z arxivini oladi, bu restorannikini emas."""
    boshqa, _ = tenant_b
    boshqa.orders_enabled = True
    db.commit()

    login(client, "choy", "adminpass123")
    archive = zip_of(download(client))

    assert archive.namelist() == ["menyu.png"]


def test_anonymous_is_turned_away(client, bino):
    response = client.post("/admin/tables/qr-pack", data={"style": "qr"})
    assert response.status_code in (302, 303, 401, 403)
    assert b"PK" != response.content[:2]


def test_csrf_token_is_required(client, bino):
    login(client, "osh", "adminpass123")
    response = client.post("/admin/tables/qr-pack", data={"style": "qr"})
    assert response.status_code == 403


# ------------------------------------------------------------- fayl nomlari


def test_file_names_say_where_the_qr_belongs(client, bino):
    """Talabning o'zagi: nomiga qayerning QR'i ekani yozilgan bo'lsin."""
    login(client, "osh", "adminpass123")
    nomlar = set(zip_of(download(client)).namelist())

    assert "1-qavat/Asosiy-zal/1-stol.png" in nomlar
    assert "1-qavat/Asosiy-zal/2-stol.png" in nomlar
    assert "2-qavat/VIP-xonalar/7-stol.png" in nomlar
    assert "1-yertola/Yertola/9-stol.png" in nomlar
    assert "bolimsiz/30-stol.png" in nomlar
    assert "menyu.png" in nomlar


def test_menu_qr_is_there_even_without_tables(client, db, tenant_a):
    """Buyurtma tizimini yoqmagan restoranda stol yo'q, lekin menyu QR'i bor.

    Busiz arxiv butunlay bo'sh chiqardi va egasi tugma buzuq deb o'ylardi.
    """
    restaurant, _ = tenant_a
    restaurant.orders_enabled = False
    db.commit()

    login(client, "osh", "adminpass123")
    archive = zip_of(download(client))

    assert archive.namelist() == ["menyu.png"]


def test_tables_are_skipped_when_ordering_is_off(client, db, bino):
    """Buyurtma o'chirilgan bo'lsa stol QR'i ish bermaydi — chiqarilmaydi."""
    bino.orders_enabled = False
    db.commit()

    login(client, "osh", "adminpass123")
    assert zip_of(download(client)).namelist() == ["menyu.png"]


# ------------------------------------------------------------------ xavfsizlik


@pytest.mark.parametrize(
    "yomon_nom",
    ["../../etc", "..", "/etc/passwd", "C:\\Windows", "....//....//tmp"],
)
def test_zone_name_cannot_escape_the_archive(client, db, bino, yomon_nom):
    """Bo'lim nomini egasi yozadi — ya'ni bu ishonchsiz matn.

    Arxiv ichida `..` qolsa, ba'zi ochish dasturlari faylni maqsad
    papkadan TASHQARIGA yozadi. Nom tozalagichi shuni to'sadi.
    """
    zone = db.query(Zone).filter(Zone.name == "Asosiy zal").one()
    zone.name = yomon_nom
    db.commit()

    login(client, "osh", "adminpass123")
    nomlar = zip_of(download(client)).namelist()

    for name in nomlar:
        assert ".." not in name, name
        assert not name.startswith("/"), name
        assert "\\" not in name, name


def test_a_bad_name_still_produces_a_usable_file(client, db, bino):
    """Nom butunlay yaroqsiz bo'lsa fayl yo'qolib ketmasin — zaxira nom olsin."""
    zone = db.query(Zone).filter(Zone.name == "Asosiy zal").one()
    zone.name = ".."
    db.commit()

    login(client, "osh", "adminpass123")
    nomlar = zip_of(download(client)).namelist()

    assert any(name.endswith("1-stol.png") for name in nomlar)
    assert len(nomlar) == 6


def test_names_that_fold_to_the_same_ascii_do_not_overwrite(db, bino):
    """Turli stollar bir xil fayl nomiga tushib qolmasin.

    Stol yozuvi bazada betakror, lekin lotinga o'girilgandan keyin
    to'qnashishi mumkin: "Café" ham, "Cafe" ham `Cafe` bo'ladi. ZIP bunga
    e'tiroz bildirmaydi — ikkita yozuv yasaydi, ochilganda esa biri
    ikkinchisini bosib ketadi va bitta stol QR'siz qoladi.
    """
    zal = db.query(Zone).filter(Zone.name == "Asosiy zal").one()
    db.add_all([
        Table(restaurant_id=bino.id, label="Café", code="kod-cafe", zone_id=zal.id),
        Table(restaurant_id=bino.id, label="Cafe", code="kod-cafe-2", zone_id=zal.id),
    ])
    db.commit()

    nomlar = [entry.path for entry in qr_pack.entries(db, bino)]
    assert len(nomlar) == len(set(nomlar)), nomlar
    # Ikkala stol ham arxivda qoldi
    assert sum("Cafe" in name for name in nomlar) == 2


# ------------------------------------------------------------- ko'rinishlar


def test_unknown_style_falls_back_to_a_plain_qr(client, bino):
    """Forma qiymati ishonchsiz — noma'lum ko'rinish yalang'och QR bersin.

    Fayl turini tekshirish yetarli EMAS: kartochka ham `.png` bo'lib
    chiqadi. Shuning uchun mazmuni aynan yalang'och QR bilan solishtiriladi
    — aks holda tekshiruv qiymat umuman tekshirilmasa ham o'tib ketardi.
    """
    login(client, "osh", "adminpass123")
    archive = zip_of(download(client, style="hech-qanaqa"))

    kutilgan = qr_pack.qr.png_bytes(qr_pack.qr.table_url(bino.slug, "kod-bir"))
    assert archive.read("1-qavat/Asosiy-zal/1-stol.png") == kutilgan
    assert len(archive.namelist()) == 6


def test_card_style_draws_the_seat_name(client, bino):
    """Kartochkada stol yozuvi bo'lishi kerak — usiz qaysi biri qaysi stol?"""
    login(client, "osh", "adminpass123")
    archive = zip_of(download(client, style="karta"))

    karta = Image.open(io.BytesIO(archive.read("1-qavat/Asosiy-zal/1-stol.png")))
    assert karta.size == qr_pack.CARD_SIZE
    # Yalang'och QR'dan kattaroq: demak atrofida yozuv va hoshiya bor
    assert len(archive.read("1-qavat/Asosiy-zal/1-stol.png")) > len(
        qr_pack.qr.png_bytes(qr_pack.qr.table_url(bino.slug, "kod-bir"))
    )


@pytest.mark.parametrize("style, extension", [("karta", "png"), ("rasm", "jpg")])
def test_the_qr_is_big_enough_to_scan_from_print(client, bino, tmp_path, style, extension):
    """QR chop etilgan kartochkada bir metrdan o'qiladigan bo'lsin.

    Dekodlash tekshiruvi buni USHLAMAYDI: rasm faylida QR o'nlab marta
    kichraytirilsa ham dastur uni bemalol o'qiydi. Odam esa telefonini
    kartochkaga tirab o'tirmaydi — o'lchamning o'zi alohida talab.

    Chegara — rasmning eng qisqa tomonining uchdan biri: bundan kichigi
    stol ustidan turib skanerlashni qiyinlashtiradi. Aynan qisqa tomonga
    nisbatan, chunki egasining rasmi bo'yiga cho'zilgan ham bo'lishi
    mumkin va QR o'sha tomonga qarab o'lchanadi.

    O'lchov QR'ning O'ZIDAN emas, dekoder topgan kvadratdan olinadi:
    rasm chetidagi bo'sh hoshiya skanerlanmaydi va uni hisobga qo'shish
    QR'ni haqiqatdan kattaroq ko'rsatardi.
    """
    zxingcpp = pytest.importorskip("zxingcpp")

    login(client, "osh", "adminpass123")
    if style == "rasm":
        fon = tmp_path / "fon.png"
        Image.new("RGB", (900, 1300), (240, 240, 240)).save(fon)
        token = csrf(client, "/admin/tables")
        with fon.open("rb") as handle:
            response = client.post(
                "/admin/tables/qr-pack",
                data={"csrf_token": token, "style": style},
                files={"background": ("fon.png", handle, "image/png")},
            )
    else:
        response = download(client, style=style)
    archive = zip_of(response)

    rasm = Image.open(io.BytesIO(archive.read(f"1-qavat/Asosiy-zal/1-stol.{extension}")))
    joy = zxingcpp.read_barcodes(rasm)[0].position
    kengligi = joy.top_right.x - joy.top_left.x
    qisqa_tomon = min(rasm.size)

    assert kengligi >= qisqa_tomon / 3, (
        f"{style}: QR qisqa tomonning {kengligi / qisqa_tomon:.0%} qismi — juda kichik"
    )


def test_own_image_style_keeps_the_owners_picture(client, bino, tmp_path):
    """Egasining rasmi asos bo'lib qoladi, QR uning ustiga tushadi."""
    fon = tmp_path / "fon.png"
    Image.new("RGB", (800, 1200), (12, 80, 160)).save(fon)

    login(client, "osh", "adminpass123")
    token = csrf(client, "/admin/tables")
    with fon.open("rb") as handle:
        response = client.post(
            "/admin/tables/qr-pack",
            data={"csrf_token": token, "style": "rasm", "position": "past"},
            files={"background": ("fon.png", handle, "image/png")},
        )
    archive = zip_of(response)

    assert "1-qavat/Asosiy-zal/1-stol.jpg" in archive.namelist()
    chiqdi = Image.open(io.BytesIO(archive.read("1-qavat/Asosiy-zal/1-stol.jpg")))
    assert chiqdi.size == (800, 1200)
    # Egasining ko'k foni tepada tegilmagan holda qolgan
    assert chiqdi.getpixel((10, 10))[2] > chiqdi.getpixel((10, 10))[0]


@pytest.mark.parametrize("olcham", [(1, 1), (100, 100), (200, 300), (2000, 2000), (1500, 500)])
@pytest.mark.parametrize("joy", ["markaz", "yuqori", "past"])
def test_a_small_background_is_enlarged_instead_of_breaking(olcham, joy):
    """Egasi logotipini yuklasa ham QR o'qiladigan chiqsin.

    100x100 rasmda QR ham, yozuv ham sig'masdi: chizish rasm chegarasidan
    chiqib ketib, butun so'rov 500 bilan tugardi. Buni egasi "yuklab olish
    ishlamayapti" deb ko'rardi va sababini bilmasdi.
    """
    zxingcpp = pytest.importorskip("zxingcpp")

    chiqdi = qr_pack.render_on_background(
        Image.new("RGB", olcham, (250, 250, 250)),
        "https://qrdasturxon.tech/r/bodom/t/abcd1234",
        "12-stol",
        joy,
    )
    rasm = Image.open(io.BytesIO(chiqdi))
    assert zxingcpp.read_barcodes(rasm), f"{olcham} {joy} — QR o'qilmadi"
    # Kattalashtirish chegarada qolsin: har kartochkaga ketadigan ish
    # rasm shakliga qarab cheksiz o'sib ketmasin
    assert max(rasm.size) <= qr_pack.MAX_BACKGROUND_LONG


@pytest.mark.parametrize("olcham", [(60, 900), (900, 60), (3000, 70), (5000, 40)])
def test_a_ribbon_shaped_background_is_refused_with_a_reason(olcham):
    """Lentasimon rasmda QR sig'maydi — jimgina foydasiz fayl bermasin.

    Ilgari bunday rasm chizishni chegaradan chiqarib yuborib, so'rovni
    500 bilan tugatardi. Endi sababi aytiladi.
    """
    with pytest.raises(qr_pack.TooNarrow):
        qr_pack.render_on_background(
            Image.new("RGB", olcham, "white"), "https://x.uz/r/a/t/b", "12-stol", "markaz"
        )


def test_a_ribbon_upload_gets_a_clear_answer_not_a_crash(client, bino, tmp_path):
    """Marshrut ham 500 emas, tushunarli 400 bersin."""
    lenta = tmp_path / "lenta.png"
    Image.new("RGB", (3000, 70), "white").save(lenta)

    login(client, "osh", "adminpass123")
    token = csrf(client, "/admin/tables")
    with lenta.open("rb") as handle:
        response = client.post(
            "/admin/tables/qr-pack",
            data={"csrf_token": token, "style": "rasm"},
            files={"background": ("lenta.png", handle, "image/png")},
        )

    assert response.status_code == 400
    assert "ingichka" in response.text


def test_own_image_without_a_file_falls_back_to_a_card(client, bino):
    """Rasm tanlanib, fayl berilmasa 500 emas — kartochka chiqsin."""
    login(client, "osh", "adminpass123")
    archive = zip_of(download(client, style="rasm"))

    assert "1-qavat/Asosiy-zal/1-stol.png" in archive.namelist()


def test_a_file_that_is_not_an_image_is_refused_clearly(client, bino):
    """Xato fayl 500 bermasin — tushunarli javob bo'lsin."""
    login(client, "osh", "adminpass123")
    token = csrf(client, "/admin/tables")
    response = client.post(
        "/admin/tables/qr-pack",
        data={"csrf_token": token, "style": "rasm"},
        files={"background": ("hujjat.pdf", io.BytesIO(b"%PDF-1.4 emas rasm"), "application/pdf")},
    )
    assert response.status_code == 400


# ------------------------------------------------------------------ arxiv


def test_the_archive_actually_opens(client, bino):
    login(client, "osh", "adminpass123")
    archive = zip_of(download(client))

    assert archive.testzip() is None
    for name in archive.namelist():
        assert archive.read(name), name


@pytest.mark.parametrize("style", ["qr", "karta"])
def test_every_qr_can_actually_be_scanned(client, db, bino, style):
    """Arxivdagi har bir QR chindan o'qilishi kerak.

    Bu boshqa hech qanday tekshiruv ushlamaydigan xato: rasm joyida
    bo'lib, o'lchami to'g'ri bo'lib, lekin skanerlanmasligi mumkin —
    masalan hoshiya yo'qolsa yoki kartochka QR'ni qirqib qo'ysa. Egasi
    buni faqat yuz dona kartochka chop etgandan keyin bilib qolardi.

    Shuning uchun QR chindan dekodlanadi va ichidagi manzil kutilganiga
    solishtiriladi — ya'ni har stol O'Z sahifasiga olib borishi ham
    tekshiriladi. Stollar almashib ketsa buyurtma boshqa stolga tushardi.
    """
    zxingcpp = pytest.importorskip("zxingcpp")

    login(client, "osh", "adminpass123")
    archive = zip_of(download(client, style=style))

    # Kutilgan xarita BAZADAN quriladi, arxivdan emas — shuning uchun
    # yo'l bilan manzil noto'g'ri juftlashgan bo'lsa shu yerda ko'rinadi
    zones = {zone.id: zone for zone in db.query(Zone).filter(Zone.restaurant_id == bino.id)}
    kutilgan = {"menyu.png": qr_pack.qr.menu_url(bino.slug)}
    for table in db.query(Table).filter(Table.restaurant_id == bino.id):
        yol = qr_pack.table_path(table, zones.get(table.zone_id), "uz", "png")
        kutilgan[yol] = qr_pack.qr.table_url(bino.slug, table.code)

    assert set(archive.namelist()) == set(kutilgan)

    for name in archive.namelist():
        topilgan = zxingcpp.read_barcodes(Image.open(io.BytesIO(archive.read(name))))
        assert topilgan, f"{name} — QR o'qilmadi"
        assert topilgan[0].text == kutilgan[name], f"{name} boshqa joyga olib boryapti"


def test_the_file_is_offered_as_a_download(client, bino):
    login(client, "osh", "adminpass123")
    response = download(client)

    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment")
    assert "osh-markazi-qr.zip" in disposition


# ---------------------------------------------------------------- nom tozalash


@pytest.mark.parametrize(
    "kirish, kutilgan",
    [
        ("Asosiy zal", "Asosiy-zal"),
        ("Основной зал", "Osnovnoy-zal"),
        ("Ўзбек", "Ozbek"),
        ("Café", "Cafe"),
        # Apostrof o'zbekchada harfning bir qismi, ajratuvchi emas
        ("Yerto'la", "Yertola"),
        ("Yerto‘la", "Yertola"),
        ("To`yxona", "Toyxona"),
        ("Terassa (yozgi)", "Terassa-yozgi"),
        # Yo'ldan chiqarishga urinishlar
        ("../../etc/passwd", "etc-passwd"),
        ("..", "nomsiz"),
        ("...", "nomsiz"),
        ("/", "nomsiz"),
        ("", "nomsiz"),
        ("   ", "nomsiz"),
        ("C:\\Windows", "C-Windows"),
    ],
)
def test_safe_name(kirish, kutilgan):
    assert qr_pack.safe_name(kirish) == kutilgan


def test_safe_name_never_returns_something_dangerous():
    """Tozalagich hech qachon papkadan chiqadigan nom bermasin."""
    for kirish in ["../..", "a/../../b", "..\\..\\x", "\x00/etc", "." * 60]:
        natija = qr_pack.safe_name(kirish)
        assert "/" not in natija
        assert "\\" not in natija
        assert natija.strip(".") or natija == "nomsiz"
        assert natija != ".."


def test_a_name_without_an_extension_keeps_its_shape():
    """Takror nom raqamlanganda nom buzilmasin.

    `rpartition` nuqta topmasa hamma narsani oxirgi bo'lakka soladi va
    "menyu" ikkinchi marta kelganda "-2.menyu" bo'lib chiqardi — oldida
    chiziqcha, orqasida soxta kengaytma.
    """
    taken: set[str] = set()
    assert qr_pack._unique("menyu", taken) == "menyu"
    assert qr_pack._unique("menyu", taken) == "menyu-2"
    assert qr_pack._unique("menyu", taken) == "menyu-3"

    # Kengaytmali nom o'z holicha qoladi
    taken = set()
    assert qr_pack._unique("a.png", taken) == "a.png"
    assert qr_pack._unique("a.png", taken) == "a-2.png"
