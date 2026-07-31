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

Jadvallar **migratsiyalar orqali** quriladi — shuning uchun har yugurishda
migratsiyalar ham tekshiriladi. Prod Postgres bo'lgani uchun testlarni o'sha bazada
ham yugurtirish mumkin:

```bash
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost/qrdasturxon_test .venv/bin/python -m pytest
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

## Serverga chiqarish

Docker Compose bilan uchta xizmat ko'tariladi: ilova, PostgreSQL va Caddy
(HTTPS sertifikatini o'zi oladi va yangilab turadi).

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY uchun
```

`.env` da to'ldiring: `DEBUG=false`, `SECRET_KEY`, `BASE_URL`, `DOMAIN`,
`POSTGRES_PASSWORD`. So'ng:

```bash
docker compose up -d --build
```

Migratsiyalar konteyner ishga tushganda avtomatik qo'llanadi. Birinchi superadminni
yaratish:

```bash
docker compose exec app python -m scripts.create_superadmin
```

**`BASE_URL` — QR kod ichiga yoziladigan manzil.** Uni domenga chiqqandan keyin
o'zgartirsangiz, chop etilgan QR kodlar eski manzilga ishora qilib qoladi.

Ishga tushmasa: `docker compose logs -f app`.

### Xavfsizlik tekshiruvi

`DEBUG=false` bo'lganda standart yoki 32 belgidan qisqa `SECRET_KEY` bilan **server
ataylab ko'tarilmaydi**. Bu xato emas — kalit zaif bo'lsa birov sessiyani soxtalashtirib
admin bo'lib kira oladi.

## Zaxira nusxa

```bash
./scripts/backup.sh              # ./backups ichiga
./scripts/backup.sh /mnt/zaxira  # boshqa joyga
```

Baza (`pg_dump`) va yuklangan rasmlar alohida arxivga tushadi, 30 kundan eskilari
o'chiriladi (`KEEP_DAYS` bilan o'zgartiriladi). Har kuni tunda ishlashi uchun:

```bash
0 3 * * * cd /srv/qrdasturxon && ./scripts/backup.sh >> /var/log/qrdasturxon-backup.log 2>&1
```

### Tiklash

Zaxira nusxaning qiymati faqat tiklab ko'rilganda bilinadi — buni **oldindan sinab
ko'ring**, kerak bo'lganda emas.

```bash
# Baza
gunzip -c backups/db-20260731-030000.sql.gz | \
  docker compose exec -T db psql -U qrdasturxon -d qrdasturxon

# Rasmlar
docker compose run --rm --no-deps --entrypoint sh \
  -v "$(pwd)/backups:/backup" app -c "tar xzf /backup/media-20260731-030000.tar.gz -C /app"
```

## Statistika

Admin bosh sahifasida oxirgi 30 kunlik ochilishlar grafigi va eng ko'p ochilgan
taomlar ro'yxati chiqadi.

Saqlanadigan narsa — faqat `(restoran, taom, sana, son)`. **IP, cookie yoki qurilma
haqida hech narsa yozilmaydi**, shuning uchun bu "necha kishi" emas, "necha marta
ochildi" degan ko'rsatkich. Sanalar UTC bo'yicha.
