from starlette.requests import Request

LANGUAGES: dict[str, str] = {"uz": "O'zbekcha", "ru": "Русский", "en": "English"}
DEFAULT_LANG = "uz"
LANG_COOKIE = "lang"

UI: dict[str, dict[str, str]] = {
    "uz": {
        "menu": "Menyu",
        "search_placeholder": "Taom qidirish...",
        "no_results": "Hech narsa topilmadi",
        "empty_menu": "Menyu hozircha bo'sh",
        "unavailable": "Mavjud emas",
        "popular": "Ommabop",
        "all": "Hammasi",
        "back": "Orqaga",
        "ingredients": "Tarkibi",
        "close": "Yopish",
        "allergens": "Allergenlar",
        "wifi": "Wi-Fi",
        "spicy": "O'tkir",
        "vegetarian": "Vegetarian",
        "halal": "Halol",
        "todays_special": "Bugungi taklif",
        "min": "daq",
        "comments": "Izohlar",
        "no_comments": "Hozircha izoh yo'q. Birinchi bo'ling.",
        "your_name": "Ismingiz",
        "your_comment": "Fikringiz",
        "send": "Yuborish",
        "comment_pending": "Rahmat! Izohingiz restoran tasdiqlagach ko'rinadi.",
        "contact": "Aloqa",
        "address": "Manzil",
        "working_hours": "Ish vaqti",
        "restaurant_closed": "Bu restoran vaqtincha faol emas",
        "not_found": "Sahifa topilmadi",
    },
    "ru": {
        "menu": "Меню",
        "search_placeholder": "Поиск блюда...",
        "no_results": "Ничего не найдено",
        "empty_menu": "Меню пока пустое",
        "unavailable": "Нет в наличии",
        "popular": "Популярное",
        "all": "Все",
        "back": "Назад",
        "ingredients": "Состав",
        "close": "Закрыть",
        "allergens": "Аллергены",
        "wifi": "Wi-Fi",
        "spicy": "Острое",
        "vegetarian": "Вегетарианское",
        "halal": "Халяль",
        "todays_special": "Предложение дня",
        "min": "мин",
        "comments": "Отзывы",
        "no_comments": "Пока нет отзывов. Будьте первым.",
        "your_name": "Ваше имя",
        "your_comment": "Ваш отзыв",
        "send": "Отправить",
        "comment_pending": "Спасибо! Отзыв появится после проверки рестораном.",
        "contact": "Контакты",
        "address": "Адрес",
        "working_hours": "Часы работы",
        "restaurant_closed": "Этот ресторан временно неактивен",
        "not_found": "Страница не найдена",
    },
    "en": {
        "menu": "Menu",
        "search_placeholder": "Search dishes...",
        "no_results": "Nothing found",
        "empty_menu": "The menu is empty for now",
        "unavailable": "Unavailable",
        "popular": "Popular",
        "all": "All",
        "back": "Back",
        "ingredients": "Ingredients",
        "close": "Close",
        "allergens": "Allergens",
        "wifi": "Wi-Fi",
        "spicy": "Spicy",
        "vegetarian": "Vegetarian",
        "halal": "Halal",
        "todays_special": "Today's special",
        "min": "min",
        "comments": "Comments",
        "no_comments": "No comments yet. Be the first.",
        "your_name": "Your name",
        "your_comment": "Your comment",
        "send": "Send",
        "comment_pending": "Thank you! Your comment appears once the restaurant approves it.",
        "contact": "Contact",
        "address": "Address",
        "working_hours": "Opening hours",
        "restaurant_closed": "This restaurant is temporarily inactive",
        "not_found": "Page not found",
    },
}


def t(key: str, lang: str) -> str:
    return UI.get(lang, UI[DEFAULT_LANG]).get(key) or UI[DEFAULT_LANG].get(key, key)


def tr(value: dict | str | None, lang: str) -> str:
    """Translate a stored i18n field, falling back to the default language."""
    if isinstance(value, str):
        return value
    if not value:
        return ""
    text = value.get(lang)
    if text:
        return text
    for fallback in (DEFAULT_LANG, *LANGUAGES):
        text = value.get(fallback)
        if text:
            return text
    return ""


def resolve_lang(request: Request) -> str:
    for candidate in (
        request.query_params.get("lang"),
        request.cookies.get(LANG_COOKIE),
        _from_accept_language(request.headers.get("accept-language", "")),
    ):
        if candidate in LANGUAGES:
            return candidate
    return DEFAULT_LANG


def _from_accept_language(header: str) -> str | None:
    for part in header.split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGUAGES:
            return code
    return None
