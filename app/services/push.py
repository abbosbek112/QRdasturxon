"""Afitsantga bildirishnoma — Web Push.

Yangi buyurtma kelganda afitsantning telefoni cho'ntakda va ekrani o'chiq
bo'lishi mumkin. O'shanda taxtaning tortishi (`hall.js`) hech nima qilmaydi:
sahifa yopiq. Push esa brauzerning fon jarayoni orqali keladi va ilova
umuman ochiq bo'lmasa ham ishlaydi.

**Xabar MAZMUNSIZ yuboriladi.** Push serveriga bo'sh "turtki" ketadi, service
worker esa uni olib `/zal/ping` dan joriy holatni o'zi so'raydi. Ikki foydasi
bor:

* mazmun shifrlash (`aes128gcm`) umuman kerak bo'lmaydi — faqat VAPID imzosi
  qoladi, ya'ni yagona bog'liqlik `cryptography`;
* buyurtma matni Google/Mozilla push serverlaridan **o'tmaydi**.

Kalitlar sozlanmagan bo'lsa modul jimgina hech narsa qilmaydi. Bu ataylab:
kalit unutilgani sababli mijozning buyurtmasi qabul qilinmay qolishi mumkin emas.
"""

import base64
import json
import logging
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils as asym_utils
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AppDevice, PushSubscription, Role, User

log = logging.getLogger(__name__)

# Push serveri xabarni shuncha soniya saqlaydi. Buyurtma tez eskiradi —
# yarim soatdan keyin yetib kelgan "yangi buyurtma" faqat chalg'itadi.
TTL_SECONDS = 600
# Imzo muddati. RFC 8292 24 soatdan oshirmaslikni aytadi.
JWT_LIFETIME = 12 * 3600
REQUEST_TIMEOUT = 10

# Expo push xizmati — native ilova uchun. Kalit talab qilmaydi: Expo o'zi
# FCM va APNs'ga uzatadi, ya'ni har platforma uchun alohida sozlash yo'q.
EXPO_ENDPOINT = "https://exp.host/--/api/v2/push/send"
EXPO_TITLE = "Yangi buyurtma"
EXPO_BODY = "Stoldan buyurtma keldi"


def public_key() -> str:
    """Brauzerga beriladigan ochiq kalit (`applicationServerKey`)."""
    return settings.vapid_public_key


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _private_key() -> ec.EllipticCurvePrivateKey:
    padding = "=" * (-len(settings.vapid_private_key) % 4)
    secret = base64.urlsafe_b64decode(settings.vapid_private_key + padding)
    return ec.derive_private_key(int.from_bytes(secret, "big"), ec.SECP256R1())


def _authorization(endpoint: str) -> str:
    """VAPID sarlavhasi: ES256 bilan imzolangan JWT.

    `aud` — push serverining ILDIZI (masalan https://fcm.googleapis.com).
    To'liq manzil qo'yilsa server imzoni rad etadi.
    """
    origin = urlparse(endpoint)
    claims = {
        "aud": f"{origin.scheme}://{origin.netloc}",
        "exp": int(time.time()) + JWT_LIFETIME,
        "sub": settings.vapid_subject,
    }
    header = _b64(b'{"typ":"JWT","alg":"ES256"}')
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode()

    der = _private_key().sign(signing_input, ec.ECDSA(hashes.SHA256()))
    # `cryptography` DER qaytaradi, JWT esa xom r||s (64 bayt) kutadi
    r, s = asym_utils.decode_dss_signature(der)
    signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")

    token = f"{header}.{body}.{_b64(signature)}"
    return f"vapid t={token}, k={settings.vapid_public_key}"


def _deliver(endpoint: str) -> int:
    """Bo'sh turtki yuboradi va HTTP holatini qaytaradi."""
    request = urllib.request.Request(
        endpoint,
        data=b"",
        method="POST",
        headers={
            "Authorization": _authorization(endpoint),
            "TTL": str(TTL_SECONDS),
            "Content-Length": "0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def _waiter_ids(db: Session, restaurant_id: int, table_id: int | None = None) -> list[int]:
    """Kimga bildirishnoma ketishi kerak.

    `table_id` berilsa faqat SHU stolga javobgar xodimlar tanlanadi —
    11-stolning buyurtmasi 1–10 ga javobgar afitsantni bezovta qilmasin.
    Kimga tegishliligini `services/areas.py` hisoblaydi.
    """
    from app.services import areas

    return areas.responsible_for(db, restaurant_id, table_id)


def _notify_browsers(db: Session, people: list[int]) -> None:
    """PWA obunalari — Web Push (VAPID)."""
    if not settings.push_enabled:
        return

    rows = db.scalars(
        select(PushSubscription).where(PushSubscription.user_id.in_(people))
    ).all()

    dead = []
    for row in rows:
        try:
            status = _deliver(row.endpoint)
        except Exception:
            log.warning("Bildirishnoma yuborilmadi", exc_info=True)
            continue
        # 404/410 — obuna o'lgan: afitsant ilovani o'chirgan yoki brauzer
        # ma'lumotini tozalagan. Jadval axlat bilan to'lmasligi uchun o'chiramiz.
        if status in (404, 410):
            dead.append(row.endpoint)

    if dead:
        db.execute(delete(PushSubscription).where(PushSubscription.endpoint.in_(dead)))
        db.commit()


def _expo_send(expo_tokens: list[str]) -> list:
    """Expo push xizmatiga yuboradi va har token uchun javobni qaytaradi.

    Mazmun bu yerda BOR — Web Push'dan farqi shu. Expo tanani o'zi shifrlab
    uzatadi, service worker esa kerak emas: ilova yopiq bo'lganda u
    qo'shimcha so'rov qila olmasdi ham.
    """
    messages = [
        {
            "to": token,
            "title": EXPO_TITLE,
            "body": EXPO_BODY,
            "sound": "default",
            "priority": "high",
            "channelId": "orders",
        }
        for token in expo_tokens
    ]
    request = urllib.request.Request(
        EXPO_ENDPOINT,
        data=json.dumps(messages).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        payload = json.loads(response.read().decode())
    data = payload.get("data")
    return data if isinstance(data, list) else []


def _notify_apps(db: Session, people: list[int]) -> None:
    """Native ilova qurilmalari — Expo Push.

    Web Push'dan farqli, bu yerda VAPID kaliti kerak emas: Expo o'z xizmati
    orqali FCM va APNs'ga uzatadi. Shuning uchun ilova kalitlar sozlanmagan
    serverda ham bildirishnoma oladi.
    """
    rows = db.scalars(select(AppDevice).where(AppDevice.user_id.in_(people))).all()
    if not rows:
        return

    try:
        replies = _expo_send([row.expo_token for row in rows])
    except Exception:
        log.warning("Expo bildirishnomasi yuborilmadi", exc_info=True)
        return

    # Javob yuborilgan tartibda keladi. "DeviceNotRegistered" — ilova
    # o'chirilgan yoki token eskirgan.
    dead = [
        row.expo_token
        for row, reply in zip(rows, replies)
        if isinstance(reply, dict)
        and (reply.get("details") or {}).get("error") == "DeviceNotRegistered"
    ]
    if dead:
        db.execute(delete(AppDevice).where(AppDevice.expo_token.in_(dead)))
        db.commit()


def notify_restaurant(restaurant_id: int, table_id: int | None = None) -> None:
    """Restoranning barcha zal qurilmalariga turtki yuboradi.

    Ikki yo'l: brauzer obunalari (PWA) va native ilova qurilmalari. Bir
    afitsantda ikkalasi ham bo'lishi mumkin va u ikkita bildirishnoma oladi —
    bu yomon emas, buyurtmani o'tkazib yuborgandan yaxshiroq.

    Fon vazifasida chaqiriladi va O'Z sessiyasini ochadi: so'rov sessiyasi
    javob yuborilgach yopilgan bo'ladi.

    Bu funksiya hech qachon xato tashlamaydi — buyurtma allaqachon qabul
    qilingan va bildirishnoma yetib bormagani uni bekor qilmaydi.
    """
    from app.database import SessionLocal

    try:
        with SessionLocal() as db:
            people = _waiter_ids(db, restaurant_id, table_id)
            if not people:
                return
            _notify_browsers(db, people)
            _notify_apps(db, people)
    except Exception:
        log.warning("Bildirishnoma bosqichida xato", exc_info=True)


# Buyurtma javobsiz qolsa qachon qayta eslatiladi (soniyada).
#
# Bitta bildirishnoma yetarli emas: shovqinli zalda afitsant telefonni
# eshitmasligi, qo'lida laganda bo'lishi yoki oshxonada turgan bo'lishi
# mumkin. Ikkita eslatma — o'rtacha yo'l: buyurtma yo'qolib ketmaydi, lekin
# telefon ham cheksiz jiringlamaydi.
#
# Eslatma faqat buyurtma HAMON "yangi" bo'lsa yuboriladi. Afitsant "Qabul
# qildim" bosgan zahoti to'xtaydi.
ESLATMA_VAQTLARI = (45, 120)


def remind_until_answered(restaurant_id: int, order_id: int, table_id: int | None) -> None:
    """Javobsiz buyurtma uchun keyinroq yana turtki yuboradi.

    `threading.Timer` ataylab: ishchi oqimni ushlab turmaydi va yengil.
    Server qayta ishga tushsa eslatma yo'qoladi — bu qabul qilingan narsa,
    chunki buyurtmaning o'zi bazada qoladi va taxtada baribir ko'rinadi.
    """
    import threading

    for kechikish in ESLATMA_VAQTLARI:
        timer = threading.Timer(
            kechikish, _remind_once, args=(restaurant_id, order_id, table_id)
        )
        timer.daemon = True
        timer.start()


def _remind_once(restaurant_id: int, order_id: int, table_id: int | None) -> None:
    from app.database import SessionLocal
    from app.models import Order, OrderStatus

    try:
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            # Javob berilgan yoki o'chirilgan bo'lsa eslatma keraksiz
            if order is None or order.status is not OrderStatus.new:
                return
        notify_restaurant(restaurant_id, table_id)
    except Exception:
        log.warning("Eslatma yuborilmadi", exc_info=True)


def save(db: Session, user: User, endpoint: str, p256dh: str, auth: str) -> PushSubscription:
    """Obunani saqlaydi yoki mavjudini shu foydalanuvchiga bog'laydi.

    Bir qurilma qayta obuna bo'lsa yozuv KO'PAYMAYDI — `endpoint` yagona.
    Qurilma boshqa xodimga o'tsa (masalan umumiy planshet) egasi almashadi,
    aks holda eski xodim ketganidan keyin ham bildirishnoma olib turardi.
    """
    row = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
    if row is None:
        row = PushSubscription(endpoint=endpoint)
        db.add(row)
    row.user_id = user.id
    row.p256dh = p256dh
    row.auth = auth
    db.commit()
    return row


def forget(db: Session, endpoint: str) -> None:
    db.execute(delete(PushSubscription).where(PushSubscription.endpoint == endpoint))
    db.commit()
