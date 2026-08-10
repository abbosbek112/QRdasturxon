# QRdasturxon Zal — afitsant ilovasi

Stollardan kelgan buyurtmalar taxtasi. Server bilan `/api/v1` orqali gaplashadi
(`app/routers/api.py`), ya'ni brauzerdagi `/zal` bilan bir xil ma'lumotni ko'radi.

Ikkalasi ham **do'kon ro'yxatisiz** tarqatiladi: Android — saytdan APK,
iPhone — TestFlight.

## Birinchi marta ishga tushirish

```bash
cd mobile
npm install
```

Telefonda sinash (kompyuter va telefon bitta Wi-Fi'da bo'lsin). `localhost`
telefonning o'zini bildiradi, shuning uchun kompyuterning tarmoqdagi IP manzili
yoziladi:

```bash
EXPO_PUBLIC_API_URL=http://192.168.1.5:8000 npx expo start
```

Expo Go ilovasini o'rnatib, chiqqan QR kodni skanerlang.

> **Bildirishnoma Expo Go'da ishlamaydi.** Uni sinash uchun haqiqiy build kerak
> (pastga qarang) — bu Expo cheklovi, kodning kamchiligi emas.

## Nima sozlanishi kerak (bir marta)

1. **Expo hisobi** — bepul, [expo.dev](https://expo.dev). Keyin `npx eas-cli login`.

   > Asbob nomi `eas-cli`, buyrug'i esa `eas`. `npx eas` ishlamaydi —
   > npm `eas` nomli paketni qidiradi va topolmaydi. Doimiy ishlatsangiz:
   > `npm install -g eas-cli`, shundan keyin oddiy `eas login` yetadi.
2. **Loyihani bog'lash** — `npx eas-cli init`. U `app.json` ga `extra.eas.projectId`
   yozadi; push tokeni aynan shu raqamga bog'lanadi.
3. **Firebase loyihasi** — bepul, Android push uchun. `google-services.json`
   faylini shu papkaga qo'yib, `app.json` da
   `android.googleServicesFile` ni ko'rsating.
4. **Imzo kaliti** — `eas build` birinchi safar o'zi yasab, o'zida saqlaydi.
   **Kalit yo'qolsa o'sha ilovani boshqa hech qachon yangilab bo'lmaydi** —
   `npx eas-cli credentials` bilan zaxirasini olib, parol menejerida saqlang.

## Build profillari (`eas.json`)

JSON'da izoh yo'q va EAS notanish kalitni rad etadi (`"//"` ham) — shuning
uchun profillar nima uchun shundayligi shu yerda yozilgan:

| Profil | Nima uchun |
|---|---|
| `preview` | Saytdan tarqatiladigan Android fayli. `buildType: apk` — **AAB emas**: AAB faqat Google Play uchun va uni telefonga to'g'ridan-to'g'ri o'rnatib bo'lmaydi. `distribution: internal` — do'konsiz tarqatish |
| `production` | iOS uchun TestFlight'ga yuboriladigan build. Android tomoni `preview` bilan bir xil APK bo'lib qoladi — Play Store'ga chiqilmaydi |

## Android — saytdan tarqatish

```bash
npx eas-cli build --platform android --profile preview
```

Tayyor bo'lgach APK yuklab olinadi va serverga qo'yiladi:

```bash
scp qrdasturxon-zal.apk server:/opt/qrdasturxon/app/static/app/
```

Shundan keyin u `https://qrdasturxon.tech/ilova` sahifasida paydo bo'ladi.
Versiyani `app/config.py` dagi `app_version` bilan birga ko'taring — ilova
yangilanish borligini `GET /api/v1/app/latest` orqali shundan biladi.

## iPhone — TestFlight

```bash
npx eas-cli build --platform ios --profile production
npx eas-cli submit --platform ios --latest
```

Ikkita eslatma: TestFlight build'i **90 kunda eskiradi** (har chorakda yangisi
kerak), va har yangi versiyaning birinchi build'i Apple'ning qisqa tekshiruvidan
o'tadi.

TestFlight havolasini olgach uni serverdagi `.env` ga qo'ying:

```
TESTFLIGHT_URL=https://testflight.apple.com/join/...
```

## Kichik tuzatishlar — qayta o'rnatishsiz

JS o'zgarsa (matn, rang, mantiq) yangi APK shart emas:

```bash
npx eas-cli update --channel preview --message "nima o'zgardi"
```

Ilova keyingi ochilishida o'zi olib qo'yadi. Faqat native o'zgarish (yangi
kutubxona, ikonka, ruxsat) yangi build talab qiladi.

## Fayllar

| Fayl | Vazifasi |
|---|---|
| `App.js` | Ildiz: kalit bor-yo'qligiga qarab kirish yoki taxta |
| `src/api.js` | Server bilan aloqa, `Authorization: Bearer` |
| `src/session.js` | Kalit `expo-secure-store` da (AsyncStorage emas — u oddiy fayl) |
| `src/push.js` | Bildirishnoma: ruxsat, token, qurilmani yozish |
| `src/BoardScreen.js` | Taxta: 8 soniyada yangilanadi, tortib yangilash |
| `src/OrderCard.js` | Bitta buyurtma va uchta katta tugma |
| `src/i18n.js` | Matnlar. Kalit nomlari `app/i18n.py` bilan bir xil |

Navigatsiya kutubxonasi ataylab yo'q: ekran uchta va ular oddiy holat bilan
almashadi.
