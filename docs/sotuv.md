# Sotuvni boshlash — ish hujjati

Bu kod emas, ish hujjati. Suhbatdan keyin o'zgartirib boring.

---

## SHOSHILINCH: ikkala restoraningiz menyusi hozir O'CHIQ

Tekshirdim (2026-08-09):

```
qrdasturxon.tech/r/restoran   → 503   "Lorus — Menyu vaqtincha yopiq"
qrdasturxon.tech/r/restoran2  → 503
```

Sinov muddati (30 kun) tugagan va menyular **avtomatik yopilgan**. Ya'ni bugun
Lorus'ga kirgan mijoz stoldagi QR ni skanerlasa, menyu o'rniga "Menyu vaqtincha
yopiq" yozuvini ko'radi.

Bu qoida ataylab shunday qilingan (`app/plans.py`) va texnik jihatdan to'g'ri
ishlayapti. Lekin natijasi shu: **sizda bor-yo'g'i ikkita restoran bor edi va
ikkalasining ham mahsuloti hozir ishlamayapti.** Ular sizga qo'ng'iroq qilmagan
bo'lsa — bu ular tashlab ketganini bildiradi, kechirganini emas.

Bugun qilinadigan ish, sotuvdan ham oldin:

1. Ikkalasiga **qo'ng'iroq qiling**. Sotish uchun emas: "menyungiz o'chib qoldi,
   kechirasiz, hozir yoqib beraman" deng.
2. Superadmin panelidan muddatni uzaytiring (`/superadmin/restaurants/<id>` →
   Tarif berish). Bu bir daqiqalik ish.
3. So'ng so'rang: **"shu vaqt ichida menyuni ishlatdingizmi?"** Javob sizning
   birinchi va eng halol mijoz ma'lumotingiz bo'ladi.

Agar javob "yo'q, ishlatmadik" bo'lsa — narx ham, landing ham, ilova ham muammo
emas. Muammo mahsulot ularning kunlik ishiga kirmagani. Buni bilish har qanday
sotuv skriptidan qimmatroq.

---

## 0. Avval faktlar: nima allaqachon bor

Tanqidda aytilgan uchta to'siqning ikkitasi **jonli saytda allaqachon hal qilingan**.
Buni tekshirib ko'rdim (2026-08-08, `qrdasturxon.tech`):

| Da'vo | Haqiqat |
|---|---|
| "Narx yo'q" | Narx saytda: **499 000 so'm/yil**, **60 000 so'm/oy**, bepul sinov. Oylik/yillik almashtirgichi bilan |
| "Bo'sh demo" | `/r/bodom` — **11 ta taom, 12 ta rasm**, to'liq menyu. Bo'sh emas |
| "Sayt hech nima aytmaydi" | Sahifada to'rt bo'lim bor: `#qanday` (3 qadam), `#imkoniyatlar`, `#narxlar`, `#aloqa`. "Nima / qancha / qanday boshlash" — uchalasiga javob bor |

**YaTT haqidagi uchinchi nuqta esa to'g'ri va uni men hal qila olmayman.**

Shuning uchun bu hujjat mavjudini qayta qurmaydi. Faqat haqiqatan yetishmayotganini yozadi.

### Tanqidchi bilmagan bitta fakt

**Bu sessiyada qurilgan hamma narsa serverga chiqarilmagan.** Lokalda 62 ta fayl,
1867 qator o'zgarish turibdi. Jonli saytda `/ilova`, `/zal`, `/api/v1` — **hammasi 404**.

Ya'ni: buyurtma tizimi, afitsant ilovasi, stol QR kodlari — sotuvda eng kuchli
argument bo'ladigan narsalar **hozir hech kimga ko'rinmaydi**.

Birinchi suhbatdan oldin qilinadigan bitta ish shu: **deploy**.

---

## 1. Restoran nima uchun to'laydi

Tanqiddagi eng qimmatli savol shu va javobni men bilmayman. Siz ham bilmaysiz.
Buni faqat restoran egasi aytadi.

Lekin bitta narsa aniq: **"QR menyu" o'zi sotilmaydi.** U tovar emas. Sotiladigan
narsa — restoran egasining bugun pul yoki asab yo'qotayotgan joyi.

Uchta gipoteza, tekshirilishi kerak:

**A. Qayta chop etish xarajati.** Narx o'zgarganda menyu qayta chop etiladi.
Yiliga necha marta va har safar qancha turadi — buni **so'rab bilish kerak**.
Agar javob "yiliga 3-4 marta, har safar 300-500 ming" bo'lsa, 499 000/yil o'zini
birinchi yilda qoplaydi va gap tugaydi. Agar "yiliga bir marta, 100 ming" bo'lsa —
bu argument ishlamaydi va boshqasini qidirish kerak.

> Men O'zbekistondagi chop etish narxlarini aniq bilmayman va taxmin qilib
> bermayman. Bu birinchi 10 suhbatda aniqlanadigan raqam.

**B. Zal ilovasi.** Afitsant xatosi, buyurtma kutish vaqti. Bu endi bor (lokalda),
lekin uni sotish uchun restoranda buyurtma jarayonida haqiqatan muammo bo'lishi kerak.

**C. Rasm bilan menyu — o'rtacha chek.** Eng kuchli argument bo'lishi mumkin, chunki
u xarajatni kamaytirmaydi, **tushumni oshiradi**. Lekin isbotlash eng qiyini: buni
faqat "bizda o'rtacha chek 8% o'sdi" degan haqiqiy raqam bilan aytish mumkin, sizda
esa hali bunday raqam yo'q.

**Xulosa:** birinchi 10 suhbat sotuv emas, **so'rov**. Maqsad — qaysi gipoteza
ishlashini bilish.

---

## 2. Narx modeli

Raqam (499 000/yil) o'zi yomon emas. Muammo raqamda emas — **modelda**.

### Tavsiya: to'lovni ikkiga bo'ling

| Nima | Qancha | Nega |
|---|---|---|
| **Ishga tushirish** (bir marta) | 300–500 ming | Menyuni biz kiritamiz: rasmga olamiz, yozamiz, QR chop etamiz, stolga qo'yamiz |
| **Obuna** (yillik) | 499 000 | Hozirgidek |

**Nega ishga tushirish xizmati eng muhim qism:**

Restoran to'lamayotganining sababi narx emas. Sabab — **60 ta taomni kimdir kiritishi
kerak**. Egasi buni qilmaydi: vaqti yo'q, kompyuterda ishlamaydi, rasm yo'q. "Bepul
sinab ko'ring" desangiz, u ro'yxatdan o'tadi, bo'sh menyuni ko'radi va tashlab ketadi.
Sizdagi ikkita restoran ham aynan shu yerda to'xtagan bo'lishi ehtimoli katta —
buni bazadan tekshiring: ularning menyusida nechta taom bor?

Ishga tushirish xizmati bu to'siqni sizning tomoningizga o'tkazadi va **birinchi
pulni bugun keltiradi**. Obuna esa keyingi yil keladi.

### Ikkita qoida

1. **Bepul rejani sotuvda umuman tilga olmang.** U saytda tursin, lekin suhbatda
   "bepul sinab ko'ring" degan gap sotuvni o'ldiradi — odam "keyin qarayman" deydi
   va qaramaydi.
2. **Oylik to'lovni faqat so'rasa ayting.** 60 000×12 = 720 000, yillikdan 31%
   qimmat. Yillikni birinchi aytasiz.

---

## 3. Birinchi 10 suhbat — so'rov skripti

Maqsad: sotish emas, **bilish**. Yozib boring.

Kirish (30 soniya):
> "Assalomu alaykum. Men kafelar uchun menyu tizimi qilaman. Sotmoqchi emasman —
> bir necha savol bermoqchiman, 5 daqiqa. Sizga menyu bilan bugun nima qiyin?"

Keyin **jim turing.** Birinchi javob eng qimmatlisi.

Savollar:
1. Menyuni oxirgi marta qachon o'zgartirgansiz? Nima uchun?
2. O'zgartirganda nima qilasiz — qayta chop etasizmi? Qancha turadi va qancha vaqt ketadi?
3. Yiliga necha marta shunday bo'ladi?
4. Mijoz "bu taom nima?" deb so'raydimi? Kim javob beradi?
5. Menyuda rasm bormi? Bo'lmasa — nega?
6. Buyurtma qabul qilishda muammo bormi?
7. (Agar shikoyat aytsa) Buni hal qilish sizga qancha arziydi?

Oxirida:
> "Rahmat. Men shu muammoni hal qiladigan narsa qilaman. Tayyor bo'lsa ko'rsatsam
> maylimi?"

**10 suhbatdan keyin** qaysi javob takrorlanganini sanang. Eng ko'p takrorlangani —
sizning sotuv argumentingiz. Landing sahifaning birinchi jumlasi ham o'sha bo'ladi.

---

## 4. Sotuv skripti — 3 daqiqa

So'rovdan keyin, gipoteza tasdiqlangach ishlatiladi.
**Telefon qo'lingizda, menyu ochiq turadi.**

**0:00 — Muammoni ularning og'zidan qaytaring**
> "O'tgan safar aytdingiz: narx o'zgarganda menyuni qayta chop etasiz, yiliga
> 3-4 marta, har safar [X] ming. Shundaymi?"

Ular "ha" deydi. Endi siz sotmayapsiz — ularning gapini takrorlayapsiz.

**0:30 — Ko'rsating, aytmang**
Telefonni bering. Stoldagi QR ni skanerlatib, menyuni ochiring.
> "Bu — bizning namuna kafemiz. Mijoz shuni ko'radi."

Keyin panelni ochib, **ularning ko'z oldida bitta narxni o'zgartiring**:
> "Osh 45 mingdan 50 mingga chiqdi."

Telefonni yangilang.
> "Tamom. Chop etish yo'q, kutish yo'q."

**Bu 30 soniya butun sotuvni hal qiladi.** Qolgani gap.

**1:30 — Buyurtma (deploy qilingandan keyin)**
> "Har stolda o'z QR kodi bo'ladi. Mijoz menyudan buyurtma beradi, afitsant
> telefoniga xabar keladi: qaysi stol, nima so'radi. Afitsant ishini olmaydi —
> unga nima kerakligini aytadi."

**2:00 — Narx**
> "Yiliga 499 ming. Bu — bir marta chop etish narxidan arzon.
> Menyuni kiritish ham bizda: kelaman, taomlarni rasmga olaman, hammasini
> yozib chiqaman, QR kodlarni stolga qo'yaman. Bu bir martalik [300-500] ming.
> Ertaga ishlab ketadi."

**2:30 — Yoping. Savol bering, jim turing.**
> "Boshlaymizmi?"

Agar "o'ylab ko'ray" desa:
> "Albatta. Nimani o'ylashingiz kerak — narxnimi yoki ishlashinimi?"

Javob sizga haqiqiy e'tirozni aytadi.

---

## 5. Landing sahifada nima o'zgaradi

Sahifada "nima / qancha / qanday" bor. Yetishmayotgani — **NEGA**.

Hozir birinchi jumla: *"Kafengiz menyusi — mijoz telefonida"*. Bu mahsulot nimaligini
aytadi, lekin **nega pul to'lash kerakligini aytmaydi**.

Ikkita o'zgarish:

1. **Hero ostiga bitta jumla:** qayta chop etish xarajati haqida. Aniq matn birinchi
   10 suhbatdan keyin yoziladi — o'shanda restoran egasining o'z so'zlari bilan.
2. **"Menyuni biz kiritamiz"** — narx bo'limiga alohida karta. Bu eng katta to'siqni
   yopadi va birinchi pulni keltiradi.

Bularni suhbatlardan **keyin** qilish kerak. Hozir yozilgan matn taxmin bo'ladi.

---

## Shu haftada

| # | Ish | Kim |
|---|---|---|
| 1 | YaTT hujjatini boshlash | Siz |
| 2 | **Deploy** — buyurtma tizimi va ilovasiz sotuv suhbati zaif | Men, siz aytsangiz |
| 3 | Bazadan tekshirish: ikkita restoran menyusida nechta taom bor | Men |
| 4 | 10 ta kafega kirish, so'rov savollarini berish | Siz |
| 5 | Javoblarni shu faylga yozish | Siz |
| 6 | Eng ko'p takrorlangan javob bo'yicha hero matni va narx modelini yakunlash | Birga |

Kod yozish bu ro'yxatda yo'q. Ataylab.
