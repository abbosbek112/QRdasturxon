# Ilovani telefonga o'rnatish

Ikki yo'l bor. Birinchisi bugun, hisobsiz, 10 daqiqada — lekin bildirishnomasiz.
Ikkinchisi haqiqiy ilova, bildirishnoma bilan — Expo hisobi kerak.

---

## Yo'l 1 — bugun sinab ko'rish (Expo Go)

Hech qanday hisob, build va kutish yo'q. Ilovaning hamma qismi ishlaydi:
kirish, buyurtmalar taxtasi, "Qabul qildim / Berildi / Bekor qilish", bo'lim filtri.

> **Bildirishnoma bu yo'lda ISHLAMAYDI.** Expo Go'dan uzoq push olib tashlangan —
> bu Expo cheklovi, kodning kamchiligi emas. Bildirishnoma uchun 2-yo'l kerak.

### 1. Telefonga Expo Go

Play Store yoki App Store'dan **"Expo Go"** ni o'rnating.

### 2. Serverni telefon ko'radigan qilib ishga tushiring

Odatdagi server faqat kompyuterning o'zidan ko'rinadi (`127.0.0.1`). Telefon
uchun u tarmoqqa ochilishi kerak:

```bash
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Ilovani ishga tushiring

Boshqa terminalda. **Telefon va kompyuter bitta Wi-Fi'da bo'lsin.**

```bash
cd mobile && EXPO_PUBLIC_API_URL=http://10.221.43.253:8000 npx expo start
```

`10.221.43.253` — shu kompyuterning hozirgi tarmoq manzili. Wi-Fi o'zgarsa u ham
o'zgaradi, o'shanda quyidagi bilan yangisini oling:

```bash
ip -4 addr show scope global | grep -oP 'inet \K[\d.]+' | head -1
```

### 4. QR kodni skanerlang

Terminalda QR chiqadi. **Android:** Expo Go ichidagi "Scan QR code".
**iPhone:** oddiy Kamera ilovasi bilan.

Ilova telefonda ochiladi. Kirish uchun afitsant logini va paroli.

---

## Yo'l 2 — haqiqiy ilova (APK va TestFlight)

Bu yerda bildirishnoma ishlaydi va ilova telefonda o'z ikonkasi bilan turadi.

### Bir martalik sozlash

Asbob nomi **`eas-cli`**, buyruq nomi esa `eas`. `npx eas` deb yozsangiz npm
`eas` nomli paketni qidiradi va topolmaydi:

```
npm error could not determine executable to run
```

Ikki yo'l bor. Bir marta ishlatadigan bo'lsangiz:

```bash
cd mobile
npx eas-cli login          # expo.dev da bepul hisob
npx eas-cli init           # app.json ga projectId yozadi
```

Tez-tez ishlatadigan bo'lsangiz o'rnatib qo'yganingiz qulayroq — keyin
`npx` shart emas va har safar yuklab o'tirmaydi:

```bash
npm install -g eas-cli
eas login
eas init
```

`projectId` muhim: push tokeni aynan shu raqamga bog'lanadi.

**Android bildirishnomasi uchun Firebase kerak** (bepul):

1. `console.firebase.google.com` da loyiha yarating
2. Android ilova qo'shing, paket nomi: `tech.qrdasturxon.zal`
3. `google-services.json` ni yuklab olib `mobile/` ga qo'ying
4. `app.json` ga qo'shing: `"android": { "googleServicesFile": "./google-services.json", ... }`
5. Firebase → Project settings → Service accounts → yangi kalit yarating va uni
   `expo.dev` dagi loyiha → Credentials → FCM V1 ga yuklang

Busiz ilova ishlaydi, lekin **push kelmaydi**.

### Android APK

```bash
npx eas-cli build --platform android --profile preview
```

Bulutda yig'iladi (~10–20 daqiqa), oxirida yuklab olish havolasi beriladi.
APK'ni telefonga o'tkazing va oching — telefon "noma'lum manbadan o'rnatish"
so'raydi, ruxsat bering.

Saytdan tarqatish uchun APK'ni serverga qo'ying:

```bash
scp qrdasturxon-zal.apk server:/opt/qrdasturxon/app/static/app/
```

Shundan keyin u `qrdasturxon.tech/ilova` sahifasida paydo bo'ladi.

### iPhone (TestFlight)

```bash
npx eas-cli build --platform ios --profile production
npx eas-cli submit --platform ios --latest
```

TestFlight havolasini olgach serverdagi `.env` ga yozing:

```
TESTFLIGHT_URL=https://testflight.apple.com/join/...
```

Eslatma: TestFlight build'i **90 kunda eskiradi** — har chorakda yangisi kerak.

---

## Kichik tuzatishlar — qayta o'rnatishsiz

Matn, rang yoki mantiq o'zgarsa yangi APK shart emas:

```bash
cd mobile && npx eas-cli update --channel preview --message "nima o'zgardi"
```

Ilova keyingi ochilishida o'zi olib qo'yadi. Faqat native o'zgarish (yangi
kutubxona, ikonka, ruxsat) yangi build talab qiladi.

---

## Nimadir ishlamasa

| Belgi | Sabab |
|---|---|
| Ilova "Aloqa yo'q" deydi | Server `--host 0.0.0.0` bilan ishga tushmagan, yoki IP eskirgan |
| QR skanerlanmaydi | Telefon va kompyuter boshqa Wi-Fi'da |
| Kirish o'tmaydi | Afitsant hisobi `/admin/staff` da yaratilganmi; parolni o'sha yerdan yangilang |
| Bildirishnoma kelmaydi | Expo Go'da umuman ishlamaydi. Haqiqiy build'da — Firebase sozlanmagan |
| `eas build`: `GraphQL request failed` / `ETIMEDOUT` | Node'ning Happy Eyeballs oynasi qisqa — pastga qarang |
| Buyurtma ko'rinmaydi | Afitsant boshqa bo'limga biriktirilgan. Taxtada "Hammasi" ni bosing |


---

## `eas build` tarmoq xatosi bilan yiqilsa

Belgi: buyruq ~0.5 soniyada quyidagini beradi.

```
request to https://api.expo.dev/graphql failed, reason:
    Error: GraphQL request failed.
```

Sabab **internet yomonligi emas.** Node 20+ da Happy Eyeballs yoqilgan: u har bir
IP manzilga **250 ms** beradi va ulgurmasa keyingisiga o'tadi. O'zbekistondan
Cloudflare'gacha ulanish ~380 ms turadi, ya'ni har bir urinish oynadan chiqib
ketadi. Ikkita IPv4 manzil × 250 ms = ~510 ms, keyin `ETIMEDOUT` — xatolar aynan
shu vaqtda kelgani shundan.

`eas whoami` ko'pincha o'tadi, chunki u bitta so'rov yuboradi. `eas build` esa
ketma-ket o'nlab so'rov qiladi va bittasi deyarli har safar yiqiladi.

Oynani uzaytiring:

```bash
NODE_OPTIONS=--network-family-autoselection-attempt-timeout=3000 eas build --platform android --profile preview
```

12 martadan o'lchandi: standart sozlama bilan 10/12, uzaytirilgani bilan 12/12.

Doimiy qilish:

```bash
echo 'export NODE_OPTIONS=--network-family-autoselection-attempt-timeout=3000' >> ~/.bashrc
```

Qo'shimcha: bu mashinada IPv6 marshruti umuman yo'q (`ip -6 route show default`
bo'sh), lekin DNS IPv6 manzil qaytaradi. Bu ham urinishlarni behuda sarflaydi.
