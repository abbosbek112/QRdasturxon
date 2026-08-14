# QRdasturxon — qo'lda tekshirish ro'yxati (test case)

Bu hujjat **odam bajaradigan** tekshiruvlar uchun. Kodning avtomatik testlari
alohida (`tests/`, 365 ta) va ular har o'zgarishda ishlaydi — bu yerda esa
avtomat ko'ra olmaydigan narsalar: ko'rinish, telefon, ovoz, tebranish,
haqiqiy QR, chop etilgan varaq va foydalanuvchi tushunadimi-yo'qmi.

## Qanday ishlatiladi

Har satrni bajarib, **Natija** ustuniga belgi qo'ying:

| Belgi | Ma'nosi |
|---|---|
| ✅ | Kutilganidek |
| ❌ | Xato — pastdagi "Topilgan xatolar" ga yozing |
| ⏭ | O'tkazib yuborildi (sababini yozing) |

**Muhim qoida:** ❌ qo'yganda faqat "ishlamadi" deb yozmang. Uch narsani
yozing: *nima qildim → nima kutgandim → nima bo'ldi*. Skrinshot bo'lsa yanada
yaxshi. Busiz xatoni takrorlash qiyin bo'ladi.

## Tayyorgarlik

| Kerak | Izoh |
|---|---|
| Kompyuter | Chrome yoki Firefox |
| Telefon | Android — ilova uchun. iPhone bo'lsa faqat brauzer qismi |
| Ikkinchi qurilma | Mijoz rolini o'ynash uchun (planshet yoki ikkinchi telefon) |
| Sinov restorani | Haqiqiy mijoz restoranida SINAMANG |

Hisoblar tekshiruvchiga alohida beriladi: egasi, afitsant va superadmin.

---

## 1. Kirish va ro'yxatdan o'tish

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 1.1 | Bosh sahifadan "Ro'yxatdan o'tish" ni bosing | Forma ochiladi, "Kirish" bilan chalkashmaydi | |
| 1.2 | Band login yozib yuboring | Xato **aynan login maydoni ostida** chiqadi, sahifa tepasida emas | |
| 1.3 | Brauzer login maydonini o'zi to'ldirsa | Ogohlantirish ko'rinadi — nima yozilganini tekshirish kerakligi aytiladi | |
| 1.4 | Qisqa parol (5 belgi) kiriting | Tushunarli xato, "xato" degan quruq so'z emas | |
| 1.5 | To'g'ri login-parol bilan kiring | Egasi panelga tushadi | |
| 1.6 | Noto'g'ri parolni **5 marta** kiriting | Bloklanadi va qachon ochilishi aytiladi | |
| 1.7 | Chiqib, orqaga qayting | Panelga qaytolmaysiz — sessiya tugagan | |

## 2. Egasi paneli — menyu

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 2.1 | **Kategoriyalar** → yangi qo'shing | Ro'yxatda chiqadi | |
| 2.2 | **Taomlar** → yangi taom, rasm bilan | Saqlanadi, rasm ko'rinadi | |
| 2.3 | Juda katta rasm (5 MB dan ortiq) yuklang | Tushunarli xato yoki avtomat kichraytiradi — "500" chiqmaydi | |
| 2.4 | Rasm o'rniga PDF yuklang | Rad etiladi, sabab aytiladi | |
| 2.5 | Narxga harf yozing | Rad etiladi | |
| 2.6 | Taomga **O'tkir** va **Vegetarian** belgilarini qo'ying | Mijoz menyusida ikkalasi ham ko'rinadi | |
| 2.7 | Menyuda "Halol" belgisi bormi? | **Bo'lmasligi kerak** — olib tashlangan | |
| 2.8 | Taomni yashiring | Mijoz menyusida yo'qoladi, panelda qoladi | |
| 2.9 | Taomni o'chiring | **Tasdiq so'raydi**, "Yo'q" desangiz o'chmaydi | |
| 2.10 | Kategoriyani o'chiring | Ichidagi taomlar bilan nima bo'lishi ogohlantiriladi | |

## 3. Zal: qavat, bo'lim, stol

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 3.1 | **Sozlamalar** → "Menyudan buyurtma qabul qilish" ni yoqing | Chap menyuda **Buyurtmalar, Zal, Xodimlar** paydo bo'ladi | |
| 3.2 | **Zal** → bo'sh restoranda "Zalni yig'ish" formasi | 2 qavat, 10 stol deb yig'sangiz — bino chiziladi | |
| 3.3 | Qavat tartibini ko'ring | Yuqori qavat **tepada**, yerto'la **pastda** | |
| 3.4 | **Qavat qo'shish** → raqam 3 | 3-qavat qo'shiladi | |
| 3.5 | **Qavat qo'shish** → raqam 2 + **Yerto'la** belgisi | "2-yerto'la" deb chiqadi, eng pastda turadi | |
| 3.6 | Yerto'ladagi qavatga **Bo'lim qo'shish** | Yangi bo'lim **yerto'lada** qoladi, 1-qavatga sakramaydi | |
| 3.7 | Bo'limga **Stol qo'shish** (4 ta) | Raqamlash mavjudlardan keyin davom etadi, takrorlanmaydi | |
| 3.8 | 3 ta stolni belgilab, boshqa bo'limda **"Shu yerga ko'chirish"** | Uchalasi ko'chadi, belgilanmagani joyida qoladi | |
| 3.9 | Kompyuterda stolni **sudrab** boshqa bo'limga tashlang | Bo'lim yoritiladi, stol o'sha yerga o'tadi | |
| 3.10 | Stol ustidagi katakchani bosing | Faqat belgilanadi — **tahrir oynasi ochilmaydi** | |
| 3.11 | Stol nomini bosing | Tahrir oynasi ochiladi (nom, turi, QR, o'chirish) | |
| 3.12 | Stol turini **VIP xona** qiling | Mijoz "VIP 3" deb ko'radi, "3-stol" emas | |
| 3.13 | Bo'limni o'chiring | **Stollar qolishi kerak** — faqat bo'limsiz bo'ladi | |
| 3.14 | "Bo'limsiz stollar" javoniga qarang | O'chirilgan bo'lim stollari shu yerda | |
| 3.15 | Telefonda (tor ekran) Zal sahifasini oching | Chetga chiqib ketmaydi, stol oynasi qirqilmaydi | |

## 4. QR kod va chop etish

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 4.1 | **Chop etish uchun varaq** ni oching | Har stol uchun kartochka: raqam, qavat, bo'lim, QR | |
| 4.2 | Varaqni **haqiqiy printerda** chop eting | QR sifatli, qirqilmagan, o'qiladi | |
| 4.3 | Chop etilgan QR'ni telefon kamerasi bilan skanerlang | Menyu ochiladi | |
| 4.4 | Manzil qatoriga qarang | Stol kodi **ko'rinmaydi** (sessiyaga yozilgan) | |
| 4.5 | Menyu manzilini nusxalab boshqa telefonga yuboring | U yerdan buyurtma berib **bo'lmaydi** | |
| 4.6 | Stolda "Kodni yangilash" ni bosing | Ogohlantiradi; keyin eski QR ishlamaydi | |
| 4.7 | Menyuni o'zgartiring (yangi taom qo'shing) | **QR qayta chop etilmaydi** — eski kod ishlayveradi | |

## 5. Mijoz: menyu va buyurtma

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 5.1 | QR orqali menyuni oching | Restoran nomi, kategoriyalar, narxlar ko'rinadi | |
| 5.2 | Tilni **RU** ga o'zgartiring | Interfeys va tarjima qilingan matnlar ruschada | |
| 5.3 | Tilni 3 marta almashtiring, keyin **Statistika** ga qarang | **1 ta ochilish** sanaladi, 3 ta emas | |
| 5.4 | Taom kartasiga qarang (telefonda) | Narx va vaqt bir-birining ustiga chiqmaydi | |
| 5.5 | Savatga 2 xil taom qo'shing | Soni va jami to'g'ri hisoblanadi | |
| 5.6 | Buyurtma bering | "Buyurtmangiz yuborildi" sahifasi, uchta bosqich ko'rinadi | |
| 5.7 | Buyurtma sahifasini telefonda ko'ring | Narx va tugmalar chetdan chiqmaydi, matn qirqilmaydi | |
| 5.8 | Sahifani ochiq qoldiring, afitsant "Qabul qildim" bossin | 15 soniyada holat o'zi yangilanadi | |
| 5.9 | Bitta stoldan **6 marta** ketma-ket buyurtma bering | Cheklov ishlaydi, tushunarli xabar | |
| 5.10 | QR skanerlab **31 daqiqa** kuting, keyin buyurtma bering | Oyna yopilgan — buyurtma qabul qilinmaydi | |
| 5.11 | Buyurtma **o'chirilgan** restoranda menyuni oching | Buyurtma tugmasi umuman yo'q | |

## 6. Afitsant taxtasi (`/zal`)

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 6.1 | **Xodimlar** → afitsant yarating | Parol yozayotganda **ko'rish tugmasi** ishlaydi | |
| 6.2 | Afitsant bilan kiring | To'g'ridan-to'g'ri `/zal` ga tushadi | |
| 6.3 | Afitsant menyuni tahrirlashga urinsin (`/admin` ga kirsin) | Ruxsat berilmaydi | |
| 6.4 | Mijoz buyurtma bersin | **8 soniyada** taxtada karta chiqadi | |
| 6.5 | Kartadagi vaqtga qarang | **Mahalliy vaqt** (soatingiz bilan bir xil) | |
| 6.6 | **"Qabul qildim"** → **"Berildi"** | Karta taxtadan tushadi | |
| 6.7 | Afitsantni bir bo'limga biriktiring | Faqat o'z bo'limi stollarini ko'radi | |
| 6.8 | Boshqa bo'limdan buyurtma kelsin | Ko'rinmaydi; **"Hammasi"** bosilsa ko'rinadi | |
| 6.9 | Hech kimga biriktirilmagan stoldan buyurtma | **Hamma** ko'radi — javobsiz qolmaydi | |
| 6.10 | Afitsantni bloklang | U darrov chiqib ketadi, kira olmaydi | |
| 6.11 | Egasi `/zal` ga kirsin | Butun zalni ko'radi | |

## 7. Bildirishnoma — eng muhim qism

Afitsant buyurtmani **sezishi** kerak. Bu bo'limni **shovqinli joyda** sinang.

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 7.1 | Ilovada **Sozlamalar → bildirishnomani yoqing** | Ruxsat so'raydi, yoqiladi | |
| 7.2 | Telefonni **qulflang**, buyurtma bering | Ekran yonadi, ovoz va uzun tebranish | |
| 7.3 | Ovozni tinglang | Ikki tonli chaqiruv — telefonning oddiy "diq"i emas | |
| 7.4 | Tebranishni sezing | Uzun, uch marta takrorlanadi | |
| 7.5 | **Ilova ochiq turganda** buyurtma bering | Ovoz va tebranish **baribir** bo'ladi | |
| 7.6 | Buyurtmaga javob bermay **45 soniya** kuting | Ikkinchi marta chaqiradi | |
| 7.7 | Yana kuting (2 daqiqa) | Uchinchi marta chaqiradi | |
| 7.8 | "Qabul qildim" bosing, keyin kuting | **Boshqa chaqirmaydi** | |
| 7.9 | Telefon jim rejimda bo'lsa | Tebranish baribir sezilади | |
| 7.10 | Bildirishnomani bosing | Ilova ochilib, taxta ko'rinadi | |
| 7.11 | Brauzerda `/zal` ochiq holda buyurtma | Ovoz chalinadi, sahifa sarlavhasida son ko'rinadi | |

## 8. Ilova (Android)

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 8.1 | `qrdasturxon.tech/ilova` dan yuklab oling | Versiya va hajm ko'rinadi, fayl tushadi | |
| 8.2 | O'rnatishda "App blocked" chiqsa | Sahifadagi izoh yordam beradi (More details → Install anyway) | |
| 8.3 | Eski ilova ustiga o'rnating | Ma'lumot yo'qolmaydi, qayta kirish talab qilinmaydi | |
| 8.4 | Afitsant bilan kiring | Taxta ochiladi | |
| 8.5 | Internetni o'chiring | Tushunarli xabar, ilova qulab tushmaydi | |
| 8.6 | Internetni qayting | O'zi tiklanadi | |
| 8.7 | Ro'yxatni pastga torting | Yangilanadi | |
| 8.8 | Ilovani yopib qayta oching | Qayta kirish so'ralmaydi | |
| 8.9 | **Sozlamalar** → versiyaga qarang | Saytdagi versiya bilan bir xil | |
| 8.10 | Chiqing va qayta kiring | Ishlaydi | |

## 9. Statistika va izohlar

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 9.1 | Menyuni 1 marta oching | Statistikada **1** ta ochilish | |
| 9.2 | Xuddi shu telefondan 5 daqiqa ichida qayta oching | Son **oshmaydi** — bir mijoz bir marta | |
| 9.3 | Ikki xil telefondan bir vaqtda oching | **2** ta sanaladi, yo'qolmaydi | |
| 9.4 | Muddatni "Hafta"/"Oy" ga o'zgartiring | Grafik va ro'yxat mos o'zgaradi | |
| 9.5 | Mijoz izoh qoldirsin | **Darrov ko'rinmaydi** — tasdiq kutadi | |
| 9.6 | Izohni tasdiqlang | Menyuda paydo bo'ladi | |
| 9.7 | **Buyurtmalar** tarixini oching | Stol, vaqt, summa to'g'ri | |

## 10. Tarif va muddat

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 10.1 | Bepul tarifda cheklovdan ortiq taom qo'shing | Tushunarli xabar, tarif ko'tarish taklif qilinadi | |
| 10.2 | Sinov muddati tugagan restoran menyusini oching | Mijoz **tinch sahifa** ko'radi, xato emas | |
| 10.3 | Muddati tugagan restoran egasi kirsin | Panelga kiradi, ogohlantirish tasmasi turadi | |
| 10.4 | Superadmin muddatni uzaytirsin | Menyu darrov ochiladi | |
| 10.5 | Superadmin slug'ni o'zgartirsin | **Chop etilgan QR o'lishi** haqida ogohlantiradi | |

## 11. Xavfsizlik — bularsiz ishonib bo'lmaydi

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 11.1 | Kirmasdan `/admin` ni oching | Kirish sahifasiga yuboriladi | |
| 11.2 | Kirmasdan `/zal` ni oching | Kirish sahifasiga yuboriladi | |
| 11.3 | **Boshqa restoran** egasi bilan kirib, sizning taomingiz manzilini oching | Topilmadi — begona ma'lumot ko'rinmaydi | |
| 11.4 | Boshqa restoran egasi sizning stolingizni ko'chirishga urinsin | Bajarilmaydi | |
| 11.5 | Afitsant boshqa restoran buyurtmasiga tegishga urinsin | Bajarilmaydi | |
| 11.6 | Ilovaga kalitsiz murojaat (`/api/v1/orders`) | Rad etiladi | |
| 11.7 | Afitsantni bloklab, uning ilovasidan so'rov yuboring | Kalit darrov kuchini yo'qotadi | |

## 12. Ko'rinish va til

| № | Nima qilinadi | Kutilgan natija | Natija |
|---|---|---|---|
| 12.1 | Har sahifani **telefon** kengligida oching | Gorizontal siljish yo'q, matn qirqilmaydi | |
| 12.2 | Uch tilni ham aylanib chiqing | Tarjimasiz joy yo'q, kalit nomi ko'rinmaydi (`dl_title` kabi) | |
| 12.3 | Uzun restoran nomi va uzun taom nomi qo'ying | Dizayn buzilmaydi | |
| 12.4 | Rasmsiz taom | Bo'sh joy emas, o'rnini bosuvchi ko'rinish | |
| 12.5 | Menyusi bo'sh restoran | Tushunarli "hali taom yo'q" xabari | |

---

## Ilgari topilgan xatolar — qaytmaganini tekshiring

Bular haqiqiy foydalanuvchi sinovida chiqqan va tuzatilgan. Har yangilanishdan
keyin shu beshtasini qayta ko'ring — eng ko'p qaytadigan joylar shular.

| № | Tekshiruv | Natija |
|---|---|---|
| R1 | Telefonda taom kartasida narx va vaqt bir-birining ustiga chiqmaydi | |
| R2 | O'chirish tugmalari **tasdiq so'raydi** (ilgari jimgina o'chirardi) | |
| R3 | Afitsant kartasida **mahalliy vaqt**, UTC emas | |
| R4 | Til almashtirish statistikani oshirmaydi | |
| R5 | Buyurtma sahifasi telefonda chetdan chiqmaydi | |

---

## Topilgan xatolar

Har xatoni shu ko'rinishda yozing:

```
№      : 3.6
Nima qildim  : Yerto'la qavatiga "Omborxona" bo'limini qo'shdim
Nima kutgandim: Bo'lim yerto'lada qolishi
Nima bo'ldi  : 1-qavatga tushib qoldi
Qurilma      : Samsung A52, Chrome
Skrinshot    : bor / yo'q
```

Takrorlanadigan xato tuzatilishi ham oson. "Ishlamadi" degan yozuvdan
foydalanish qiyin.
