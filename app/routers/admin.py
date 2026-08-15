from datetime import timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse, Response
from PIL import UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.flash import set_flash
from app.i18n import resolve_lang, t
from app.models import (
    Category,
    Combo,
    ItemComment,
    MenuItem,
    Restaurant,
    Role,
    TableKind,
    User,
)
from app.plans import limits_for, refresh_status, trial_days_left
from app.security import hash_password, require_restaurant_admin, verify_csrf
from app import themes
from app.services import areas, combos, comments, onboarding, orders, qr, qr_pack, stats, tables
from app.services import staff as staff_svc
from app.services.images import MAX_BYTES as MAX_IMAGE_BYTES, delete_image, save_image
from app.templating import floor_label, templates

router = APIRouter(prefix="/admin", tags=["admin"])

DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_restaurant_admin)]


def i18n_field(uz: str, ru: str, en: str) -> dict:
    return {
        lang: text.strip()
        for lang, text in (("uz", uz), ("ru", ru), ("en", en))
        if text and text.strip()
    }


def get_restaurant(db: Session, user: User) -> Restaurant:
    restaurant = db.get(Restaurant, user.restaurant_id)
    if restaurant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restoran topilmadi")
    # Sinov muddati tugagan bo'lsa holatni shu yerda yangilaymiz — alohida
    # fon vazifasi kerak bo'lmaydi, admin panelga kirganda o'zi tekshiriladi
    if refresh_status(restaurant):
        db.commit()
    return restaurant


def check_item_limit(db: Session, restaurant: Restaurant) -> None:
    limit = limits_for(restaurant).max_items
    if limit is None:
        return
    used = db.scalar(
        select(func.count(MenuItem.id)).where(MenuItem.restaurant_id == restaurant.id)
    )
    if used >= limit:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Tarifingizda {limit} tagacha taom qo'shish mumkin. "
            "Ko'proq kerak bo'lsa tarifni ko'taring.",
        )


def check_category_limit(db: Session, restaurant: Restaurant) -> None:
    limit = limits_for(restaurant).max_categories
    if limit is None:
        return
    used = db.scalar(
        select(func.count(Category.id)).where(Category.restaurant_id == restaurant.id)
    )
    if used >= limit:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Tarifingizda {limit} tagacha kategoriya mumkin. "
            "Ko'proq kerak bo'lsa tarifni ko'taring.",
        )


def form_failed(request: Request, error: HTTPException, target: str) -> RedirectResponse:
    """Forma xatosini o'sha sahifaning o'ziga qaytaradi.

    Ilgari har qanday xato to'liq xato sahifasiga otvorib yuborardi: egasi
    stollarni ketma-ket kiritib o'tirganda bitta takror raqam uni ishidan
    uzib, boshqa sahifaga tashlardi. Endi xabar sahifa tepasida chiqadi.

    Faqat FOYDALANUVCHI xatosi ushlanadi. 403/404 kabilar o'z holicha
    o'tadi — ular forma xatosi emas va ularni yumshoq xabarga aylantirish
    haqiqiy muammoni yashirardi.
    """
    if error.status_code not in (
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_429_TOO_MANY_REQUESTS,
    ):
        raise error
    set_flash(request, error.detail)
    return RedirectResponse(target, status.HTTP_303_SEE_OTHER)


def owned_category(db: Session, user: User, category_id: int) -> Category:
    category = db.scalar(
        select(Category).where(
            Category.id == category_id, Category.restaurant_id == user.restaurant_id
        )
    )
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kategoriya topilmadi")
    return category


def owned_item(db: Session, user: User, item_id: int) -> MenuItem:
    item = db.scalar(
        select(MenuItem).where(
            MenuItem.id == item_id, MenuItem.restaurant_id == user.restaurant_id
        )
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Taom topilmadi")
    return item


@router.get("")
def dashboard(request: Request, db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    category_count = db.scalar(
        select(func.count(Category.id)).where(Category.restaurant_id == restaurant.id)
    )
    item_count = db.scalar(
        select(func.count(MenuItem.id)).where(MenuItem.restaurant_id == restaurant.id)
    )
    hidden_count = db.scalar(
        select(func.count(MenuItem.id)).where(
            MenuItem.restaurant_id == restaurant.id, MenuItem.is_available.is_(False)
        )
    )
    limits = limits_for(restaurant)
    # Kunlik ustunlar 30 tadan oshsa ingichkalashib ko'rinmay qoladi — bosh
    # sahifadagi grafikni shu bilan cheklaymiz. To'liq tahlil /admin/stats da.
    chart_days = min(limits.stats_days, 30)
    chart_end = stats.today()
    chart_start = chart_end - timedelta(days=chart_days - 1)
    window_start = chart_end - timedelta(days=limits.stats_days - 1)
    daily = stats.daily_series(db, restaurant.id, chart_start, chart_end)

    # Buyurtma yoqilgan restoran uchun BUGUNGI kun eng muhim raqam —
    # ochilishlar emas. Yoqilmagan restoranda esa bu blok umuman
    # chizilmaydi, aks holda panel doim nol ko'rsatib turardi.
    today = orders.day_summary(db, restaurant.id, chart_end) if restaurant.orders_enabled else None
    combo_count = db.scalar(
        select(func.count(Combo.id)).where(Combo.restaurant_id == restaurant.id)
    )
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "user": user,
            "restaurant": restaurant,
            "category_count": category_count,
            "item_count": item_count,
            "hidden_count": hidden_count,
            "combo_count": combo_count,
            "today": today,
            "menu_url": qr.menu_url(restaurant.slug),
            "daily_views": daily,
            "views_total": stats.total_views(db, restaurant.id, window_start, chart_end),
            "views_peak": max((count for _, count in daily), default=0),
            "top_items": stats.top_items(db, restaurant.id, window_start, chart_end),
            "limits": limits,
            "chart_days": chart_days,
            "trial_days": trial_days_left(restaurant),
            # Barcha qadam bajarilgach ro'yxat o'zi yo'qoladi
            "steps": [s for s in onboarding.setup_steps(db, restaurant)],
        },
    )


@router.get("/stats")
def statistics(
    request: Request,
    db: DbSession,
    user: AdminUser,
    period: str = "oy",
    start: str | None = None,
    end: str | None = None,
):
    """Analitika: ixtiyoriy muddat ichida nima necha marta ochilgan."""
    restaurant = get_restaurant(db, user)
    limits = limits_for(restaurant)
    first, last, preset = stats.resolve_range(period, start, end, limits.stats_days)

    daily = stats.daily_series(db, restaurant.id, first, last)
    ranked = stats.top_items(db, restaurant.id, first, last, limit=25)
    # Baho izohlar bilan keladi, ochilish esa MenyuView bilan — ikkalasini
    # taom bo'yicha birlashtiramiz, shunda bitta jadvalda ko'rinadi
    ratings = comments.rating_summary(db, [item.id for item, _ in ranked])

    return templates.TemplateResponse(
        request,
        "admin/stats.html",
        {
            "user": user,
            "restaurant": restaurant,
            "limits": limits,
            "presets": stats.PRESETS,
            "preset": preset,
            "start": first,
            "end": last,
            "daily_views": daily,
            "views_peak": max((count for _, count in daily), default=0),
            "views_total": stats.total_views(db, restaurant.id, first, last),
            "top_items": ranked,
            "ratings": ratings,
            "best_rated": comments.best_rated(db, restaurant.id, limit=10),
        },
    )


@router.get("/settings")
def settings_form(request: Request, db: DbSession, user: AdminUser):
    return templates.TemplateResponse(
        request,
        "admin/settings.html",
        {"user": user, "restaurant": get_restaurant(db, user)},
    )


@router.post("/settings", dependencies=[Depends(verify_csrf)])
async def update_settings(
    db: DbSession,
    user: AdminUser,
    name: Annotated[str, Form()],
    description_uz: Annotated[str, Form()] = "",
    description_ru: Annotated[str, Form()] = "",
    description_en: Annotated[str, Form()] = "",
    address_uz: Annotated[str, Form()] = "",
    address_ru: Annotated[str, Form()] = "",
    address_en: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
    working_hours: Annotated[str, Form()] = "",
    instagram: Annotated[str, Form()] = "",
    telegram: Annotated[str, Form()] = "",
    wifi_name: Annotated[str, Form()] = "",
    wifi_password: Annotated[str, Form()] = "",
    currency: Annotated[str, Form()] = "so'm",
    orders_enabled: Annotated[bool, Form()] = False,
    order_window_minutes: Annotated[int, Form()] = 30,
):
    restaurant = get_restaurant(db, user)
    restaurant.name = name.strip() or restaurant.name
    restaurant.description = i18n_field(description_uz, description_ru, description_en)
    restaurant.address = i18n_field(address_uz, address_ru, address_en)
    restaurant.phone = phone.strip() or None
    restaurant.working_hours = working_hours.strip() or None
    restaurant.instagram = instagram.strip() or None
    restaurant.telegram = telegram.strip() or None
    restaurant.wifi_name = wifi_name.strip() or None
    restaurant.wifi_password = wifi_password.strip() or None
    restaurant.currency = currency.strip() or restaurant.currency
    restaurant.orders_enabled = orders_enabled
    # 0 = cheksiz. Yuqori chegara — formadan tasodifan katta son kelib qolmasin
    restaurant.order_window_minutes = (
        0 if order_window_minutes <= 0 else min(order_window_minutes, 240)
    )

    db.commit()
    return RedirectResponse("/admin/settings", status.HTTP_303_SEE_OTHER)


@router.get("/design")
def design_page(request: Request, db: DbSession, user: AdminUser):
    """Menyu dizayni — Sozlamalardan chiqarilgan alohida bo'lim.

    Ilgari uslub tanlash Sozlamalarning o'rtasida, ish vaqti va Wi-Fi
    paroli orasida turardi. Dizayn bir marta qilinadigan va vaqt talab
    qiladigan ish — u o'z sahifasiga arziydi. Sozlamalarda esa faqat
    ishlash sozlamalari qoldi.
    """
    restaurant = get_restaurant(db, user)
    return templates.TemplateResponse(
        request,
        "admin/design.html",
        {
            "user": user,
            "restaurant": restaurant,
            "accents": themes.ACCENTS,
            # Hozirgi uslub shu yerda hal qilinadi: shablonda "agar
            # ro'yxatda bo'lsa, aks holda standarti" degan shart
            # `themes.get()` mantiqini ikkinchi marta yozgan bo'lardi
            "current_theme": themes.get(restaurant.theme),
            # Ko'rish uchun namuna taom: egasining o'z menyusidan olinadi,
            # shunda u o'z taomini o'z uslubida ko'radi
            "sample": db.scalar(
                select(MenuItem)
                .where(
                    MenuItem.restaurant_id == restaurant.id,
                    MenuItem.is_available.is_(True),
                )
                .order_by(MenuItem.image.is_(None), MenuItem.sort_order, MenuItem.id)
            ),
        },
    )


@router.post("/design", dependencies=[Depends(verify_csrf)])
async def update_design(
    db: DbSession,
    user: AdminUser,
    theme: Annotated[str, Form()] = "",
    theme_color: Annotated[str, Form()] = "",
    own_color: Annotated[str, Form()] = "",
    remove_logo: Annotated[bool, Form()] = False,
    remove_cover: Annotated[bool, Form()] = False,
    logo: Annotated[UploadFile | None, File()] = None,
    cover_image: Annotated[UploadFile | None, File()] = None,
):
    restaurant = get_restaurant(db, user)

    if theme in themes.THEMES:
        restaurant.theme = theme
    # `__own__` — "yonidagi maydondan ol" degan belgi. Tayyor ranglar
    # radio bo'lib keladi va ular bilan bir nomda `<input type="color">`
    # yuborib bo'lmaydi.
    tanlangan = own_color if theme_color == "__own__" else theme_color
    # Rang menyu sahifasining <style> ichiga tushadi — shakli
    # tekshirilmasa u yerdan chiqib ketish mumkin edi
    if tanlangan:
        restaurant.theme_color = themes.safe_accent(
            themes.get(restaurant.theme), tanlangan
        )

    if logo is not None and logo.filename:
        old = restaurant.logo
        restaurant.logo = await save_image(logo, restaurant.id, max_width=400)
        delete_image(old)
    elif remove_logo:
        delete_image(restaurant.logo)
        restaurant.logo = None

    if cover_image is not None and cover_image.filename:
        old = restaurant.cover_image
        restaurant.cover_image = await save_image(cover_image, restaurant.id, max_width=1600)
        delete_image(old)
    elif remove_cover:
        delete_image(restaurant.cover_image)
        restaurant.cover_image = None

    db.commit()
    return RedirectResponse("/admin/design", status.HTTP_303_SEE_OTHER)


@router.get("/menu")
def menu_page(request: Request, db: DbSession, user: AdminUser):
    """Kategoriya va taomlar BITTA sahifada.

    Ilgari ular ikki bo'lim edi. Taomni tartiblash uchun odam kategoriyadan
    chiqib ketishga majbur bo'lardi va qaysi taom qayerga tegishli ekani
    ko'rinmasdi. Endi taom o'z kategoriyasi ichida turadi.
    """
    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == user.restaurant_id)
        .options(selectinload(Category.items))
        .order_by(Category.sort_order, Category.id)
    ).all()
    return templates.TemplateResponse(
        request,
        "admin/menu.html",
        {"user": user, "restaurant": get_restaurant(db, user), "categories": categories},
    )


@router.get("/categories")
def categories_page(user: AdminUser):
    """Eski manzil — endi menyuning bir qismi. Xatcho'plar buzilmasin."""
    return RedirectResponse("/admin/menu", status.HTTP_303_SEE_OTHER)


@router.post("/categories", dependencies=[Depends(verify_csrf)])
async def create_category(
    request: Request,
    db: DbSession,
    user: AdminUser,
    name_uz: Annotated[str, Form()],
    name_ru: Annotated[str, Form()] = "",
    name_en: Annotated[str, Form()] = "",
    sort_order: Annotated[int, Form()] = 0,
    image: Annotated[UploadFile | None, File()] = None,
):
    try:
        if not name_uz.strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kategoriya nomi bo'sh bo'lmasin")
        check_category_limit(db, get_restaurant(db, user))
    except HTTPException as error:
        return form_failed(request, error, "/admin/menu")

    # Kategoriya rasmi taom rasmidan kichik: u menyuda kichkina belgi
    # bo'lib turadi, kartaning butun enini egallamaydi
    picture = None
    if image is not None and image.filename:
        picture = await save_image(image, user.restaurant_id, max_width=400)

    db.add(
        Category(
            restaurant_id=user.restaurant_id,
            name=i18n_field(name_uz, name_ru, name_en),
            image=picture,
            sort_order=sort_order,
        )
    )
    db.commit()
    return RedirectResponse("/admin/menu", status.HTTP_303_SEE_OTHER)


@router.post("/categories/{category_id}", dependencies=[Depends(verify_csrf)])
async def update_category(
    db: DbSession,
    user: AdminUser,
    category_id: int,
    name_uz: Annotated[str, Form()],
    name_ru: Annotated[str, Form()] = "",
    name_en: Annotated[str, Form()] = "",
    sort_order: Annotated[int, Form()] = 0,
    is_active: Annotated[bool, Form()] = False,
    remove_image: Annotated[bool, Form()] = False,
    image: Annotated[UploadFile | None, File()] = None,
):
    category = owned_category(db, user, category_id)
    category.name = i18n_field(name_uz, name_ru, name_en) or category.name
    category.sort_order = sort_order
    category.is_active = is_active

    if image is not None and image.filename:
        old = category.image
        category.image = await save_image(image, user.restaurant_id, max_width=400)
        delete_image(old)
    elif remove_image:
        delete_image(category.image)
        category.image = None

    db.commit()
    return RedirectResponse("/admin/menu", status.HTTP_303_SEE_OTHER)


@router.post("/categories/{category_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_category(db: DbSession, user: AdminUser, category_id: int):
    category = owned_category(db, user, category_id)
    for item in category.items:
        delete_image(item.image)
    delete_image(category.image)
    db.delete(category)
    db.commit()
    return RedirectResponse("/admin/menu", status.HTTP_303_SEE_OTHER)


@router.get("/combos")
def combos_page(request: Request, db: DbSession, user: AdminUser):
    """Kombo to'plamlari — menyu bo'limining ichida alohida sahifa."""
    restaurant = get_restaurant(db, user)
    rows = combos.list_for(db, restaurant.id)
    return templates.TemplateResponse(
        request,
        "admin/combos.html",
        {
            "user": user,
            "restaurant": restaurant,
            "combos": [
                {
                    "combo": combo,
                    "full": combos.full_price(combo),
                    "saving": combos.saving(combo),
                    "orderable": combos.is_orderable(combo),
                    # Tarkib formasi uchun: qaysi taom nechta
                    "chosen": {line.item_id: line.quantity for line in combo.lines},
                }
                for combo in rows
            ],
            "items": db.scalars(
                select(MenuItem)
                .where(MenuItem.restaurant_id == restaurant.id)
                .order_by(MenuItem.category_id, MenuItem.sort_order, MenuItem.id)
            ).all(),
        },
    )


async def _combo_lines(request: Request) -> list[tuple[int, int]]:
    """Tanlangan taomlar va ularning soni.

    Soni `qty_<taom raqami>` deb nomlangan maydonda keladi, oddiy `qty`
    ro'yxatida emas. Sabab jiddiy: belgilanmagan katakcha brauzer
    tomonidan YUBORILMAYDI, lekin uning yonidagi son maydoni yuboriladi.
    Ikki parallel ro'yxatda bu siljishga olib kelardi — birinchi taomni
    belgilamay ikkinchisini belgilasangiz, ikkinchisiga birinchisining
    soni yopishardi va egasi buni faqat kombo narxi noto'g'ri chiqqanda
    payqardi.

    Nomga bog'lash bu xatoni butunlay yo'q qiladi: har son o'z taomiga
    tegishli va tartib ahamiyatsiz.
    """
    form = await request.form()
    lines: list[tuple[int, int]] = []
    for raw_id in form.getlist("item_id"):
        try:
            item_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        try:
            quantity = int(form.get(f"qty_{item_id}") or 1)
        except (TypeError, ValueError):
            quantity = 1
        lines.append((item_id, quantity))
    return lines


@router.post("/combos", dependencies=[Depends(verify_csrf)])
async def create_combo(
    request: Request,
    db: DbSession,
    user: AdminUser,
    name_uz: Annotated[str, Form()],
    name_ru: Annotated[str, Form()] = "",
    name_en: Annotated[str, Form()] = "",
    description_uz: Annotated[str, Form()] = "",
    description_ru: Annotated[str, Form()] = "",
    description_en: Annotated[str, Form()] = "",
    price: Annotated[Decimal, Form()] = Decimal("0"),
    sort_order: Annotated[int, Form()] = 0,
    image: Annotated[UploadFile | None, File()] = None,
):
    restaurant = get_restaurant(db, user)
    picture = None
    if image is not None and image.filename:
        picture = await save_image(image, restaurant.id, max_width=800)
    try:
        combos.create(
            db,
            restaurant.id,
            name=i18n_field(name_uz, name_ru, name_en),
            description=i18n_field(description_uz, description_ru, description_en),
            price=price,
            sort_order=sort_order,
            image=picture,
            lines=await _combo_lines(request),
        )
    except HTTPException as error:
        delete_image(picture)
        return form_failed(request, error, "/admin/combos")
    return RedirectResponse("/admin/combos", status.HTTP_303_SEE_OTHER)


@router.post("/combos/{combo_id}", dependencies=[Depends(verify_csrf)])
async def update_combo(
    request: Request,
    db: DbSession,
    user: AdminUser,
    combo_id: int,
    name_uz: Annotated[str, Form()],
    name_ru: Annotated[str, Form()] = "",
    name_en: Annotated[str, Form()] = "",
    description_uz: Annotated[str, Form()] = "",
    description_ru: Annotated[str, Form()] = "",
    description_en: Annotated[str, Form()] = "",
    price: Annotated[Decimal, Form()] = Decimal("0"),
    sort_order: Annotated[int, Form()] = 0,
    is_active: Annotated[bool, Form()] = False,
    remove_image: Annotated[bool, Form()] = False,
    image: Annotated[UploadFile | None, File()] = None,
):
    combo = combos.owned(db, user.restaurant_id, combo_id)
    combo.name = i18n_field(name_uz, name_ru, name_en) or combo.name
    combo.description = i18n_field(description_uz, description_ru, description_en)
    combo.price = max(price, Decimal("0"))
    combo.sort_order = sort_order
    combo.is_active = is_active
    combos.set_lines(db, combo, await _combo_lines(request))

    if image is not None and image.filename:
        old = combo.image
        combo.image = await save_image(image, user.restaurant_id, max_width=800)
        delete_image(old)
    elif remove_image:
        delete_image(combo.image)
        combo.image = None

    db.commit()
    return RedirectResponse("/admin/combos", status.HTTP_303_SEE_OTHER)


@router.post("/combos/{combo_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_combo(db: DbSession, user: AdminUser, combo_id: int):
    combo = combos.owned(db, user.restaurant_id, combo_id)
    delete_image(combo.image)
    db.delete(combo)
    db.commit()
    return RedirectResponse("/admin/combos", status.HTTP_303_SEE_OTHER)


@router.get("/items")
def items_page(user: AdminUser):
    """Taomlar endi menyuning ichida — kategoriyasi bilan birga ko'rinadi."""
    return RedirectResponse("/admin/menu", status.HTTP_303_SEE_OTHER)


@router.get("/items/new")
def new_item_form(request: Request, db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == user.restaurant_id)
        .order_by(Category.sort_order, Category.id)
    ).all()
    return templates.TemplateResponse(
        request,
        "admin/item_form.html",
        {
            "user": user,
            "restaurant": restaurant,
            "categories": categories,
            "item": None,
            "limits": limits_for(restaurant),
        },
    )


@router.get("/items/{item_id}/edit")
def edit_item_form(request: Request, db: DbSession, user: AdminUser, item_id: int):
    restaurant = get_restaurant(db, user)
    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == user.restaurant_id)
        .order_by(Category.sort_order, Category.id)
    ).all()
    return templates.TemplateResponse(
        request,
        "admin/item_form.html",
        {
            "user": user,
            "restaurant": restaurant,
            "categories": categories,
            "item": owned_item(db, user, item_id),
            "limits": limits_for(restaurant),
        },
    )


@router.post("/items", dependencies=[Depends(verify_csrf)])
async def create_item(
    request: Request,
    db: DbSession,
    user: AdminUser,
    category_id: Annotated[int, Form()],
    name_uz: Annotated[str, Form()],
    price: Annotated[float, Form()],
    name_ru: Annotated[str, Form()] = "",
    name_en: Annotated[str, Form()] = "",
    description_uz: Annotated[str, Form()] = "",
    description_ru: Annotated[str, Form()] = "",
    description_en: Annotated[str, Form()] = "",
    ingredients_uz: Annotated[str, Form()] = "",
    ingredients_ru: Annotated[str, Form()] = "",
    ingredients_en: Annotated[str, Form()] = "",
    allergens_uz: Annotated[str, Form()] = "",
    allergens_ru: Annotated[str, Form()] = "",
    allergens_en: Annotated[str, Form()] = "",
    prep_minutes: Annotated[int, Form()] = 0,
    sort_order: Annotated[int, Form()] = 0,
    is_popular: Annotated[bool, Form()] = False,
    is_special: Annotated[bool, Form()] = False,
    is_spicy: Annotated[bool, Form()] = False,
    is_vegetarian: Annotated[bool, Form()] = False,
    image: Annotated[UploadFile | None, File()] = None,
):
    category = owned_category(db, user, category_id)
    try:
        if not name_uz.strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Taom nomi bo'sh bo'lmasin")
        check_item_limit(db, get_restaurant(db, user))
    except HTTPException as error:
        return form_failed(request, error, "/admin/items/new")

    item = MenuItem(
        restaurant_id=user.restaurant_id,
        category_id=category.id,
        name=i18n_field(name_uz, name_ru, name_en),
        description=i18n_field(description_uz, description_ru, description_en),
        ingredients=i18n_field(ingredients_uz, ingredients_ru, ingredients_en),
        allergens=i18n_field(allergens_uz, allergens_ru, allergens_en),
        price=max(price, 0),
        prep_minutes=max(prep_minutes, 0),
        sort_order=sort_order,
        is_popular=is_popular,
        is_special=is_special,
        is_spicy=is_spicy,
        is_vegetarian=is_vegetarian,
    )
    if image is not None and image.filename:
        item.image = await save_image(image, user.restaurant_id, max_width=1000)
    db.add(item)
    db.commit()
    return RedirectResponse("/admin/menu", status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}", dependencies=[Depends(verify_csrf)])
async def update_item(
    db: DbSession,
    user: AdminUser,
    item_id: int,
    category_id: Annotated[int, Form()],
    name_uz: Annotated[str, Form()],
    price: Annotated[float, Form()],
    name_ru: Annotated[str, Form()] = "",
    name_en: Annotated[str, Form()] = "",
    description_uz: Annotated[str, Form()] = "",
    description_ru: Annotated[str, Form()] = "",
    description_en: Annotated[str, Form()] = "",
    ingredients_uz: Annotated[str, Form()] = "",
    ingredients_ru: Annotated[str, Form()] = "",
    ingredients_en: Annotated[str, Form()] = "",
    allergens_uz: Annotated[str, Form()] = "",
    allergens_ru: Annotated[str, Form()] = "",
    allergens_en: Annotated[str, Form()] = "",
    prep_minutes: Annotated[int, Form()] = 0,
    sort_order: Annotated[int, Form()] = 0,
    is_popular: Annotated[bool, Form()] = False,
    is_special: Annotated[bool, Form()] = False,
    is_spicy: Annotated[bool, Form()] = False,
    is_vegetarian: Annotated[bool, Form()] = False,
    is_available: Annotated[bool, Form()] = False,
    remove_image: Annotated[bool, Form()] = False,
    image: Annotated[UploadFile | None, File()] = None,
):
    item = owned_item(db, user, item_id)
    category = owned_category(db, user, category_id)

    item.category_id = category.id
    item.name = i18n_field(name_uz, name_ru, name_en) or item.name
    item.description = i18n_field(description_uz, description_ru, description_en)
    item.ingredients = i18n_field(ingredients_uz, ingredients_ru, ingredients_en)
    item.allergens = i18n_field(allergens_uz, allergens_ru, allergens_en)
    item.price = max(price, 0)
    item.prep_minutes = max(prep_minutes, 0)
    item.sort_order = sort_order
    item.is_popular = is_popular
    item.is_special = is_special
    item.is_spicy = is_spicy
    item.is_vegetarian = is_vegetarian
    item.is_available = is_available

    if image is not None and image.filename:
        old = item.image
        item.image = await save_image(image, user.restaurant_id, max_width=1000)
        delete_image(old)
    elif remove_image:
        delete_image(item.image)
        item.image = None

    db.commit()
    return RedirectResponse("/admin/menu", status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}/order", dependencies=[Depends(verify_csrf)])
def reorder_item(
    db: DbSession,
    user: AdminUser,
    item_id: int,
    sort_order: Annotated[int, Form()] = 0,
):
    """Taomning kategoriya ichidagi tartibi.

    Alohida marshrut: to'liq tahrir formasi rasm va tarjimalarni ham
    talab qiladi, tartibni o'zgartirish uchun esa ularni qaytadan
    yuborishning ma'nosi yo'q.
    """
    item = owned_item(db, user, item_id)
    item.sort_order = sort_order
    db.commit()
    return RedirectResponse("/admin/menu", status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}/toggle", dependencies=[Depends(verify_csrf)])
def toggle_item(db: DbSession, user: AdminUser, item_id: int):
    item = owned_item(db, user, item_id)
    item.is_available = not item.is_available
    db.commit()
    return RedirectResponse("/admin/menu", status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_item(db: DbSession, user: AdminUser, item_id: int):
    item = owned_item(db, user, item_id)
    delete_image(item.image)
    db.delete(item)
    db.commit()
    return RedirectResponse("/admin/menu", status.HTTP_303_SEE_OTHER)


@router.get("/comments")
def comments_page(request: Request, db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    rows = db.scalars(
        select(ItemComment)
        .where(ItemComment.restaurant_id == restaurant.id)
        .options(selectinload(ItemComment.item))
        .order_by(ItemComment.is_approved, ItemComment.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        request,
        "admin/comments.html",
        {
            "user": user,
            "restaurant": restaurant,
            "comments": rows,
            "pending": sum(1 for row in rows if not row.is_approved),
            "limits": limits_for(restaurant),
        },
    )


def owned_comment(db: Session, user: User, comment_id: int) -> ItemComment:
    comment = db.scalar(
        select(ItemComment).where(
            ItemComment.id == comment_id,
            ItemComment.restaurant_id == user.restaurant_id,
        )
    )
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Izoh topilmadi")
    return comment


@router.post("/comments/{comment_id}/approve", dependencies=[Depends(verify_csrf)])
def approve_comment(db: DbSession, user: AdminUser, comment_id: int):
    comment = owned_comment(db, user, comment_id)
    comment.is_approved = True
    db.commit()
    return RedirectResponse("/admin/comments", status.HTTP_303_SEE_OTHER)


@router.post("/comments/{comment_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_comment(db: DbSession, user: AdminUser, comment_id: int):
    db.delete(owned_comment(db, user, comment_id))
    db.commit()
    return RedirectResponse("/admin/comments", status.HTTP_303_SEE_OTHER)


@router.get("/menu/print")
def print_menu(request: Request, db: DbSession, user: AdminUser):
    """Qog'ozga chiqarish uchun menyu.

    Server tomonda PDF yasamaymiz: brauzerning "Chop etish -> PDF saqlash"
    funksiyasi shu sahifadan aynan shunday natija beradi va qo'shimcha
    kutubxona talab qilmaydi.
    """
    restaurant = get_restaurant(db, user)
    if not limits_for(restaurant).printable:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Chop etish uchun menyu To'liq tarifda mavjud",
        )

    categories = db.scalars(
        select(Category)
        .where(Category.restaurant_id == restaurant.id, Category.is_active.is_(True))
        .options(selectinload(Category.items))
        .order_by(Category.sort_order, Category.id)
    ).all()
    sections = [
        (category, [item for item in category.items if item.is_available])
        for category in categories
    ]
    return templates.TemplateResponse(
        request,
        "admin/menu_print.html",
        {
            "restaurant": restaurant,
            "sections": [(c, items) for c, items in sections if items],
        },
    )


@router.get("/qr")
def qr_page(request: Request, db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    return templates.TemplateResponse(
        request,
        "admin/qr.html",
        {"user": user, "restaurant": restaurant, "menu_url": qr.menu_url(restaurant.slug)},
    )


@router.get("/qr.png")
def qr_png(db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    return Response(
        qr.png_bytes(qr.menu_url(restaurant.slug)),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{restaurant.slug}-qr.png"'},
    )


@router.get("/qr.svg")
def qr_svg(db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    return Response(
        qr.svg_bytes(qr.menu_url(restaurant.slug)),
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'attachment; filename="{restaurant.slug}-qr.svg"'},
    )


# --- stollar --------------------------------------------------------------
#
# Har stolning o'z QR kodi bor: shunda afitsant buyurtma qaysi stoldan
# kelganini biladi. Kod tasodifiy, chunki manzilda stol raqami tursa
# (`/t/7`) restoran tashqarisidagi odam uni terib buyurtma bera olardi.


@router.get("/tables")
def tables_page(request: Request, db: DbSession, user: AdminUser):
    """Zal — bino kesim ko'rinishida.

    Ilgari bu ikki sahifa edi: qavat va bo'limlar `/admin/zones` da, stollar
    shu yerda. Ikkalasi bir-birini ko'rsatmasdi va egasi stol qaysi qavatda
    turganini hech qayerda ko'ra olmasdi.
    """
    restaurant = get_restaurant(db, user)
    rows = tables.list_for(db, restaurant.id)
    zones = areas.list_zones(db, restaurant.id)

    grouped: dict[int | None, list] = {None: []}
    for zone in zones:
        grouped[zone.id] = []
    for table in rows:
        grouped.setdefault(table.zone_id, []).append(table)

    # [(qavat, [(bo'lim, [stollar]), ...]), ...] — tepada yuqori qavat
    building = [
        (floor, [(zone, grouped.get(zone.id, [])) for zone in group])
        for floor, group in areas.by_floor(zones)
    ]

    return templates.TemplateResponse(
        request,
        "admin/tables.html",
        {
            "user": user,
            "restaurant": restaurant,
            "building": building,
            "loose": grouped.get(None, []),
            "tables": rows,
            "zones": zones,
            "kinds": list(TableKind),
            # Keyingi bo'sh qavat — "qavat qo'shish" formasi bo'sh kelmasin
            "next_floor": max((zone.floor for zone in zones), default=0) + 1,
        },
    )


@router.post("/tables", dependencies=[Depends(verify_csrf)])
def create_table(
    request: Request,
    db: DbSession,
    user: AdminUser,
    label: Annotated[str, Form()],
    kind: Annotated[str, Form()] = "stol",
    zone_id: Annotated[int | None, Form()] = None,
):
    try:
        tables.create(db, get_restaurant(db, user), label, kind, zone_id)
    except HTTPException as error:
        return form_failed(request, error, "/admin/tables")
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.post("/tables/bulk", dependencies=[Depends(verify_csrf)])
def create_tables_bulk(
    request: Request,
    db: DbSession,
    user: AdminUser,
    count: Annotated[int, Form()],
    kind: Annotated[str, Form()] = "stol",
    zone_id: Annotated[int | None, Form()] = None,
):
    try:
        tables.bulk_create(db, get_restaurant(db, user), count, kind, zone_id)
    except HTTPException as error:
        return form_failed(request, error, "/admin/tables")
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


# Bu ikkalasi `/tables/{table_id}` dan OLDIN turishi shart: FastAPI
# marshrutlarni tartib bo'yicha tekshiradi va "move" so'zi `table_id: int`
# ga tushmay 422 bo'lib qolardi.


@router.post("/tables/build", dependencies=[Depends(verify_csrf)])
def build_hall(
    request: Request,
    db: DbSession,
    user: AdminUser,
    floors: Annotated[int, Form()] = 1,
):
    """Bo'sh restoranda qavatlarni yasaydi. Stol yasamaydi.

    Ilgari "har qavatda nechta stol" ham so'ralardi va hamma qavatga bir
    xil son qo'yilardi. Amalda qavatlar bir xil emas: birida o'nta stol,
    boshqasida uchta divan, beshta xona va bitta VIP bo'lishi mumkin.
    Shuning uchun stollarni egasi har qavatga o'zi qo'shadi — o'sha yerda
    turini ham, raqamlashni ham o'zi tanlaydi.
    """
    restaurant = get_restaurant(db, user)
    lang = resolve_lang(request)
    try:
        for floor in range(1, max(1, min(floors, 5)) + 1):
            zone = areas.create_zone(
                db,
                restaurant,
                f"{floor_label(floor, lang)} · {t('zone_name_example', lang)}",
                sort_order=floor,
                floor=floor,
            )
    except HTTPException as error:
        return form_failed(request, error, "/admin/tables")
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.post("/tables/move", dependencies=[Depends(verify_csrf)])
def move_tables(
    db: DbSession,
    user: AdminUser,
    table_id: Annotated[list[int] | None, Form()] = None,
    zone_id: Annotated[str, Form()] = "",
):
    """Belgilangan stollarni bo'limga ko'chiradi.

    Butun bino bitta forma: har bo'limda o'z `zone_id` qiymatini olib
    keladigan tugma bor. Shuning uchun JS'siz ham ishlaydi — sudrab tashlash
    esa shu formani o'sha tugma bilan yuboradi, alohida marshrut kerak emas.
    """
    tables.move_many(db, user.restaurant_id, table_id or [], zone_id)
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.post("/tables/zone/{zone_id}/add", dependencies=[Depends(verify_csrf)])
def add_tables_to_zone(
    request: Request,
    db: DbSession,
    user: AdminUser,
    zone_id: int,
    count: Annotated[int, Form()] = 1,
    kind: Annotated[str, Form()] = "stol",
    start: Annotated[int | None, Form()] = None,
):
    """Bo'lim ichiga tez stol qo'shish.

    `start` — egasi tanlagan boshlanish raqami. Bo'sh qoldirilsa eng katta
    mavjud raqamdan davom etadi.
    """
    zone = areas.owned_zone(db, user.restaurant_id, zone_id)
    try:
        tables.add_next(db, get_restaurant(db, user), count, kind, zone.id, start)
    except HTTPException as error:
        return form_failed(request, error, "/admin/tables")
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.post("/tables/qr-pack", dependencies=[Depends(verify_csrf)])
async def download_qr_pack(
    request: Request,
    db: DbSession,
    user: AdminUser,
    style: Annotated[str, Form()] = qr_pack.QR_ONLY,
    position: Annotated[str, Form()] = "markaz",
    background: Annotated[UploadFile | None, File()] = None,
):
    """Butun binoning QR'lari — bitta arxivda.

    Ilgari egasi har stolni alohida yuklab olardi va brauzer fayllarni
    `qr (1).png` deb saqlab, qaysi biri qaysi stolniki ekanini yo'qotardi.

    POST, chunki egasi o'z fonini yuklashi mumkin va so'rov CSRF bilan
    himoyalanadi.
    """
    restaurant = get_restaurant(db, user)
    lang = resolve_lang(request)

    # Forma qiymatlariga ishonilmaydi: noma'lum ko'rinish yalang'och QR'ga
    # tushadi, aks holda tanlanmagan yo'l chaqirilib qolardi
    if style not in qr_pack.STYLES:
        style = qr_pack.QR_ONLY
    if position not in qr_pack.POSITIONS:
        position = "markaz"

    canvas = None
    if style == qr_pack.OWN_IMAGE and background is not None and background.filename:
        raw = await background.read(MAX_IMAGE_BYTES + 1)
        if len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Rasm hajmi 5 MB dan oshmasin"
            )
        try:
            canvas = qr_pack.prepare_background(raw)
        except qr_pack.TooNarrow as juda_ingichka:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(juda_ingichka))
        except (UnidentifiedImageError, OSError):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fayl rasm emas")

    archive = qr_pack.build(
        db,
        restaurant,
        lang=lang,
        style=style,
        background=canvas,
        position=position,
        hint=t("qr_card_hint", lang),
    )
    return Response(
        archive,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{qr_pack.filename(restaurant)}"'
        },
    )


@router.post("/tables/{table_id}", dependencies=[Depends(verify_csrf)])
def update_table(
    request: Request,
    db: DbSession,
    user: AdminUser,
    table_id: int,
    label: Annotated[str, Form()],
    kind: Annotated[str, Form()] = "stol",
    zone_id: Annotated[int | None, Form()] = None,
):
    table = tables.owned(db, user.restaurant_id, table_id)
    try:
        tables.update(db, table, label, kind, zone_id)
    except HTTPException as error:
        return form_failed(request, error, "/admin/tables")
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.post("/tables/{table_id}/code", dependencies=[Depends(verify_csrf)])
def refresh_table_code(db: DbSession, user: AdminUser, table_id: int):
    tables.regenerate_code(db, tables.owned(db, user.restaurant_id, table_id))
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.post("/tables/{table_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_table(db: DbSession, user: AdminUser, table_id: int):
    # Buyurtmalar qolaveradi: table_id bo'shaydi, lekin table_label nusxasi
    # saqlangani uchun tarixda "7" ko'rinib turadi
    db.delete(tables.owned(db, user.restaurant_id, table_id))
    db.commit()
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.get("/tables/print")
def print_tables(request: Request, db: DbSession, user: AdminUser):
    """Qirqib stollarga qo'yish uchun kartochkalar varaqi.

    QR'lar keshlanmagan `inline_svg` bilan yasaladi: bir yugurishda 30 tagacha
    turli kod chiqadi va ular keshni to'ldirib, foyda o'rniga zarar qilardi.
    """
    restaurant = get_restaurant(db, user)
    rows = tables.list_for(db, restaurant.id)
    return templates.TemplateResponse(
        request,
        "admin/tables_print.html",
        {
            "restaurant": restaurant,
            "cards": [
                (table, qr.inline_svg(qr.table_url(restaurant.slug, table.code)))
                for table in rows
            ],
        },
    )


@router.get("/tables/{table_id}/qr.png")
def table_qr_png(db: DbSession, user: AdminUser, table_id: int):
    restaurant = get_restaurant(db, user)
    table = tables.owned(db, restaurant.id, table_id)
    return Response(
        qr.png_bytes(qr.table_url(restaurant.slug, table.code)),
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{restaurant.slug}-stol-{table.label}.png"'
        },
    )


@router.get("/tables/{table_id}/qr.svg")
def table_qr_svg(db: DbSession, user: AdminUser, table_id: int):
    restaurant = get_restaurant(db, user)
    table = tables.owned(db, restaurant.id, table_id)
    return Response(
        qr.svg_bytes(qr.table_url(restaurant.slug, table.code)),
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f'attachment; filename="{restaurant.slug}-stol-{table.label}.svg"'
        },
    )


# --- xodimlar -------------------------------------------------------------


def owned_waiter(db: Session, user: User, staff_id: int) -> User:
    """Faqat SHU restoranning afitsanti.

    Rol ham tekshiriladi: aks holda egasi bu marshrutlar orqali o'z hisobini
    (yoki boshqa admin hisobini) o'chirib qo'ya olardi.
    """
    staff = db.scalar(
        select(User).where(
            User.id == staff_id,
            User.restaurant_id == user.restaurant_id,
            User.role == Role.waiter,
        )
    )
    if staff is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Xodim topilmadi")
    return staff


@router.get("/staff")
def staff_page(request: Request, db: DbSession, user: AdminUser):
    restaurant = get_restaurant(db, user)
    staff = db.scalars(
        select(User)
        .where(User.restaurant_id == restaurant.id, User.role == Role.waiter)
        .order_by(User.username)
    ).all()
    return templates.TemplateResponse(
        request,
        "admin/staff.html",
        {
            "user": user,
            "restaurant": restaurant,
            "staff": staff,
            "zones": areas.list_zones(db, restaurant.id),
            "tables": tables.list_for(db, restaurant.id),
            "assignment": {person.id: areas.assignment_of(db, person) for person in staff},
            # Faoliyat va baho hamma xodim uchun bittadan so'rovda olinadi:
            # har biriga alohida so'rov yuborish ro'yxatni sekinlashtirardi
            "activity": staff_svc.activity_for(db, restaurant.id, [p.id for p in staff]),
            "ratings": staff_svc.rating_summary(db, restaurant.id, [p.id for p in staff]),
            "blank_activity": staff_svc.BOSH_FAOLIYAT,
            "activity_days": staff_svc.ACTIVITY_DAYS,
            # Login butun tizimda yagona — slug bilan boshlangani band bo'lish
            # ehtimoli kam va kimga tegishliligi ham ko'rinib turadi
            "suggested": f"afitsant{len(staff) + 1}",
        },
    )


@router.get("/staff/{staff_id}")
def staff_detail(request: Request, db: DbSession, user: AdminUser, staff_id: int):
    """Bitta xodim: faoliyat tarixi va baholar.

    Ro'yxatda hammasini ko'rsatish sahifani o'qib bo'lmas holga solardi —
    tarix va baho tarixi bitta xodimga tegishli va shu yerda turadi.
    """
    restaurant = get_restaurant(db, user)
    person = staff_svc.owned_waiter(db, restaurant.id, staff_id)
    activity = staff_svc.activity_for(db, restaurant.id, [person.id])
    return templates.TemplateResponse(
        request,
        "admin/staff_detail.html",
        {
            "user": user,
            "restaurant": restaurant,
            "person": person,
            "activity": activity.get(person.id, staff_svc.BOSH_FAOLIYAT),
            "activity_days": staff_svc.ACTIVITY_DAYS,
            "orders": staff_svc.recent_orders(db, restaurant.id, person.id),
            "reviews": staff_svc.reviews_for(db, restaurant.id, person.id),
            "rating": staff_svc.rating_summary(db, restaurant.id, [person.id]).get(person.id),
        },
    )


@router.post("/staff/{staff_id}/review", dependencies=[Depends(verify_csrf)])
def review_staff(
    request: Request,
    db: DbSession,
    user: AdminUser,
    staff_id: int,
    rating: Annotated[int, Form()],
    note: Annotated[str, Form()] = "",
):
    restaurant = get_restaurant(db, user)
    person = staff_svc.owned_waiter(db, restaurant.id, staff_id)
    try:
        staff_svc.add_review(db, restaurant.id, person, rating=rating, note=note, author=user)
    except HTTPException as error:
        return form_failed(request, error, f"/admin/staff/{staff_id}")
    return RedirectResponse(f"/admin/staff/{staff_id}", status.HTTP_303_SEE_OTHER)


@router.post("/staff/{staff_id}/review/{review_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_staff_review(
    db: DbSession, user: AdminUser, staff_id: int, review_id: int
):
    restaurant = get_restaurant(db, user)
    staff_svc.owned_waiter(db, restaurant.id, staff_id)
    staff_svc.delete_review(db, restaurant.id, review_id)
    return RedirectResponse(f"/admin/staff/{staff_id}", status.HTTP_303_SEE_OTHER)


@router.post("/staff", dependencies=[Depends(verify_csrf)])
def create_staff(
    request: Request,
    db: DbSession,
    user: AdminUser,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    try:
        onboarding.create_waiter(db, get_restaurant(db, user), username, password)
    except HTTPException as error:
        return form_failed(request, error, "/admin/staff")
    return RedirectResponse("/admin/staff", status.HTTP_303_SEE_OTHER)


@router.post("/staff/{staff_id}/password", dependencies=[Depends(verify_csrf)])
def reset_staff_password(
    request: Request,
    db: DbSession,
    user: AdminUser,
    staff_id: int,
    password: Annotated[str, Form()],
):
    if len(password) < onboarding.MIN_PASSWORD_LENGTH:
        return form_failed(
            request,
            HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Parol kamida {onboarding.MIN_PASSWORD_LENGTH} belgidan iborat bo'lsin",
            ),
            "/admin/staff",
        )
    staff = owned_waiter(db, user, staff_id)
    staff.password_hash = hash_password(password)
    db.commit()
    return RedirectResponse("/admin/staff", status.HTTP_303_SEE_OTHER)


@router.post("/staff/{staff_id}/toggle", dependencies=[Depends(verify_csrf)])
def toggle_staff(db: DbSession, user: AdminUser, staff_id: int):
    staff = owned_waiter(db, user, staff_id)
    staff.is_active = not staff.is_active
    db.commit()
    return RedirectResponse("/admin/staff", status.HTTP_303_SEE_OTHER)


@router.post("/staff/{staff_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_staff(db: DbSession, user: AdminUser, staff_id: int):
    db.delete(owned_waiter(db, user, staff_id))
    db.commit()
    return RedirectResponse("/admin/staff", status.HTTP_303_SEE_OTHER)


# --- buyurtmalar tarixi ---------------------------------------------------


@router.get("/orders")
def orders_page(
    request: Request,
    db: DbSession,
    user: AdminUser,
    period: str = "hafta",
    start: str | None = None,
    end: str | None = None,
):
    """Egasi uchun tarix. Jonli taxta esa /zal da — u afitsantga ham ochiq."""
    restaurant = get_restaurant(db, user)
    first, last, preset = stats.resolve_range(period, start, end, 365)
    rows = orders.history(db, restaurant.id, first, last)
    done = [order for order in rows if order.status.value == "served"]

    return templates.TemplateResponse(
        request,
        "admin/orders.html",
        {
            "user": user,
            "restaurant": restaurant,
            "orders": rows,
            "presets": stats.PRESETS,
            "preset": preset,
            "start": first,
            "end": last,
            "served_count": len(done),
            # Summa faqat berilgan buyurtmalar bo'yicha — bekor qilingani
            # tushumga kirmaydi va uni hisobga qo'shish egani chalg'itardi
            "served_total": sum((order.total for order in done), start=0),
            "table_count": len(tables.list_for(db, restaurant.id)),
            "open_count": len(orders.open_orders(db, restaurant.id)),
        },
    )


# --- zal bo'limlari -------------------------------------------------------


@router.get("/zones")
def zones_page(user: AdminUser):
    """Bo'limlar endi "Zal" sahifasining ichida.

    Marshrut o'chirilmadi: eski xatcho'p va panel ichidagi havolalar 404
    bo'lib qolmasin. `POST /zones*` marshrutlari esa hamon kerak — yangi
    sahifa aynan ulardan foydalanadi.
    """
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.post("/zones", dependencies=[Depends(verify_csrf)])
def create_zone(
    request: Request,
    db: DbSession,
    user: AdminUser,
    name: Annotated[str, Form()],
    sort_order: Annotated[int, Form()] = 0,
    floor: Annotated[int, Form()] = 1,
    basement: Annotated[bool, Form()] = False,
):
    try:
        areas.create_zone(
            db,
            get_restaurant(db, user),
            name,
            sort_order,
            areas.signed_floor(floor, basement),
        )
    except HTTPException as error:
        return form_failed(request, error, "/admin/tables")
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.post("/zones/{zone_id}", dependencies=[Depends(verify_csrf)])
def update_zone(
    db: DbSession,
    user: AdminUser,
    zone_id: int,
    name: Annotated[str, Form()],
    sort_order: Annotated[int, Form()] = 0,
    floor: Annotated[int, Form()] = 1,
    basement: Annotated[bool, Form()] = False,
):
    areas.rename_zone(
        db,
        areas.owned_zone(db, user.restaurant_id, zone_id),
        name,
        sort_order,
        areas.signed_floor(floor, basement),
    )
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.post("/zones/{zone_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_zone(db: DbSession, user: AdminUser, zone_id: int):
    # Stollar qoladi, faqat bo'limsiz bo'lib qoladi — chop etilgan QR omon
    areas.delete_zone(db, areas.owned_zone(db, user.restaurant_id, zone_id))
    return RedirectResponse("/admin/tables", status.HTTP_303_SEE_OTHER)


@router.post("/staff/{staff_id}/area", dependencies=[Depends(verify_csrf)])
async def set_staff_area(request: Request, db: DbSession, user: AdminUser, staff_id: int):
    """Xodimning javobgarlik doirasi.

    Forma ko'p qiymatli katakchalardan iborat, shuning uchun `request.form()`
    orqali o'qiladi — FastAPI'ning `list[int]` shakli bo'sh tanlovda umuman
    kelmaydi va "hammasini olib tashlash" ishlamay qolardi.
    """
    staff = owned_waiter(db, user, staff_id)
    form = await request.form()
    zone_ids = [int(v) for v in form.getlist("zone_ids") if str(v).isdigit()]
    table_ids = [int(v) for v in form.getlist("table_ids") if str(v).isdigit()]
    areas.set_assignment(db, staff, zone_ids, table_ids)
    return RedirectResponse("/admin/staff", status.HTTP_303_SEE_OTHER)
