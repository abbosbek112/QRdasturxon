# QRdasturxon

Restoranlar uchun ko'p ijarali (multi-tenant) QR-menyu tizimi. Mijoz stoldagi QR kodni
skanerlaydi va telefonida restoran menyusini o'zbek, rus yoki ingliz tilida ko'radi.
Buyurtma va to'lov yo'q — bu faqat menyu ko'rsatish tizimi.

**Rollar**

| Rol | Nima qiladi |
|---|---|
| Tizim admini (superadmin) | Restoranlarni va ularning admin hisoblarini yaratadi |
| Restoran admini | O'z restorani menyusini, sozlamalarini va QR kodini boshqaradi |
| Mijoz | Ro'yxatdan o'tmaydi — QR orqali menyuni ko'radi |

## Texnologiyalar

FastAPI · Jinja2 · SQLAlchemy 2 + Alembic · SQLite · Pillow · qrcode · argon2

Tashqi CDN yoki frontend build-step yo'q — loyiha internetdan mustaqil ishlaydi.

## O'rnatish

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

`.env` faylini yarating:

```bash
cp .env.example .env
```

So'ng `.env` ichidagi `SECRET_KEY` ni uzun tasodifiy qatorga almashtiring:

```bash
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Bazani tayyorlang va tizim adminini yarating:

```bash
.venv/bin/alembic upgrade head
```

```bash
.venv/bin/python -m scripts.create_superadmin
```

## Ishga tushirish

```bash
.venv/bin/uvicorn app.main:app --reload
```

- Menyu: `http://localhost:8000/r/<slug>`
- Boshqaruv paneli: `http://localhost:8000/login`

## Testlar

```bash
.venv/bin/python -m pytest
```

## Sozlamalar (`.env`)

| Kalit | Vazifasi |
|---|---|
| `SECRET_KEY` | Sessiya cookie'sini imzolaydi. Ishlab chiqarishda albatta almashtiring |
| `DATABASE_URL` | Standart SQLite. Postgres uchun: `postgresql+psycopg://...` |
| `BASE_URL` | **QR kod ichiga shu manzil yoziladi** — domenga chiqishdan oldin o'zgartiring |
| `MEDIA_DIR` | Yuklangan rasmlar katalogi (standart `media/`) |
| `DEBUG` | `false` bo'lganda sessiya cookie'si faqat HTTPS orqali yuboriladi |

## Ma'lumotlar modeli

`users` · `restaurants` · `categories` · `menu_items`

Tarjima qilinadigan maydonlar (`name`, `description`, `address`) JSON ustunlarida
`{"uz": "...", "ru": "...", "en": "..."}` ko'rinishida saqlanadi. Tanlangan tilda matn
bo'lmasa o'zbekchaga qaytadi (`app/i18n.py` dagi `tr()`).

Til quyidagi tartibda aniqlanadi: `?lang=` → cookie → brauzerning `Accept-Language`
sarlavhasi → o'zbekcha.

Model o'zgartirilgandan keyin migratsiya yarating:

```bash
.venv/bin/alembic revision --autogenerate -m "tavsif"
```

## Xavfsizlik

- Har bir admin so'rovi restoranni **sessiyadan** oladi — begona restoran obyektiga
  murojaat 404 qaytaradi (`tests/test_tenancy.py`)
- Barcha holat o'zgartiruvchi formalarda CSRF token
- Yuklangan rasm Pillow orqali majburiy qayta kodlanadi (WebP), hajmi 5 MB bilan
  cheklangan; fayl nomi UUID
- Parollar argon2 bilan hashlanadi, login urinishlari IP bo'yicha cheklanadi

## Ishlab chiqarishga chiqarish

1. `.env` da `DEBUG=false`, haqiqiy `SECRET_KEY` va domenga mos `BASE_URL`
2. HTTPS majburiy — sessiya cookie'si `Secure` bayrog'i bilan yuboriladi
3. `media/` katalogini zaxiralashni unutmang — rasmlar bazada emas, diskda
4. Yuklama oshsa `DATABASE_URL` ni Postgres'ga o'tkazing va `alembic upgrade head` ni
   qayta ishga tushiring
