# QRdasturxon

Kafe va restoranlar uchun ko'p ijarali (multi-tenant) QR-menyu platformasi. Mijoz
stoldagi QR kodni skanerlaydi va telefonida menyuni o'zbek, rus yoki ingliz tilida
ko'radi.

**Buyurtma va to'lov ataylab yo'q.** QR orqali buyurtma berishni ko'p kafe
pandemiyadan keyin tashlab yubordi: ofitsiant qimmat emas, dasturxon madaniyati
kuchli. Menyu-only mahsulot esa ancha arzon va ishonchli — bir kishi olib borishi mumkin.

**Rollar**

| Rol | Nima qiladi |
|---|---|
| Tizim admini (superadmin) | Restoranlarni ko'radi, tariflarni beradi va uzaytiradi |
| Restoran admini | O'z menyusi, sozlamalari, izohlari va QR kodini boshqaradi |
| Mijoz | Ro'yxatdan o'tmaydi — QR orqali menyuni ko'radi |

Restoran o'zi `/signup` orqali ro'yxatdan o'tadi va **7 kun bepul** sinov oladi.

## Imkoniyatlar

**Menyu (mijoz ko'radigan tomon)**

- Uch tilli menyu; tarjima bo'lmasa o'zbekchaga qaytadi
- Taomga bosilganda sahifa almashmaydi — pastdan **oyna** chiqadi (sudrab,
  overlay bosib, `Escape` yoki "orqaga" tugmasi bilan yopiladi). JS ishlamasa
  havola oddiy sahifa bo'lib ochiladi
- **Wi-Fi paroli** menyuning tepasida, bosilganda ochiladi
- Taom belgilari: o'tkir, vegetarian, halol; allergenlar; tayyorlanish vaqti
- **Bugungi taklif** — kategoriyalardan yuqoridagi alohida bo'lim
- Mijoz izohlari — restoran tasdiqlagandan keyin ko'rinadi
- To'rtta **uslub** (Zamonaviy, Klassik, Issiq, Minimal) — palitra, shrift va
  burchak yumaloqligini birga o'zgartiradi

**Boshqaruv paneli**

- Yangi restoran uchun uch qadamli yo'l-yo'riq; bajarilgach o'zi yo'qoladi
- QR kod: PNG va chop etishga tayyor SVG
- **Chop etish uchun menyu** — brauzerdan "PDF saqlash" qilinadigan A4 varaq
- Statistika: kunlik ochilishlar grafigi va eng ko'p ko'rilgan taomlar

## Tariflar

Yiliga bir marta to'lanadi. To'lov tizimi ulanmagan — restoran Telegram orqali
bog'lanadi, pul qo'lda qabul qilinadi, superadmin panelidan obuna uzaytiriladi.

| | Bepul | To'liq (500 000 so'm/yil) |
|---|---|---|
| Taom / kategoriya | 20 / 3 | cheksiz |
| Tillar | faqat o'zbekcha | uz + ru + en |
| Statistika | 7 kun | 365 kun |
| Wi-Fi, taom belgilari | bor | bor |
| Bugungi taklif, izohlar, chop etish | yo'q | bor |

### Muddat tugagach nima bo'ladi

Bepul rejim — **7 kunlik sinov**, undan nariga cho'zilmaydi. Muddat tugasa:

* stoldagi QR kod ishlamaydi — mijoz "menyu vaqtincha yopiq" sahifasini ko'radi
  (HTTP 503, ya'ni "vaqtincha", shuning uchun qidiruv tizimi sahifani o'chirmaydi);
* restoran egasi hisobiga bemalol kiradi, menyusi va rasmlari joyida turadi;
* obuna uzaytirilgach menyu o'sha zahoti qayta ochiladi.

Ochiq-yopiqlikni `plans.menu_is_live()` hal qiladi va u **sanaga** qaraydi,
bazadagi holatga emas. Sabab: `refresh_status()` faqat egasi panelga kirganda
ishlaydi, ya'ni holatga qarasak panelga kirmaslik sinovni cheksiz cho'zish
yo'liga aylanardi.

> Buning narxi bor: xato sahifasini restoranning aybsiz mijozi ko'radi. Shu
> sababli o'sha sahifada tarif ham, qarz ham tilga olinmaydi — faqat menyu
> vaqtincha yopiqligi aytiladi.

## Texnologiyalar

FastAPI · Jinja2 · SQLAlchemy 2 + Alembic · PostgreSQL (lokalda SQLite) ·
Pillow · qrcode · argon2

Tashqi CDN, frontend build-step va JS kutubxonasi yo'q — butun mijoz tomoni
40 qatorlik vanilla JS.

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

## Namuna menyu

Bosh sahifadagi "Namunani ko'rish" havolasi `DEMO_SLUG` sozlamasidagi menyuni
ochadi. Uni quyidagi buyruq to'ldirib beradi — 5 kategoriya, 10 ta taom,
rasmlar, izohlar va Wi-Fi paroligacha:

```bash
.venv/bin/python -m scripts.seed_demo
```

Qayta yugurtirsa bo'ladi: eski namuna butunlay o'chirilib, yangisi quriladi.
Faqat `DEMO_SLUG`ga tegadi, boshqa restoranlarga umuman tegmaydi.

Rasmlar `scripts/demo_art.py` da Pillow bilan chiziladi — internetdan hech narsa
yuklanmaydi. Bular foto emas, illyustratsiya; haqiqiy foto qo'yilsa menyu
chiroyliroq chiqadi va uni admin paneldan almashtirsa bo'ladi.

> Bu sozlama qo'shilishidan oldin namuna sifatida **eng eski restoran**
> ko'rsatilardi — ya'ni saytga kelgan odam haqiqiy mijozning menyusini namuna
> deb ko'rardi. `DEMO_SLUG` shuning uchun kerak.

### Bosh sahifadagi ko'rgazma

Imkoniyatlar bo'limi mahsulotni **ko'rsatadi**: statistika paneli, to'rt uslub,
izoh va yulduz, QR kod. Hamma maket mahsulotning o'z klasslaridan yig'iladi
(`.chart`, `.stat`, `.meter`, `.stars-show`, `.dish`, `.badge`) — dizayn
o'zgarsa ko'rgazma ham o'zi bilan o'zgaradi va eskirib qolmaydi.

Uslub kartalari `THEMES` bo'yicha aylanadi va palitrani `css_variables()` dan
oladi, ya'ni yangi uslub qo'shilsa bosh sahifaga hech narsa yozish shart emas.

> Palitra `<style>` blokiga chiqariladi, `style="..."` atributiga emas: uslub
> shriftlari ichida qo'shtirnoq bor (`"Iowan Old Style"`) va u atributni o'sha
> yerda uzib qo'yadi — natijada burchak radiusi va shrift qo'llanmay qoladi.

QR kod bezak emas: `qr.svg_markup()` namuna menyusi uchun **ishlaydigan** kod
yasaydi, uni ekrandan skanerlasa menyu ochiladi. Natija `lru_cache` bilan
saqlanadi. Namuna restoran bo'lmasa QR umuman chizilmaydi.

### Havola kartochkasi

Havola Telegram yoki Facebookka tashlanganda chiqadigan ko'rinish
(`public/base.html`, `<head>` ichida). Mahsulot aynan Telegram orqali
sotilgani uchun bu bevosita mijozga ta'sir qiladi.

| Sahifa | Nom | Rasm |
|---|---|---|
| Bosh sahifa | mahsulot nomi | `static/img/og.jpg` |
| Menyu `/r/<slug>` | **restoran nomi** | uning muqovasi |
| Taom sahifasi | taom + restoran | taom rasmi |

Menyu havolasini restoran o'z mijozlariga tarqatadi — o'sha yerda
QRdasturxon emas, restoranning o'zi ko'rinishi kerak. Muqova bo'lmasa
standart kartochkaga qaytadi.

Kartochka rasmi `scripts/demo_art.py` da **bir marta** chiziladi va static
fayl bo'lib qoladi:

```bash
.venv/bin/python -m scripts.demo_art
```

Ish paytida chizilmaydi, chunki Docker konteynerida shrift yo'q va bo'lishi
ham shart emas. Manzillar mutlaq (`BASE_URL`) — nisbiy yo'lni na Telegram,
na Facebook tanimaydi.

### Animatsiya

`static/js/landing.js` — IntersectionObserver, ~90 qator, bog'liqliksiz.
Element ekranga kirganda `is-in` klassi qo'yiladi va bir marta kuzatuvdan
chiqariladi. Statistika raqamlari noldan o'sib chiqadi.

Ikkita qoida:

* **JS o'chsa sahifa to'liq ko'rinadi.** Yashirish faqat `html.js` ostida
  ishlaydi, o'sha klassni esa shu faylning o'zi qo'yadi. Shuning uchun u
  `<head>` da, `defer` siz ulanadi — aks holda mazmun ko'rinib, keyin
  yashirinib, keyin qayta chiqardi.
* **`prefers-reduced-motion`** yoqilgan bo'lsa hech narsa harakatlanmaydi;
  JS ham, CSS ham buni alohida tekshiradi.

Bo'limlarda `overflow-x: clip` bor: yon tomondan kirib keladigan elementlar
animatsiyadan oldin o'ng chetdan oshib, gorizontal skroll hosil qilardi.
`hidden` emas, `clip` — `hidden` skroll konteyneri yasab, ichidagi sticky
sarlavhani buzardi.

Oxirgi bo'lim (`.lp-dark`) — sahifadagi yagona qorong'i joy. Ranglar shu blok
ichida qayta belgilanadi, ya'ni tugma va sarlavhalarga alohida qoida yozilmagan:
hammasi bir xil o'zgaruvchilardan foydalanadi.

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
| `CONTACT_PHONE` | Reklama sahifasida ko'rsatiladigan telefon |
| `CONTACT_TELEGRAM` | Telegram foydalanuvchi nomi (`@` siz) |
| `DEMO_SLUG` | "Namunani ko'rish" qaysi menyuni ochadi (standart `bodom`) |

## Ma'lumotlar modeli

`users` · `restaurants` · `categories` · `menu_items` · `item_comments` ·
`menu_views` · `login_attempts`

Tarjima qilinadigan maydonlar (`name`, `description`, `ingredients`, `allergens`,
`address`) JSON ustunlarida `{"uz": "...", "ru": "...", "en": "..."}` ko'rinishida
saqlanadi — Postgres'da **JSONB**. Tanlangan tilda matn bo'lmasa o'zbekchaga
qaytadi (`app/i18n.py` dagi `tr()`).

Muhim modullar:

| Fayl | Nima uchun |
|---|---|
| `app/plans.py` | Tariflar, cheklovlar, sinov muddati |
| `app/themes.py` | Uslub to'plamlari (palitra, shrift, burchak) |
| `app/services/onboarding.py` | Restoran yaratish va uch qadamli yo'l-yo'riq |
| `app/services/stats.py` | Kunlik ochilishlar hisobi |
| `app/services/comments.py` | Izohlar va spamdan himoya |

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
- Parollar argon2 bilan hashlanadi. Login urinishlari IP bo'yicha **bazada**
  hisoblanadi — server qayta ishga tushsa ham cheklov kuchida qoladi va bir nechta
  ishchi jarayon bitta hisobni ko'radi
- Javob sarlavhalarida CSP (`script-src 'self'` — inline JS umuman yo'q),
  `X-Frame-Options`, `nosniff`, `Referrer-Policy`
- `DEBUG=false` bo'lganda zaif yoki standart `SECRET_KEY` bilan **server
  ko'tarilmaydi** — bu ataylab, kalit ma'lum bo'lsa sessiyani soxtalashtirish mumkin
- Izohlar restoran tasdiqlagunicha ko'rinmaydi; bitta IP bir taomga kuniga bitta izoh

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
docker compose exec -T \
  -e SUPERADMIN_USERNAME=root -e SUPERADMIN_PASSWORD='uzun-parol' \
  app python -m scripts.create_superadmin
```

Skript interaktiv ham ishlaydi, lekin Docker ichida terminal bo'lmagani uchun
login va parolni muhit o'zgaruvchilari orqali berish kerak.

**`BASE_URL` — QR kod ichiga yoziladigan manzil.** Uni domenga chiqqandan keyin
o'zgartirsangiz, chop etilgan QR kodlar eski manzilga ishora qilib qoladi.

### Oracle Cloud (Always Free)

Ampere A1 instansi (4 CPU / 24 GB) muddatsiz bepul va bu loyihaga ortig'i bilan
yetadi. Lekin Oracle'da uchta tuzoq bor — ular boshqa provayderlarda uchramaydi.

**1. Always Free faqat "home region"da ishlaydi.** Region ro'yxatdan o'tishda
tanlanadi va **keyin o'zgartirilmaydi**. Instance o'sha regionda yaratilishi kerak.

**2. "Out of host capacity"** — ARM instansda tez-tez chiqadi va bu xato emas,
o'sha paytda joy yo'qligini bildiradi. Boshqa Availability Domain'ni tanlang,
2 CPU / 12 GB bilan urinib ko'ring yoki bir necha soatdan keyin qayta urining.

**3. Ikki qavatli firewall — eng ko'p vaqt yeydigan joy.** Portni faqat bulut
darajasida ochib qo'yish yetarli emas, operatsion tizimda ham ochish kerak.

Bulut darajasi — VCN → Subnet → Security List → *Add Ingress Rules*:
`0.0.0.0/0` uchun TCP **80** va **443**.

Operatsion tizim darajasi (Oracle'ning Ubuntu image'i SSH'dan boshqa hammasini
bloklaydi):

```bash
sudo iptables -I INPUT 6 -p tcp --dport 80 -m state --state NEW -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -m state --state NEW -j ACCEPT
sudo netfilter-persistent save
```

`sudo iptables -L INPUT --line-numbers` bilan tekshiring: ACCEPT qatorlari
REJECT'dan **yuqorida** turishi kerak.

**ARM haqida.** Image serverning o'zida quriladi, shuning uchun aarch64 avtomatik
hal bo'ladi — `python`, `postgres` va `caddy` image'lari ko'p arxitekturali.
Agar `pip install` bosqichida kutilmagan build xatosi chiqsa, biror paketning
aarch64 wheel'i yo'q degani: `Dockerfile` ning builder bosqichiga `build-essential`
qo'shish kifoya.

Docker o'rnatgandan keyin **SSH'dan chiqib qayta kiring** — `docker` guruhi
a'zoligi shundan keyin kuchga kiradi.

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

## Analitika va baholar

Mijoz izoh qoldirganda **1–5 yulduz** ham qo'yishi mumkin (ixtiyoriy). Baho
faqat restoran tasdiqlagan izohlardan hisoblanadi; yulduzsiz izohlar
o'rtachaga umuman qatnashmaydi.

Ikkita analitika sahifasi bor va ikkalasi ham bir xil oraliq tanlagichdan
foydalanadi — **bugun / 7 kun / 30 kun / 365 kun / ixtiyoriy sana**:

| Sahifa | Kim ko'radi | Nima ko'rsatadi |
|---|---|---|
| `/admin/stats` | restoran egasi | kunlik grafik, eng ko'p ochilgan taomlar, eng yuqori baholilar |
| `/superadmin/restaurants/<id>` | tizim admini | xuddi shu, ustiga obuna boshqaruvi va hisoblar |

Tanlangan oraliq manzilda qoladi (`?period=…`), shuning uchun sahifani
yangilasa ham yo'qolmaydi va havolasini ulashsa bo'ladi.

Restoran egasi tarifi ruxsat etgan chuqurlikkacha ko'radi (bepulda 7 kun) —
`stats.clamp_range()` uzunroq so'rovni o'zi qisqartiradi. Superadmin uchun bu
cheklov qo'llanmaydi.

## Statistika

Admin bosh sahifasida oxirgi 30 kunlik ochilishlar grafigi va eng ko'p ochilgan
taomlar ro'yxati chiqadi.

Saqlanadigan narsa — faqat `(restoran, taom, sana, son)`. **IP, cookie yoki qurilma
haqida hech narsa yozilmaydi**, shuning uchun bu "necha kishi" emas, "necha marta
ochildi" degan ko'rsatkich. Sanalar UTC bo'yicha.
