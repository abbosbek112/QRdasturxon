"""Tariflar, sinov muddati va cheklovlar.

Muhim qoida: **obuna tugasa ham mijoz menyusi ochiq qoladi**. Faqat admin
panelidagi imkoniyatlar toraydi. Restoranning stolidagi QR kodni ishlamay
qo'yish — restoranga ham, uning mijoziga ham zarar, to'lovni esa tezlashtirmaydi.
"""

from dataclasses import dataclass
from datetime import timedelta
from math import ceil

from app.models import Plan, Restaurant, SubscriptionStatus, utcnow_naive

TRIAL_DAYS = 7


@dataclass(frozen=True)
class Limits:
    name: str
    price_yearly: int  # so'mda, 0 = bepul
    max_items: int | None  # None = cheksiz
    max_categories: int | None
    languages: tuple[str, ...]
    stats_days: int
    specials: bool  # "Bugungi taklif" bo'limi
    comments: bool  # taomlarga izoh
    printable: bool  # chop etish uchun menyu

    def allows_language(self, lang: str) -> bool:
        return lang in self.languages


# Wi-Fi paroli va taom belgilari ataylab bepulda ham ochiq: mahsulot birinchi
# kundan yoqishi kerak, aks holda ikkinchi yilga qadar yetib bormaydi.
LIMITS: dict[Plan, Limits] = {
    Plan.free: Limits(
        name="Bepul",
        price_yearly=0,
        max_items=20,
        max_categories=3,
        languages=("uz",),
        stats_days=7,
        specials=False,
        comments=False,
        printable=False,
    ),
    Plan.full: Limits(
        name="To'liq",
        price_yearly=600_000,
        max_items=None,
        max_categories=None,
        languages=("uz", "ru", "en"),
        stats_days=365,
        specials=True,
        comments=True,
        printable=True,
    ),
}


def start_trial(restaurant: Restaurant) -> None:
    restaurant.plan = Plan.free
    restaurant.subscription_status = SubscriptionStatus.trial
    restaurant.trial_ends_at = utcnow_naive() + timedelta(days=TRIAL_DAYS)


def refresh_status(restaurant: Restaurant) -> bool:
    """Muddati o'tgan obunani `expired` ga o'tkazadi. O'zgarish bo'lsa True."""
    now = utcnow_naive()
    status = restaurant.subscription_status

    if status is SubscriptionStatus.trial:
        if restaurant.trial_ends_at and restaurant.trial_ends_at < now:
            restaurant.subscription_status = SubscriptionStatus.expired
            return True
    elif status is SubscriptionStatus.active:
        if restaurant.paid_until and restaurant.paid_until < now:
            restaurant.subscription_status = SubscriptionStatus.expired
            return True
    return False


def effective_plan(restaurant: Restaurant) -> Plan:
    """Hozir amalda qaysi tarif imkoniyatlari ishlayapti.

    Sinov muddatida restoran To'liq imkoniyatlarni ko'radi — shunda u nima
    sotib olayotganini bilib turadi. Muddat tugasa Bepul darajaga tushadi.
    """
    if restaurant.subscription_status is SubscriptionStatus.trial:
        return Plan.full
    if restaurant.subscription_status is SubscriptionStatus.expired:
        return Plan.free
    return restaurant.plan


def limits_for(restaurant: Restaurant) -> Limits:
    return LIMITS[effective_plan(restaurant)]


def trial_days_left(restaurant: Restaurant) -> int:
    """Qolgan kunlar, yuqoriga yaxlitlangan: yarim kun qolsa ham "1 kun" deydi."""
    if restaurant.subscription_status is not SubscriptionStatus.trial:
        return 0
    if not restaurant.trial_ends_at:
        return 0
    seconds = (restaurant.trial_ends_at - utcnow_naive()).total_seconds()
    return max(0, ceil(seconds / 86400))


def visible_languages(restaurant: Restaurant) -> tuple[str, ...]:
    return limits_for(restaurant).languages
