from starlette.requests import Request

LANGUAGES: dict[str, str] = {"uz": "O'zbekcha", "ru": "Русский", "en": "English"}
DEFAULT_LANG = "uz"
LANG_COOKIE = "lang"

UI: dict[str, dict[str, str]] = {
    # --- mijoz menyusi ---
    "menu": {"uz": 'Menyu', "ru": 'Меню', "en": 'Menu'},
    "search_placeholder": {"uz": 'Taom qidirish...', "ru": 'Поиск блюда...', "en": 'Search dishes...'},
    "no_results": {"uz": 'Hech narsa topilmadi', "ru": 'Ничего не найдено', "en": 'Nothing found'},
    "empty_menu": {"uz": "Menyu hozircha bo'sh", "ru": 'Меню пока пустое', "en": 'The menu is empty for now'},
    "unavailable": {"uz": 'Mavjud emas', "ru": 'Нет в наличии', "en": 'Unavailable'},
    "popular": {"uz": 'Ommabop', "ru": 'Популярное', "en": 'Popular'},
    "all": {"uz": 'Hammasi', "ru": 'Все', "en": 'All'},
    "back": {"uz": 'Orqaga', "ru": 'Назад', "en": 'Back'},
    "ingredients": {"uz": 'Tarkibi', "ru": 'Состав', "en": 'Ingredients'},
    "close": {"uz": 'Yopish', "ru": 'Закрыть', "en": 'Close'},
    "allergens": {"uz": 'Allergenlar', "ru": 'Аллергены', "en": 'Allergens'},
    "wifi": {"uz": 'Wi-Fi', "ru": 'Wi-Fi', "en": 'Wi-Fi'},
    "spicy": {"uz": "O'tkir", "ru": 'Острое', "en": 'Spicy'},
    "vegetarian": {"uz": 'Vegetarian', "ru": 'Вегетарианское', "en": 'Vegetarian'},
    "todays_special": {"uz": 'Bugungi taklif', "ru": 'Предложение дня', "en": "Today's special"},
    "min": {"uz": 'daq', "ru": 'мин', "en": 'min'},
    "comments": {"uz": 'Izohlar', "ru": 'Отзывы', "en": 'Comments'},
    "no_comments": {"uz": "Hozircha izoh yo'q. Birinchi bo'ling.", "ru": 'Пока нет отзывов. Будьте первым.', "en": 'No comments yet. Be the first.'},
    "your_name": {"uz": 'Ismingiz', "ru": 'Ваше имя', "en": 'Your name'},
    "your_comment": {"uz": 'Fikringiz', "ru": 'Ваш отзыв', "en": 'Your comment'},
    "your_rating": {"uz": 'Bahoyingiz', "ru": 'Ваша оценка', "en": 'Your rating'},
    "rating": {"uz": 'Baho', "ru": 'Оценка', "en": 'Rating'},
    "send": {"uz": 'Yuborish', "ru": 'Отправить', "en": 'Send'},
    "comment_pending": {"uz": "Rahmat! Izohingiz restoran tasdiqlagach ko'rinadi.", "ru": 'Спасибо! Отзыв появится после проверки рестораном.', "en": 'Thank you! Your comment appears once the restaurant approves it.'},
    "contact": {"uz": 'Aloqa', "ru": 'Контакты', "en": 'Contact'},
    "address": {"uz": 'Manzil', "ru": 'Адрес', "en": 'Address'},
    "working_hours": {"uz": 'Ish vaqti', "ru": 'Часы работы', "en": 'Opening hours'},
    "restaurant_closed": {"uz": 'Bu restoran vaqtincha faol emas', "ru": 'Этот ресторан временно неактивен', "en": 'This restaurant is temporarily inactive'},
    "not_found": {"uz": 'Sahifa topilmadi', "ru": 'Страница не найдена', "en": 'Page not found'},
    # --- bosh sahifa ---
    "nav_how": {"uz": "Qanday ishlaydi", "ru": "Как это работает", "en": "How it works"},
    "nav_features": {"uz": "Imkoniyatlar", "ru": "Возможности", "en": "Features"},
    "nav_pricing": {"uz": "Narxlar", "ru": "Цены", "en": "Pricing"},
    "nav_contact": {"uz": "Aloqa", "ru": "Контакты", "en": "Contact"},
    "sign_in": {"uz": "Kirish", "ru": "Войти", "en": "Sign in"},
    "get_started": {"uz": "Boshlash", "ru": "Начать", "en": "Get started"},

    "hero_badge": {
        "uz": "{days} kun bepul \u00b7 karta so'ralmaydi",
        "ru": "{days} дней бесплатно \u00b7 карта не нужна",
        "en": "{days} days free \u00b7 no card required",
    },
    "hero_title_1": {"uz": "Kafengiz menyusi \u2014", "ru": "Меню вашего кафе \u2014", "en": "Your cafe menu \u2014"},
    "hero_title_2": {"uz": "mijoz telefonida", "ru": "в телефоне гостя", "en": "on your guest's phone"},
    "hero_lead": {
        "uz": "Stolga QR kod qo'yasiz, mijoz skanerlaydi \u2014 menyu telefonida ochiladi. "
              "Narx o'zgarsa bitta joyda tahrirlaysiz, qayta chop etish yo'q.",
        "ru": "Ставите QR-код на стол, гость сканирует \u2014 меню открывается в телефоне. "
              "Цена изменилась \u2014 правите в одном месте, перепечатывать ничего не нужно.",
        "en": "Put a QR code on the table, the guest scans it and the menu opens on their phone. "
              "When a price changes you edit it in one place \u2014 nothing gets reprinted.",
    },
    "hero_cta": {"uz": "Bepul boshlash", "ru": "Начать бесплатно", "en": "Start for free"},
    "hero_demo": {"uz": "Namunani ko'rish", "ru": "Посмотреть пример", "en": "See a sample"},
    "hero_fine": {
        "uz": "Kafe, qahvaxona va shirinlik do'konlari uchun \u00b7 Dastur o'rnatish shart emas",
        "ru": "Для кафе, кофеен и кондитерских \u00b7 Ничего устанавливать не нужно",
        "en": "For cafes, coffee shops and bakeries \u00b7 Nothing to install",
    },

    "steps_title": {"uz": "Uch qadam, bir kunda", "ru": "Три шага, один день", "en": "Three steps, one day"},
    "step1_title": {"uz": "Menyuni kiritasiz", "ru": "Вносите меню", "en": "Enter your menu"},
    "step1_text": {
        "uz": "Kategoriya, taom, narx va rasm. Uch tilda \u2014 mehmonlar uchun.",
        "ru": "Разделы, блюда, цены и фото. На трёх языках \u2014 для гостей.",
        "en": "Sections, dishes, prices and photos. In three languages, for your guests.",
    },
    "step2_title": {"uz": "QR kodni chop etasiz", "ru": "Печатаете QR-код", "en": "Print the QR code"},
    "step2_text": {
        "uz": "Tayyor QR kodni stolga qo'yasiz. SVG \u2014 istalgan o'lchamda aniq chiqadi.",
        "ru": "Готовый QR-код ставите на стол. SVG \u2014 чёткий в любом размере.",
        "en": "Put the ready QR code on the table. SVG stays sharp at any size.",
    },
    "step3_title": {
        "uz": "Menyuni istagancha o'zgartirasiz",
        "ru": "Меняете меню сколько угодно",
        "en": "Change the menu as often as you like",
    },
    "step3_text": {
        "uz": "QR kod o'sha-o'sha. Qayta chop etish hech qachon kerak bo'lmaydi.",
        "ru": "QR-код остаётся прежним. Перепечатывать больше не придётся.",
        "en": "The QR code stays the same. You never reprint it.",
    },

    "features_title": {"uz": "Ichkarida nima bor", "ru": "Что внутри", "en": "What's inside"},
    "features_sub": {"uz": "Aytib o'tirmaymiz \u2014 ko'rsatamiz.", "ru": "Не рассказываем \u2014 показываем.", "en": "We won't tell you \u2014 we'll show you."},

    "show_stats_kicker": {"uz": "Statistika", "ru": "Статистика", "en": "Statistics"},
    "show_stats_title": {
        "uz": "Qaysi taom ishlayapti \u2014 raqam bilan",
        "ru": "Какое блюдо работает \u2014 в цифрах",
        "en": "Which dish works \u2014 in numbers",
    },
    "show_stats_text": {
        "uz": "Menyu necha marta ochilgani kunma-kun ko'rinadi. Qaysi taom ko'proq "
              "qiziqtirgani ro'yxatda turadi. Kun, hafta, oy yoki o'zingiz tanlagan sana oralig'i bo'yicha.",
        "ru": "Сколько раз открывали меню \u2014 по дням. Какое блюдо смотрели чаще \u2014 в списке. "
              "За день, неделю, месяц или любой выбранный период.",
        "en": "How often the menu was opened, day by day. Which dishes drew the most interest, "
              "in a list. By day, week, month or any range you pick.",
    },
    "show_stats_note": {
        "uz": "Bu menyudan nima olib tashlash kerakligini ham ko'rsatadi.",
        "ru": "Это же показывает, что из меню пора убрать.",
        "en": "It also shows what to take off the menu.",
    },
    "stat_opens": {"uz": "Menyu ochilgan", "ru": "Открытий меню", "en": "Menu opens"},
    "stat_peak": {"uz": "Eng yuqori kun", "ru": "Лучший день", "en": "Best day"},
    "stat_rating": {"uz": "O'rtacha baho", "ru": "Средняя оценка", "en": "Average rating"},

    "show_themes_kicker": {"uz": "Uslublar", "ru": "Стили", "en": "Styles"},
    "show_themes_title": {
        "uz": "Menyu sizning ko'rinishingizda",
        "ru": "Меню в вашем стиле",
        "en": "A menu that looks like you",
    },
    "show_themes_text": {
        "uz": "Bitta bosishda butun menyu uslubi o'zgaradi \u2014 shrift, burchaklar, "
              "soyalar va rang birga. Keyin asosiy rangni o'zingizga moslaysiz.",
        "ru": "Один клик меняет весь стиль меню \u2014 шрифт, скругления, тени и цвет сразу. "
              "Потом подбираете основной цвет под себя.",
        "en": "One click changes the whole look \u2014 type, corners, shadows and colour together. "
              "Then you tune the accent colour to match your brand.",
    },
    "show_themes_note": {
        "uz": "Quyidagi to'rt karta \u2014 aynan menyudagi ko'rinish.",
        "ru": "Четыре карточки ниже \u2014 это ровно то, что видит гость.",
        "en": "The four cards below are exactly what the guest sees.",
    },

    "show_rating_kicker": {"uz": "Izoh va baho", "ru": "Отзывы и оценки", "en": "Reviews and ratings"},
    "show_rating_title": {
        "uz": "Mijoz fikri \u2014 lekin sizning ruxsatingiz bilan",
        "ru": "Отзыв гостя \u2014 но только с вашего согласия",
        "en": "Guest feedback \u2014 but only with your approval",
    },
    "show_rating_text": {
        "uz": "Mijoz taomga izoh qoldiradi va yulduz qo'yadi. Lekin u menyuda faqat "
              "siz tasdiqlaganingizdan keyin ko'rinadi.",
        "ru": "Гость оставляет отзыв и ставит звёзды. Но в меню это появится только "
              "после вашего подтверждения.",
        "en": "A guest leaves a comment and stars. It appears on the menu only after "
              "you approve it.",
    },
    "show_rating_note": {
        "uz": "Ya'ni \"yomon izoh chiqib qoladi\" degan xavotir yo'q.",
        "ru": "То есть переживать, что вылезет плохой отзыв, не нужно.",
        "en": "So there is no worry about a bad review slipping through.",
    },
    "badge_published": {"uz": "Menyuda", "ru": "В меню", "en": "Published"},
    "badge_waiting": {"uz": "Kutmoqda", "ru": "Ожидает", "en": "Waiting"},
    "show_comment_waiting": {
        "uz": "Bu izohni mijoz hali ko'rmayapti \u2014 qaroringizni kutyapti.",
        "ru": "Этот отзыв гость ещё не видит \u2014 он ждёт вашего решения.",
        "en": "Guests cannot see this one yet \u2014 it is waiting for your decision.",
    },

    "show_qr_kicker": {"uz": "QR kod", "ru": "QR-код", "en": "QR code"},
    "show_qr_title": {"uz": "Chop eting va stolga qo'ying", "ru": "Распечатайте и поставьте на стол", "en": "Print it and put it on the table"},
    "show_qr_text": {
        "uz": "QR kod tayyor holda beriladi. SVG \u2014 istalgan o'lchamda aniq chiqadi. "
              "Menyuni keyin necha marta o'zgartirsangiz ham QR kod o'sha-o'sha.",
        "ru": "QR-код выдаётся готовым. SVG \u2014 чёткий в любом размере. "
              "Сколько бы раз вы потом ни меняли меню, QR-код остаётся прежним.",
        "en": "The QR code comes ready to use. SVG stays sharp at any size, and however "
              "often you change the menu afterwards the code stays the same.",
    },
    "show_qr_note": {
        "uz": "Qog'oz menyu kerak bo'lsa \u2014 xuddi shu ma'lumotdan chop etiladi.",
        "ru": "Нужно бумажное меню \u2014 печатается из этих же данных.",
        "en": "Need a paper menu? It prints from the same data.",
    },
    "show_qr_scan": {
        "uz": "Telefoningiz bilan skanerlang \u2014 namuna menyu ochiladi",
        "ru": "Отсканируйте телефоном \u2014 откроется пример меню",
        "en": "Scan it with your phone \u2014 the sample menu opens",
    },

    "more_features": {"uz": "Yana nimalar bor", "ru": "Что ещё есть", "en": "What else there is"},
    "feat_wifi_title": {"uz": "Wi-Fi paroli menyuda", "ru": "Пароль от Wi-Fi в меню", "en": "Wi-Fi password in the menu"},
    "feat_wifi_text": {
        "uz": "Mijoz menyuni ochgan \u2014 paroli ham o'sha yerda. Kuniga o'nlab marta so'raladigan savol yopiladi.",
        "ru": "Гость открыл меню \u2014 пароль уже там. Вопрос, который задают десятки раз в день, закрыт.",
        "en": "The guest opens the menu and the password is right there. A question asked dozens of times a day, gone.",
    },
    "feat_lang_title": {"uz": "Uch tilli menyu", "ru": "Меню на трёх языках", "en": "A menu in three languages"},
    "feat_lang_text": {
        "uz": "Bir marta kiritasiz \u2014 mijoz o'z tilida ko'radi. Tarjima bo'lmasa o'zbekchasi chiqadi.",
        "ru": "Вносите один раз \u2014 гость видит на своём языке. Нет перевода \u2014 показывается узбекский.",
        "en": "Enter it once and the guest sees their own language. If a translation is missing, Uzbek is shown.",
    },
    "feat_marks_title": {"uz": "Taom belgilari", "ru": "Метки блюд", "en": "Dietary markers"},
    "feat_marks_text": {
        "uz": "Halol, o'tkir, vegetarian va allergen ma'lumoti. Mijoz so'ramaydi, xodim vaqti tejaladi.",
        "ru": "Халяль, острое, вегетарианское и аллергены. Гость не спрашивает, официант не тратит время.",
        "en": "Halal, spicy, vegetarian and allergens. Guests stop asking and staff save time.",
    },
    # --- bosh sahifa: narxlar va oxirgi chaqiriq ---
    "pricing_title": {"uz": "Qulay narxlar", "ru": "Удобные цены", "en": "Affordable pricing"},
    "pricing_sub": {
        "uz": "{days} kun bepul sinab ko'ring — karta so'ralmaydi. Oylik yoki yillik to'lang.",
        "ru": "Попробуйте {days} дней бесплатно — карта не нужна. Платите помесячно или за год.",
        "en": "Try it free for {days} days — no card needed. Pay monthly or yearly.",
    },
    "plan_tag_best": {"uz": "Tejamkor", "ru": "Выгодно", "en": "Best value"},
    "per_year": {"uz": "so'm/yil", "ru": "сум/год", "en": "UZS/year"},
    "per_month": {"uz": "so'm/oy", "ru": "сум/мес", "en": "UZS/mo"},
    "toggle_monthly": {"uz": "Oylik", "ru": "Помесячно", "en": "Monthly"},
    "toggle_yearly": {"uz": "Yillik", "ru": "Годовой", "en": "Yearly"},
    "yearly_savings": {"uz": "Tejaysiz", "ru": "Экономия", "en": "Save"},
    "plan_items": {"uz": "{n} ta taom", "ru": "{n} блюд", "en": "{n} dishes"},
    "plan_items_unlimited": {"uz": "Cheksiz taom", "ru": "Блюда без ограничений", "en": "Unlimited dishes"},
    "plan_categories": {"uz": "{n} ta kategoriya", "ru": "{n} раздела", "en": "{n} categories"},
    "plan_categories_unlimited": {"uz": "Cheksiz kategoriya", "ru": "Разделы без ограничений", "en": "Unlimited categories"},
    "plan_three_languages": {
        "uz": "Uch til (o'zbek, rus, ingliz)",
        "ru": "Три языка (узбекский, русский, английский)",
        "en": "Three languages (Uzbek, Russian, English)",
    },
    "plan_one_language": {"uz": "Faqat o'zbekcha", "ru": "Только узбекский", "en": "Uzbek only"},
    "plan_wifi_marks": {
        "uz": "Wi-Fi paroli va taom belgilari",
        "ru": "Пароль от Wi-Fi и метки блюд",
        "en": "Wi-Fi password and dietary markers",
    },
    "plan_stats": {"uz": "{n} kunlik statistika", "ru": "Статистика за {n} дней", "en": "{n} days of statistics"},
    "plan_specials": {"uz": "Bugungi taklif bo'limi", "ru": "Раздел «Блюдо дня»", "en": "Today's special section"},
    "plan_comments": {"uz": "Taomlarga mijoz izohlari", "ru": "Отзывы гостей о блюдах", "en": "Guest reviews on dishes"},
    "plan_print": {"uz": "Chop etish uchun menyu", "ru": "Меню для печати", "en": "A printable menu"},
    "plan_payment": {"uz": "To'lov \u2014 Telegram orqali", "ru": "Оплата \u2014 через Telegram", "en": "Payment via Telegram"},
    "plan_buy": {"uz": "Sotib olish", "ru": "Купить", "en": "Buy"},
    "plan_start_free": {"uz": "{days} kun bepul boshlash", "ru": "Начать: {days} дней бесплатно", "en": "Start free for {days} days"},

    "pay_how": {"uz": "To'lov qanday bo'ladi", "ru": "Как проходит оплата", "en": "How payment works"},
    "pay_step1": {
        "uz": "Ro'yxatdan o'tasiz \u2014 {days} kun hamma imkoniyat ochiq, karta so'ralmaydi",
        "ru": "Регистрируетесь \u2014 {days} дней всё открыто, карта не нужна",
        "en": "You sign up \u2014 {days} days with everything open, no card asked",
    },
    "pay_step2": {
        "uz": "Davom ettirmoqchi bo'lsangiz Telegramdan yozasiz",
        "ru": "Хотите продолжить \u2014 пишете в Telegram",
        "en": "If you want to continue, you write to us on Telegram",
    },
    "pay_step3": {
        "uz": "To'lovni o'tkazasiz \u2014 tarifingiz o'sha kuni ochiladi",
        "ru": "Переводите оплату \u2014 тариф открывается в тот же день",
        "en": "You send the payment and your plan opens the same day",
    },
    "pay_write": {"uz": "Telegramdan yozish", "ru": "Написать в Telegram", "en": "Write on Telegram"},

    "cta_kicker": {"uz": "Boshlash", "ru": "Начать", "en": "Get started"},
    "cta_title": {
        "uz": "Kechqurun stolda QR kod turadi",
        "ru": "К вечеру на столе будет QR-код",
        "en": "By tonight there is a QR code on the table",
    },
    "cta_text": {
        "uz": "Ro'yxatdan o'tish bir daqiqa. Menyuni kiritib, kechga QR kodni stolga qo'yasiz. "
              "Savol bo'lsa qo'ng'iroq qiling \u2014 menyuni kiritishda ham yordam beramiz.",
        "ru": "Регистрация занимает минуту. Вносите меню и к вечеру ставите QR-код на стол. "
              "Возникнут вопросы \u2014 позвоните, поможем и с внесением меню.",
        "en": "Signing up takes a minute. Enter the menu and by evening the QR code is on the "
              "table. If anything comes up, call us \u2014 we will help with the menu too.",
    },
    "cta_button": {"uz": "Kafemni ulash", "ru": "Подключить кафе", "en": "Connect my cafe"},
    # --- kirish va ro'yxatdan o'tish ---
    "login_title": {"uz": "Kirish", "ru": "Вход", "en": "Sign in"},
    "login_sub": {"uz": "Boshqaruv paneliga kirish", "ru": "Вход в панель управления", "en": "Sign in to the dashboard"},
    "field_login": {"uz": "Login", "ru": "Логин", "en": "Username"},
    "field_password": {"uz": "Parol", "ru": "Пароль", "en": "Password"},
    "forgot_password": {"uz": "Parolni unutdingizmi?", "ru": "Забыли пароль?", "en": "Forgot your password?"},
    "write_telegram": {"uz": "Telegramdan yozing", "ru": "Напишите в Telegram", "en": "Write to us on Telegram"},

    "signup_title": {"uz": "Ro'yxatdan o'tish", "ru": "Регистрация", "en": "Sign up"},
    "signup_sub": {
        "uz": "Restoraningizni ulang \u2014 {days} kun bepul, karta so'ralmaydi",
        "ru": "Подключите ресторан \u2014 {days} дней бесплатно, карта не нужна",
        "en": "Connect your restaurant \u2014 {days} days free, no card required",
    },
    "field_restaurant_name": {"uz": "Restoran nomi", "ru": "Название ресторана", "en": "Restaurant name"},
    "field_menu_address": {"uz": "Menyu manzili", "ru": "Адрес меню", "en": "Menu address"},
    "field_phone": {"uz": "Telefon", "ru": "Телефон", "en": "Phone"},
    "field_email_optional": {"uz": "Email (ixtiyoriy)", "ru": "Email (необязательно)", "en": "Email (optional)"},
    "password_hint": {"uz": "Kamida 8 belgi", "ru": "Минимум 8 символов", "en": "At least 8 characters"},
    "have_account": {"uz": "Hisobingiz bormi?", "ru": "Уже есть аккаунт?", "en": "Already have an account?"},
    "sign_in_link": {"uz": "Kiring", "ru": "Войдите", "en": "Sign in"},
    "signup_throttled": {
        "uz": "Juda ko'p urinish bo'ldi. Bir soatdan keyin qayta urinib ko'ring yoki biz bilan bog'laning.",
        "ru": "Слишком много попыток. Попробуйте через час или свяжитесь с нами.",
        "en": "Too many attempts. Try again in an hour or get in touch with us.",
    },

    # --- yopiq menyu (mijoz ko'radi) ---
    "closed_title": {"uz": "Menyu vaqtincha yopiq", "ru": "Меню временно закрыто", "en": "The menu is temporarily closed"},
    "closed_text": {
        "uz": "Uzr so'raymiz \u2014 buyurtmani xodimdan so'rasangiz bo'ladi.",
        "ru": "Приносим извинения \u2014 заказ можно сделать у официанта.",
        "en": "Sorry about that \u2014 you can order from the staff.",
    },
    # --- buyurtma: mijoz tomoni ---
    "order_table": {"uz": "{n}-stol", "ru": "Стол {n}", "en": "Table {n}"},
    # O'tirish joyi turlari. Mijoz "7-stol" yoki "VIP 2" deb ko'radi —
    # restoranda faqat stol bo'lmaydi.
    "kind_stol": {"uz": "{n}-stol", "ru": "Стол {n}", "en": "Table {n}"},
    "kind_xona": {"uz": "{n}-xona", "ru": "Комната {n}", "en": "Room {n}"},
    "kind_divan": {"uz": "{n}-divan", "ru": "Диван {n}", "en": "Sofa {n}"},
    "kind_vip": {"uz": "VIP {n}", "ru": "VIP {n}", "en": "VIP {n}"},
    "kind_stol_name": {"uz": "Stol", "ru": "Стол", "en": "Table"},
    "kind_xona_name": {"uz": "Xona", "ru": "Комната", "en": "Room"},
    "kind_divan_name": {"uz": "Divan", "ru": "Диван", "en": "Sofa"},
    "kind_vip_name": {"uz": "VIP xona", "ru": "VIP-комната", "en": "VIP room"},

    # --- zal bo'limlari ---
    "nav_zones": {"uz": "Bo'limlar", "ru": "Зоны", "en": "Areas"},
    "zones_title": {"uz": "Zal bo'limlari", "ru": "Зоны зала", "en": "Areas of the room"},
    "zones_sub": {
        "uz": "Zalni bo'limlarga ajratasiz: \"Asosiy zal\", \"VIP xonalar\", \"Terasa\". "
              "Afitsantlar shu bo'limlar bo'yicha taqsimlanadi.",
        "ru": "Разделите зал на зоны: «Основной зал», «VIP-комнаты», «Терраса». "
              "Официанты распределяются по этим зонам.",
        "en": "Split the room into areas: \"Main hall\", \"VIP rooms\", \"Terrace\". "
              "Waiters are then assigned to those areas.",
    },
    "zones_empty": {"uz": "Hali bo'lim yo'q", "ru": "Зон пока нет", "en": "No areas yet"},
    "zones_empty_text": {
        "uz": "Bo'lim bo'lmasa ham hammasi ishlaydi — barcha afitsant butun zalni ko'radi. "
              "Bo'lim bir nechta afitsant ishlaganda kerak bo'ladi.",
        "ru": "Без зон тоже всё работает — каждый официант видит весь зал. "
              "Зоны нужны, когда официантов несколько.",
        "en": "Everything works without areas too — every waiter sees the whole room. "
              "Areas start to matter once there is more than one waiter.",
    },
    "signup_username_hint": {
        "uz": "Panelga shu login bilan kirasiz. Brauzer bu maydonni o'zi "
              "to'ldirib qo'yishi mumkin — yuborishdan oldin tekshiring.",
        "ru": "С этим логином вы будете входить в панель. Браузер может "
              "заполнить поле сам — проверьте перед отправкой.",
        "en": "This is the login you will use for the dashboard. The browser "
              "may fill it in for you — check it before you submit.",
    },
    "zone_name": {"uz": "Bo'lim nomi", "ru": "Название зоны", "en": "Area name"},
    "zone_floor": {"uz": "Qavat", "ru": "Этаж", "en": "Floor"},
    "floor_n": {"uz": "{n}-qavat", "ru": "{n}-й этаж", "en": "Floor {n}"},
    "floor_basement": {"uz": "Yerto'la", "ru": "Подвал", "en": "Basement"},
    "floor_basement_n": {"uz": "{n}-yerto'la", "ru": "{n}-й подвал", "en": "Basement {n}"},
    "zone_tables": {"uz": "stol", "ru": "столов", "en": "tables"},
    "zone_none": {"uz": "Bo'limsiz", "ru": "Без зоны", "en": "No area"},
    "field_kind": {"uz": "Turi", "ru": "Тип", "en": "Type"},
    "field_zone": {"uz": "Bo'lim", "ru": "Зона", "en": "Area"},

    # --- afitsant javobgarligi ---
    "staff_area": {"uz": "Javobgarlik", "ru": "Зона ответственности", "en": "Responsibility"},
    "staff_area_all": {"uz": "Butun zal", "ru": "Весь зал", "en": "The whole room"},
    "staff_area_hint": {
        "uz": "Hech narsa tanlanmasa afitsant butun zalni ko'radi. Bir nechta "
              "afitsant bo'lsa har biriga o'z bo'limini bering — shunda "
              "bildirishnoma ham faqat o'ziga keladi.",
        "ru": "Если ничего не выбрано, официант видит весь зал. Когда официантов "
              "несколько, дайте каждому свою зону — тогда и уведомления придут "
              "только ему.",
        "en": "With nothing selected the waiter sees the whole room. Once there is "
              "more than one waiter, give each their own area — notifications then "
              "reach only them.",
    },
    "staff_area_extra": {"uz": "Alohida stollar", "ru": "Отдельные столы", "en": "Individual tables"},

    # --- taxtadagi filtr ---
    "hall_mine": {"uz": "Mening bo'limim", "ru": "Моя зона", "en": "My area"},
    "hall_all": {"uz": "Hammasi", "ru": "Все", "en": "All"},
    "order_add": {"uz": "Qo'shish", "ru": "Добавить", "en": "Add"},
    "order_cart": {"uz": "Savat", "ru": "Корзина", "en": "Cart"},
    "order_cart_empty": {"uz": "Savat bo'sh", "ru": "Корзина пуста", "en": "Your cart is empty"},
    "order_total": {"uz": "Jami", "ru": "Итого", "en": "Total"},
    "order_note": {
        "uz": "Izoh (masalan: piyozsiz)",
        "ru": "Комментарий (например: без лука)",
        "en": "Note (for example: no onion)",
    },
    "order_send": {"uz": "Buyurtma berish", "ru": "Заказать", "en": "Place order"},
    "order_clear": {"uz": "Tozalash", "ru": "Очистить", "en": "Clear"},
    "order_placed": {"uz": "Buyurtmangiz yuborildi", "ru": "Заказ отправлен", "en": "Your order has been sent"},
    "order_placed_text": {
        "uz": "Afitsant uni ko'radi va tez orada oldingizga keladi.",
        "ru": "Официант увидит его и скоро подойдёт к вам.",
        "en": "A waiter will see it and come over shortly.",
    },
    "order_number": {"uz": "Buyurtma", "ru": "Заказ", "en": "Order"},
    "order_back_to_menu": {"uz": "Menyuga qaytish", "ru": "Вернуться в меню", "en": "Back to the menu"},
    "order_status_new": {"uz": "Yuborildi", "ru": "Отправлен", "en": "Sent"},
    "order_status_accepted": {"uz": "Qabul qilindi", "ru": "Принят", "en": "Accepted"},
    "order_status_served": {"uz": "Berildi", "ru": "Подан", "en": "Served"},
    "order_status_cancelled": {"uz": "Bekor qilindi", "ru": "Отменён", "en": "Cancelled"},
    "order_cancelled_text": {
        "uz": "Afitsant bu buyurtmani bekor qildi. Sababi haqida undan so'rang.",
        "ru": "Официант отменил этот заказ. Спросите у него о причине.",
        "en": "The waiter cancelled this order. Please ask them why.",
    },
    "order_window_over": {"uz": "Buyurtma muddati tugadi", "ru": "Время заказа истекло", "en": "The ordering window has closed"},
    "order_window_over_text": {
        "uz": "Stoldagi QR kodni yana bir marta skanerlang — buyurtma qayta ochiladi.",
        "ru": "Отсканируйте QR-код на столе ещё раз — заказ снова откроется.",
        "en": "Scan the QR code on your table once more and ordering opens again.",
    },
    "order_scan_first": {
        "uz": "Buyurtma berish uchun stoldagi QR kodni skanerlang.",
        "ru": "Чтобы сделать заказ, отсканируйте QR-код на столе.",
        "en": "To place an order, scan the QR code on your table.",
    },

    # --- buyurtma: afitsant taxtasi ---
    "hall_title": {"uz": "Buyurtmalar", "ru": "Заказы", "en": "Orders"},
    "hall_empty": {"uz": "Hozircha buyurtma yo'q", "ru": "Заказов пока нет", "en": "No orders yet"},
    "hall_empty_text": {
        "uz": "Stoldan buyurtma kelganda u shu yerda o'zi paydo bo'ladi.",
        "ru": "Когда заказ придёт со стола, он появится здесь сам.",
        "en": "When an order comes in from a table it will appear here on its own.",
    },
    "hall_accept": {"uz": "Qabul qildim", "ru": "Принять", "en": "Accept"},
    "hall_serve": {"uz": "Berildi", "ru": "Подан", "en": "Served"},
    "hall_cancel": {"uz": "Bekor qilish", "ru": "Отменить", "en": "Cancel"},
    "hall_waiting": {"uz": "kutmoqda", "ru": "ожидает", "en": "waiting"},
    "hall_minutes_ago": {"uz": "{n} daqiqa oldin", "ru": "{n} мин назад", "en": "{n} min ago"},
    "hall_just_now": {"uz": "hozirgina", "ru": "только что", "en": "just now"},

    # --- ilova (PWA) ---
    "app_install": {"uz": "Ilovani o'rnatish", "ru": "Установить приложение", "en": "Install the app"},
    "app_install_why": {
        "uz": "Bosh ekranga qo'yiladi — manzil terish shart emas, to'liq ekranda ochiladi.",
        "ru": "Появится на главном экране — адрес вводить не нужно, откроется на весь экран.",
        "en": "It goes on your home screen — no address to type, opens full screen.",
    },
    "app_install_ios": {
        "uz": "iPhone'da: pastdagi \"Ulashish\" belgisini bosing, so'ng \"Bosh ekranga qo'shish\".",
        "ru": "На iPhone: нажмите значок «Поделиться» внизу, затем «На экран «Домой»».",
        "en": "On iPhone: tap the Share icon at the bottom, then \"Add to Home Screen\".",
    },
    "app_notify_on": {"uz": "Bildirishnomani yoqish", "ru": "Включить уведомления", "en": "Turn on notifications"},
    "app_notify_why": {
        "uz": "Telefon cho'ntakda bo'lsa ham yangi buyurtma bildiradi.",
        "ru": "Сообщит о новом заказе, даже если телефон в кармане.",
        "en": "It tells you about a new order even when the phone is in your pocket.",
    },
    "app_notify_ready": {"uz": "Bildirishnoma yoqilgan", "ru": "Уведомления включены", "en": "Notifications are on"},
    "app_notify_blocked": {
        "uz": "Bildirishnoma brauzer sozlamalarida taqiqlangan. Uni o'sha yerdan ochish kerak.",
        "ru": "Уведомления запрещены в настройках браузера. Разрешить нужно там же.",
        "en": "Notifications are blocked in the browser settings and have to be allowed there.",
    },
    "app_notify_ios": {
        "uz": "iPhone'da bildirishnoma faqat ilova bosh ekranga qo'shilgandan keyin ishlaydi.",
        "ru": "На iPhone уведомления работают только после добавления приложения на главный экран.",
        "en": "On iPhone notifications only work once the app has been added to the home screen.",
    },
    "app_new_order": {"uz": "Yangi buyurtma", "ru": "Новый заказ", "en": "New order"},
    "app_later": {"uz": "Keyinroq", "ru": "Позже", "en": "Later"},

    # --- ilovani yuklab olish sahifasi ---
    "dl_title": {"uz": "Afitsant ilovasi", "ru": "Приложение для официанта", "en": "The waiter app"},
    "dl_lead": {
        "uz": "Stollardan kelgan buyurtmalar telefoningizga tushadi. Ilova yopiq bo'lsa "
              "ham xabar beradi — brauzerni ochib o'tirish shart emas.",
        "ru": "Заказы со столов приходят на ваш телефон. Уведомление придёт, даже если "
              "приложение закрыто — открывать браузер не нужно.",
        "en": "Orders from the tables land on your phone. It tells you even when the app "
              "is closed, so there is no browser to keep open.",
    },
    "dl_android": {"uz": "Android uchun yuklab olish", "ru": "Скачать для Android", "en": "Download for Android"},
    "dl_ios": {"uz": "iPhone uchun o'rnatish", "ru": "Установить для iPhone", "en": "Install for iPhone"},
    "dl_size": {"uz": "hajmi", "ru": "размер", "en": "size"},
    "dl_version": {"uz": "Versiya", "ru": "Версия", "en": "Version"},
    "dl_protect_title": {
        "uz": "\"App blocked\" degan oyna chiqsa",
        "ru": "Если появится окно «App blocked»",
        "en": "If you see an \"App blocked\" dialog",
    },
    "dl_protect_text": {
        "uz": "Bu virus emas. Google bu ilovani birinchi marta ko'rayotgani uchun "
              "shunday deydi. \"More details\" ni bosing, ostidan \"Install anyway\" "
              "chiqadi — o'shani tanlang.",
        "ru": "Это не вирус. Google просто видит это приложение впервые. Нажмите "
              "«More details», ниже появится «Install anyway» — выберите его.",
        "en": "This is not a virus. Google is simply seeing this app for the first "
              "time. Tap \"More details\" and pick \"Install anyway\" underneath.",
    },
    "dl_android_how": {
        "uz": "Yuklab olgach faylni oching. Telefon \"noma'lum manbadan o'rnatishga\" "
              "ruxsat so'raydi — ruxsat bering, keyin \"O'rnatish\" ni bosing.",
        "ru": "После скачивания откройте файл. Телефон попросит разрешение на установку "
              "из неизвестного источника — разрешите и нажмите «Установить».",
        "en": "Open the file once it downloads. The phone asks for permission to install "
              "from an unknown source — allow it, then tap Install.",
    },
    "dl_ios_how": {
        "uz": "Havola TestFlight orqali ochiladi. Avval TestFlight ilovasini o'rnatasiz, "
              "so'ng u orqali \"Zal\" ilovasi o'rnatiladi.",
        "ru": "Ссылка откроется через TestFlight. Сначала установите TestFlight, затем "
              "через него — приложение «Zal».",
        "en": "The link opens through TestFlight. Install TestFlight first, then get the "
              "Zal app through it.",
    },
    "dl_ios_pwa": {
        "uz": "iPhone ilovasi hozircha tayyorlanmoqda. Shu paytgacha menyu manzilini "
              "Safari'da ochib, \"Ulashish\" → \"Bosh ekranga qo'shish\" qiling — ilova "
              "kabi ishlaydi.",
        "ru": "Приложение для iPhone готовится. А пока откройте адрес в Safari и выберите "
              "«Поделиться» → «На экран «Домой»» — работать будет как приложение.",
        "en": "The iPhone app is still being prepared. Until then open the address in "
              "Safari and pick Share → Add to Home Screen — it works like an app.",
    },
    "dl_soon": {"uz": "Tez orada", "ru": "Скоро", "en": "Coming soon"},
    "dl_scan": {
        "uz": "Telefoningizda ochish uchun skanerlang",
        "ru": "Отсканируйте, чтобы открыть на телефоне",
        "en": "Scan to open this on your phone",
    },
    "dl_login_note": {
        "uz": "Kirish uchun restoran egangiz bergan login va parolni ishlating.",
        "ru": "Для входа используйте логин и пароль, которые дал владелец ресторана.",
        "en": "Sign in with the username and password your restaurant owner gave you.",
    },

    # --- admin panel: navigatsiya va umumiy ---
    "nav_home": {"uz": "Bosh sahifa", "ru": "Главная", "en": "Home"},
    "nav_orders": {"uz": "Buyurtmalar", "ru": "Заказы", "en": "Orders"},
    "nav_tables": {"uz": "Stollar", "ru": "Столы", "en": "Tables"},
    "nav_staff": {"uz": "Xodimlar", "ru": "Сотрудники", "en": "Staff"},
    "nav_categories": {"uz": "Kategoriyalar", "ru": "Разделы", "en": "Categories"},
    "nav_items": {"uz": "Taomlar", "ru": "Блюда", "en": "Dishes"},
    "nav_stats": {"uz": "Statistika", "ru": "Статистика", "en": "Statistics"},
    "nav_comments": {"uz": "Izohlar", "ru": "Отзывы", "en": "Reviews"},
    "nav_qr": {"uz": "QR kod", "ru": "QR-код", "en": "QR code"},
    "nav_settings": {"uz": "Sozlamalar", "ru": "Настройки", "en": "Settings"},
    "sign_out": {"uz": "Chiqish", "ru": "Выйти", "en": "Sign out"},
    "action_save": {"uz": "Saqlash", "ru": "Сохранить", "en": "Save"},
    "action_add": {"uz": "Qo'shish", "ru": "Добавить", "en": "Add"},
    "action_delete": {"uz": "O'chirish", "ru": "Удалить", "en": "Delete"},
    "action_edit": {"uz": "Tahrirlash", "ru": "Изменить", "en": "Edit"},
    "action_show": {"uz": "Ko'rsatish", "ru": "Показать", "en": "Show"},
    "field_order": {"uz": "Tartib", "ru": "Порядок", "en": "Order"},
    "state_active": {"uz": "Faol", "ru": "Активен", "en": "Active"},
    "state_hidden": {"uz": "Yashirilgan", "ru": "Скрыто", "en": "Hidden"},

    # --- muddat ogohlantirishi ---
    "banner_closed_title": {"uz": "Menyungiz yopiq.", "ru": "Ваше меню закрыто.", "en": "Your menu is closed."},
    "banner_closed_text": {
        "uz": "QR kodni skanerlagan mijoz uni ko'rmayapti. Ma'lumotlaringiz joyida \u2014 "
              "to'lov tasdiqlangach o'sha zahoti ochiladi.",
        "ru": "Гость, отсканировавший QR-код, его не видит. Данные на месте \u2014 "
              "после подтверждения оплаты меню откроется сразу же.",
        "en": "Guests who scan the QR code cannot see it. Your data is safe \u2014 "
              "the menu opens the moment payment is confirmed.",
    },
    "banner_days_left": {"uz": "{n} kun qoldi.", "ru": "Осталось дней: {n}.", "en": "{n} days left."},
    "banner_days_text": {
        "uz": "Muddat tugagach menyu yopiladi \u2014 QR kodni skanerlagan mijoz uni ko'rmaydi. "
              "Davom ettirish uchun",
        "ru": "По окончании срока меню закроется \u2014 гость, отсканировавший QR-код, его не увидит. "
              "Чтобы продолжить,",
        "en": "When the period ends the menu closes \u2014 guests scanning the QR code will not see it. "
              "To continue,",
    },
    "trial_days_left_title": {
        "uz": "Sinov muddati: {n} kun qoldi.",
        "ru": "Пробный период: осталось дней \u2014 {n}.",
        "en": "Trial period: {n} days left.",
    },
    "trial_days_left_text": {
        "uz": "Hozir To'liq tarif imkoniyatlari ochiq. Muddat tugagach menyu yopiladi \u2014 "
              "QR kodni skanerlagan mijoz uni ko'rmaydi. Davom ettirish uchun",
        "ru": "Сейчас открыты все возможности полного тарифа. По окончании срока меню закроется \u2014 "
              "гость, отсканировавший QR-код, его не увидит. Чтобы продолжить,",
        "en": "All full-plan features are open right now. When the period ends the menu closes \u2014 "
              "guests scanning the QR code will not see it. To continue,",
    },

    # --- boshqaruv paneli ---
    "dash_open_menu": {"uz": "Menyuni ochish", "ru": "Открыть меню", "en": "Open the menu"},
    "dash_new_item": {"uz": "Yangi taom", "ru": "Новое блюдо", "en": "New dish"},
    "dash_opens_in": {"uz": "{n} kunda ochilgan", "ru": "Открытий за {n} дней", "en": "Opens in {n} days"},
    "dash_categories": {"uz": "Kategoriya", "ru": "Разделов", "en": "Categories"},
    "dash_items": {"uz": "Taom", "ru": "Блюд", "en": "Dishes"},
    "dash_hidden": {"uz": "Yashirilgan taom", "ru": "Скрытых блюд", "en": "Hidden dishes"},
    "dash_quick": {"uz": "Tez havolalar", "ru": "Быстрые ссылки", "en": "Quick links"},
    "dash_print_menu": {"uz": "Chop etish uchun menyu", "ru": "Меню для печати", "en": "Printable menu"},

    # --- kategoriyalar ---
    "cat_title": {"uz": "Kategoriyalar", "ru": "Разделы", "en": "Categories"},
    "cat_sub": {
        "uz": "Menyudagi bo'limlar. Tartib raqami kichigi yuqorida turadi.",
        "ru": "Разделы меню. Чем меньше номер порядка, тем выше раздел.",
        "en": "The sections of your menu. A smaller order number puts a section higher.",
    },
    "cat_new": {"uz": "Yangi kategoriya", "ru": "Новый раздел", "en": "New category"},
    "cat_existing": {"uz": "Mavjud kategoriyalar", "ru": "Существующие разделы", "en": "Existing categories"},
    "cat_show_in_menu": {"uz": "Menyuda ko'rsatilsin", "ru": "Показывать в меню", "en": "Show in the menu"},
    "cat_dish_count": {"uz": "{n} ta taom", "ru": "Блюд: {n}", "en": "{n} dishes"},
    "name_in": {"uz": "Nomi", "ru": "Название", "en": "Name"},

    # --- taomlar ---
    "items_title": {"uz": "Taomlar", "ru": "Блюда", "en": "Dishes"},
    "items_sub": {
        "uz": "Menyudagi barcha taomlar va ularning holati.",
        "ru": "Все блюда меню и их состояние.",
        "en": "Every dish on the menu and its state.",
    },
    "items_all": {"uz": "Hammasi", "ru": "Все", "en": "All"},
    "items_empty": {"uz": "Bu yerda hali taom yo'q", "ru": "Здесь пока нет блюд", "en": "No dishes here yet"},
    "items_empty_hint": {"uz": "Birinchi taomni qo'shing.", "ru": "Добавьте первое блюдо.", "en": "Add the first dish."},
    "col_name": {"uz": "Nomi", "ru": "Название", "en": "Name"},
    "col_category": {"uz": "Kategoriya", "ru": "Раздел", "en": "Category"},
    "col_price": {"uz": "Narx", "ru": "Цена", "en": "Price"},
    "col_state": {"uz": "Holat", "ru": "Состояние", "en": "State"},
    "state_in_menu": {"uz": "Menyuda", "ru": "В меню", "en": "In the menu"},

    # --- izohlar ---
    "comments_title": {"uz": "Izohlar", "ru": "Отзывы", "en": "Reviews"},
    "comments_sub": {
        "uz": "Izoh siz tasdiqlagandan keyingina menyuda ko'rinadi. "
              "Tasdiqlamaganingiz mijozga umuman ko'rinmaydi.",
        "ru": "Отзыв появляется в меню только после вашего подтверждения. "
              "Неподтверждённые гость не видит вовсе.",
        "en": "A review appears on the menu only after you approve it. "
              "Guests never see the ones you have not approved.",
    },
    "comments_empty": {"uz": "Hozircha izoh yo'q", "ru": "Отзывов пока нет", "en": "No reviews yet"},
    "action_approve": {"uz": "Tasdiqlash", "ru": "Подтвердить", "en": "Approve"},
    "state_waiting": {"uz": "Kutmoqda", "ru": "Ожидает", "en": "Waiting"},

    # --- QR ---
    "qr_title": {"uz": "QR kod", "ru": "QR-код", "en": "QR code"},
    "qr_sub": {
        "uz": "Stolga qo'yish uchun chop eting \u2014 mijoz skanerlab menyuni ochadi.",
        "ru": "Распечатайте и поставьте на стол \u2014 гость отсканирует и откроет меню.",
        "en": "Print it for the table \u2014 a guest scans it and the menu opens.",
    },
    "qr_hint": {
        "uz": "Chop etish uchun SVG'ni tanlang \u2014 u sifatini yo'qotmasdan istalgan o'lchamga kattalashadi.",
        "ru": "Для печати выбирайте SVG \u2014 он масштабируется без потери качества.",
        "en": "Pick SVG for printing \u2014 it scales to any size without losing quality.",
    },
    "qr_open": {"uz": "Ochish", "ru": "Открыть", "en": "Open"},

    # --- stollar (egasi) ---
    "tables_title": {"uz": "Stollar", "ru": "Столы", "en": "Tables"},
    "tables_sub": {
        "uz": "Har stolning o'z QR kodi bor — shunda afitsant buyurtma qaysi stoldan "
              "kelganini biladi.",
        "ru": "У каждого стола свой QR-код — официант видит, с какого стола пришёл заказ.",
        "en": "Every table gets its own QR code, so the waiter knows which table ordered.",
    },
    "tables_empty": {"uz": "Hali stol qo'shilmagan", "ru": "Столы ещё не добавлены", "en": "No tables yet"},
    "tables_bulk": {"uz": "Zalda nechta stol bor?", "ru": "Сколько столов в зале?", "en": "How many tables are in the room?"},
    "tables_bulk_action": {"uz": "Stollarni yasash", "ru": "Создать столы", "en": "Create tables"},
    "tables_bulk_hint": {
        "uz": "1 dan shu songacha raqamlanadi. Borlari o'z kodini saqlab qoladi — "
              "chop etilgan QR kodlar ishlayveradi.",
        "ru": "Нумерация от 1 до этого числа. Существующие сохраняют свой код — "
              "распечатанные QR-коды продолжат работать.",
        "en": "Numbered from 1 up to this number. Existing tables keep their code, so "
              "already printed QR codes keep working.",
    },
    "tables_one": {"uz": "Bitta stol qo'shish", "ru": "Добавить один стол", "en": "Add a single table"},
    "tables_label": {"uz": "Stol nomi", "ru": "Название стола", "en": "Table name"},
    "tables_label_hint": {
        "uz": "Faqat raqam yozing: 7. Turini yonidagi ro'yxatdan tanlaysiz — "
              "nomga \"VIP\" yoki \"stol\" so'zini qo'shish shart emas, "
              "mijoz uni baribir \"VIP 7\" deb ko'radi.",
        "ru": "Пишите только номер: 7. Тип выбирается в списке рядом — "
              "добавлять слово «VIP» или «стол» в название не нужно, гость "
              "всё равно увидит «VIP 7».",
        "en": "Just the number: 7. Pick the type from the list beside it — "
              "there is no need to put \"VIP\" or \"table\" in the name, the "
              "guest sees \"VIP 7\" either way.",
    },
    "tables_print": {"uz": "Chop etish uchun varaq", "ru": "Лист для печати", "en": "Printable sheet"},
    "tables_new_code": {"uz": "Kodni yangilash", "ru": "Обновить код", "en": "Refresh code"},
    "tables_new_code_hint": {
        "uz": "Eski QR o'sha zahoti ishlamay qoladi. QR rasmi tarqalib ketgan bo'lsa ishlating.",
        "ru": "Старый QR сразу перестанет работать. Пригодится, если фото кода разошлось.",
        "en": "The old QR stops working immediately. Use it if a photo of the code got around.",
    },
    "tables_scan_me": {"uz": "Skanerlang va buyurtma bering", "ru": "Отсканируйте и закажите", "en": "Scan to see the menu and order"},

    # --- Bino: qavat, bo'lim, stol ---
    #
    # Kalit ataylab `building_` bilan boshlanadi: `hall_` afitsant taxtasiga
    # tegishli va `hall_title` allaqachon "Buyurtmalar" degan ma'noda band.
    # Ilgari shu nom ikki marta ta'riflangan edi va Python lug'atida
    # keyingisi oldingisining ustiga yozib, taxta sarlavhasini buzgan.
    "building_title": {"uz": "Bino", "ru": "Здание", "en": "Building"},
    "hall_sub": {
        "uz": "Binongizni shu yerda yig'asiz: qavat, bo'lim, stol. Har stolning "
              "o'z QR kodi bor — afitsant buyurtma qaysi stoldan kelganini biladi.",
        "ru": "Здесь вы собираете своё здание: этаж, зона, стол. У каждого стола "
              "свой QR-код — официант видит, с какого стола пришёл заказ.",
        "en": "Build your building here: floor, area, table. Every table gets its "
              "own QR code, so the waiter knows which table ordered.",
    },
    "hall_start_title": {"uz": "Binoni yig'amiz", "ru": "Соберём здание", "en": "Let's build the building"},
    "hall_start_floors": {"uz": "Nechta qavat?", "ru": "Сколько этажей?", "en": "How many floors?"},
    "hall_start_tables": {"uz": "Har qavatda nechta stol?", "ru": "Сколько столов на этаже?", "en": "Tables per floor?"},
    "hall_start_action": {"uz": "Qavatlarni yasash", "ru": "Создать этажи", "en": "Create the floors"},
    "hall_start_hint": {
        "uz": "Har qavatga bitta bo'lim yasaladi. Stollarni keyin o'zingiz "
              "qo'shasiz — qavatlar bir xil emas va har birida stol, divan, "
              "xona soni boshqacha bo'ladi.",
        "ru": "На каждом этаже появится одна зона. Столы добавите сами — этажи "
              "разные, и на каждом своё количество столов, диванов и комнат.",
        "en": "Each floor gets one area. You add the seats yourself — floors "
              "differ, and each has its own mix of tables, sofas and rooms.",
    },
    "hall_add_floor": {"uz": "Qavat qo'shish", "ru": "Добавить этаж", "en": "Add a floor"},
    "hall_add_zone": {"uz": "Bo'lim qo'shish", "ru": "Добавить зону", "en": "Add an area"},
    "hall_add_zone_hint": {
        "uz": "Qavat bo'lim bilan tug'iladi: bo'sh qavat saqlanmaydi.",
        "ru": "Этаж появляется вместе с зоной: пустой этаж не сохраняется.",
        "en": "A floor is born with its area — an empty floor is not stored.",
    },
    "hall_add_tables": {"uz": "Stol qo'shish", "ru": "Добавить столы", "en": "Add tables"},
    "hall_move_here": {"uz": "Shu yerga ko'chirish", "ru": "Перенести сюда", "en": "Move here"},
    "hall_unassigned": {"uz": "Bo'limsiz stollar", "ru": "Столы без зоны", "en": "Tables without an area"},
    "hall_unassigned_hint": {
        "uz": "Bu stollar zalning biror bo'limiga tegishli emas. Afitsantga "
              "biriktirib bo'lmaydi — buyurtmasi hammaga ketadi.",
        "ru": "Эти столы не принадлежат ни одной зоне. Их нельзя закрепить за "
              "официантом — заказ уйдёт всем.",
        "en": "These tables belong to no area. They cannot be assigned to a waiter — "
              "their orders go to everyone.",
    },
    "hall_take_out": {"uz": "Bo'limdan chiqarish", "ru": "Убрать из зоны", "en": "Take out of the area"},
    "hall_selected": {"uz": "{n} ta belgilandi", "ru": "Выбрано: {n}", "en": "{n} selected"},
    "hall_clear": {"uz": "Bekor qilish", "ru": "Отменить", "en": "Clear"},
    "hall_pick_hint": {
        "uz": "Stolni bosib belgilang, keyin bo'limdagi \"Shu yerga ko'chirish\" "
              "tugmasini bosing. Kompyuterda stolni sudrab ham tashlash mumkin.",
        "ru": "Отметьте столы, затем нажмите «Перенести сюда» в нужной зоне. "
              "На компьютере стол можно и перетащить.",
        "en": "Tap tables to select them, then press \"Move here\" on an area. "
              "On a computer you can also drag a table across.",
    },
    "hall_zone_empty": {"uz": "Bu bo'limda stol yo'q", "ru": "В этой зоне нет столов", "en": "No tables in this area"},
    "hall_floor_empty": {"uz": "Bu qavatda bo'lim yo'q", "ru": "На этом этаже нет зон", "en": "No areas on this floor"},
    "hall_zone_count": {"uz": "{z} bo'lim · {t} stol", "ru": "зон: {z} · столов: {t}", "en": "{z} areas · {t} tables"},
    "hall_open_table": {"uz": "Stolni ochish", "ru": "Открыть стол", "en": "Open table"},
    "hall_start_from": {"uz": "Raqamlash", "ru": "Нумерация с", "en": "Numbering from"},
    "hall_start_from_hint": {
        "uz": "Qaysi raqamdan boshlansin. 1-qavatda 10 stol bo'lsa, 2-qavatnikini "
              "11 dan boshlashingiz mumkin — afitsant chalkashmaydi.",
        "ru": "С какого номера начать. Если на 1-м этаже 10 столов, на 2-м можно "
              "начать с 11 — официант не запутается.",
        "en": "Which number to start from. With 10 tables on floor 1, floor 2 can "
              "start at 11 — the waiter will not mix them up.",
    },
    "staff_login_hint": {
        "uz": "Login restoraningiz nomi bilan boshlanadi — uni tizim o'zi qo'shadi. "
              "Afitsantga to'liq loginni ayting.",
        "ru": "Логин начинается с названия вашего ресторана — система добавляет его сама. "
              "Сообщите официанту полный логин.",
        "en": "The login starts with your restaurant name — the system adds it. "
              "Give the waiter the full login.",
    },
    "zone_name_example": {"uz": "Asosiy zal", "ru": "Основной зал", "en": "Main room"},
    "zones_delete_keeps_tables": {
        "uz": "Stollar qoladi, faqat bo'limsiz bo'ladi.",
        "ru": "Столы останутся, просто окажутся без зоны.",
        "en": "The tables stay — they simply end up without an area.",
    },

    # --- xodimlar (egasi) ---
    "staff_title": {"uz": "Xodimlar", "ru": "Сотрудники", "en": "Staff"},
    "staff_sub": {
        "uz": "Afitsant o'z logini bilan kiradi va faqat buyurtmalar taxtasini ko'radi — "
              "menyu va narxlarga tega olmaydi.",
        "ru": "Официант входит под своим логином и видит только доску заказов — "
              "меню и цены ему недоступны.",
        "en": "A waiter signs in with their own login and sees only the order board — "
              "the menu and prices stay out of reach.",
    },
    "staff_empty": {"uz": "Hali afitsant qo'shilmagan", "ru": "Официанты ещё не добавлены", "en": "No waiters yet"},
    "staff_add": {"uz": "Afitsant qo'shish", "ru": "Добавить официанта", "en": "Add a waiter"},
    "staff_login": {"uz": "Login", "ru": "Логин", "en": "Username"},
    "staff_password": {"uz": "Parol", "ru": "Пароль", "en": "Password"},
    "staff_new_password": {"uz": "Yangi parol", "ru": "Новый пароль", "en": "New password"},
    "staff_reset": {"uz": "Parolni almashtirish", "ru": "Сменить пароль", "en": "Change password"},
    "staff_block": {"uz": "Bloklash", "ru": "Заблокировать", "en": "Block"},
    "staff_unblock": {"uz": "Blokdan chiqarish", "ru": "Разблокировать", "en": "Unblock"},
    "pw_show": {"uz": "Parolni ko'rsatish", "ru": "Показать пароль", "en": "Show password"},
    "pw_hide": {"uz": "Parolni yashirish", "ru": "Скрыть пароль", "en": "Hide password"},
    "pw_make": {"uz": "Parol yasash", "ru": "Сгенерировать", "en": "Generate"},
    "pw_copy": {"uz": "Nusxa olish", "ru": "Копировать", "en": "Copy"},
    "pw_copied": {"uz": "Nusxa olindi", "ru": "Скопировано", "en": "Copied"},
    "pw_cannot_show": {
        "uz": "Qo'yilgan parolni keyin ko'rsatib bo'lmaydi — u qaytmaydigan qilib "
              "shifrlangan. Unutsangiz shu yerdan yangisini qo'yasiz.",
        "ru": "Уже заданный пароль показать нельзя — он зашифрован необратимо. "
              "Если забыли, задайте здесь новый.",
        "en": "An existing password cannot be shown — it is hashed one-way. "
              "If it is forgotten, set a new one here.",
    },
    "staff_link_hint": {
        "uz": "Afitsant {url} manziliga o'z logini bilan kiradi.",
        "ru": "Официант заходит на {url} под своим логином.",
        "en": "The waiter signs in at {url} with their own login.",
    },

    # --- buyurtmalar tarixi (egasi) ---
    "orders_title": {"uz": "Buyurtmalar", "ru": "Заказы", "en": "Orders"},
    "orders_sub": {
        "uz": "Stoldan kelgan buyurtmalar tarixi.",
        "ru": "История заказов со столов.",
        "en": "The history of orders placed from tables.",
    },
    "orders_live": {"uz": "Jonli taxta", "ru": "Живая доска", "en": "Live board"},
    "orders_empty": {"uz": "Bu oraliqda buyurtma yo'q", "ru": "За этот период заказов нет", "en": "No orders in this range"},
    "orders_off": {"uz": "Buyurtma o'chirilgan", "ru": "Приём заказов выключен", "en": "Ordering is off"},
    "orders_off_text": {
        "uz": "Sozlamalardan yoqing, so'ng stollar uchun QR kod chop eting.",
        "ru": "Включите его в настройках, затем распечатайте QR-коды для столов.",
        "en": "Turn it on in settings, then print the QR codes for your tables.",
    },
    "orders_no_tables": {
        "uz": "Buyurtma yoqilgan, lekin stol qo'shilmagan — mijoz buyurtma bera olmaydi.",
        "ru": "Приём заказов включён, но столов нет — гость не сможет заказать.",
        "en": "Ordering is on but there are no tables yet, so guests cannot order.",
    },
    "field_orders_enabled": {"uz": "Menyudan buyurtma qabul qilish", "ru": "Принимать заказы из меню", "en": "Accept orders from the menu"},
    "field_order_window": {"uz": "Buyurtma oynasi (daqiqa)", "ru": "Окно заказа (минут)", "en": "Ordering window (minutes)"},
    "field_order_window_hint": {
        "uz": "QR skanerlangandan keyin shuncha daqiqa buyurtma berish mumkin. 0 — cheksiz. "
              "Bu havolani nusxalab tashqariga yuborishni to'xtatadi; tashqaridan kelgan "
              "buyurtmani esa afitsant tasdiqlamay rad etadi.",
        "ru": "Столько минут после сканирования можно заказывать. 0 — без ограничения. "
              "Это останавливает скопированную ссылку; заказ извне всё равно отклонит официант.",
        "en": "How long ordering stays open after a scan. 0 means no limit. It stops a copied "
              "link from being reused; an order from outside is still rejected by the waiter.",
    },
    "col_table": {"uz": "Stol", "ru": "Стол", "en": "Table"},
    "col_total": {"uz": "Summa", "ru": "Сумма", "en": "Total"},
    "col_status": {"uz": "Holat", "ru": "Статус", "en": "Status"},
    "col_time": {"uz": "Vaqt", "ru": "Время", "en": "Time"},

    # --- admin panel: qolgan matnlar ---
    "state_inactive": {"uz": "Faol emas", "ru": "Не активен", "en": "Inactive"},
    "setup_title": {"uz": "Menyuni ishga tushiramiz", "ru": "Запускаем меню", "en": "Let's get the menu running"},
    "setup_progress": {
        "uz": "{done} / {all} bajarildi \u2014 qolgan qadamlarni ketma-ket bajaring.",
        "ru": "Выполнено {done} из {all} \u2014 пройдите оставшиеся шаги по порядку.",
        "en": "{done} of {all} done \u2014 work through the remaining steps in order.",
    },
    "setup_hint": {
        "uz": "Uchalasi bajarilgach bu ro'yxat o'zi yo'qoladi va QR kodni chop etishga o'tasiz.",
        "ru": "Когда все три шага будут сделаны, список исчезнет сам, и вы перейдёте к печати QR-кода.",
        "en": "Once all three are done this list disappears and you move on to printing the QR code.",
    },
    "dash_opens_chart": {
        "uz": "Menyu ochilishi \u2014 oxirgi {n} kun",
        "ru": "Открытия меню \u2014 последние {n} дней",
        "en": "Menu opens \u2014 last {n} days",
    },
    "dash_peak_day": {"uz": "Eng yuqori kun: {n}", "ru": "Лучший день: {n}", "en": "Best day: {n}"},
    "dash_no_opens": {
        "uz": "Hozircha ochilish yo'q. QR kodni stolga qo'ygandan keyin bu yerda kunlik grafik chiqadi.",
        "ru": "Открытий пока нет. Поставьте QR-код на стол \u2014 и здесь появится график по дням.",
        "en": "No opens yet. Put the QR code on the table and a daily chart appears here.",
    },
    "dash_opens_hint": {
        "uz": "Bu \u2014 menyu necha marta ochilgani. Bir mijoz bir necha marta ochsa, har biri sanaladi.",
        "ru": "Это количество открытий меню. Если гость открыл несколько раз, считается каждое.",
        "en": "This counts menu opens. If one guest opens it several times, each one counts.",
    },
    "dash_top_items": {"uz": "Eng ko'p ochilgan taomlar", "ru": "Самые просматриваемые блюда", "en": "Most viewed dishes"},
    "times": {"uz": "marta", "ru": "раз", "en": "times"},

    # --- sozlamalar ---
    "settings_title": {"uz": "Restoran sozlamalari", "ru": "Настройки ресторана", "en": "Restaurant settings"},
    "settings_sub": {
        "uz": "Bu ma'lumotlar mijoz ko'radigan menyu sahifasining yuqorisida chiqadi.",
        "ru": "Эти данные показываются вверху страницы меню, которую видит гость.",
        "en": "This information appears at the top of the menu page your guests see.",
    },
    "settings_main": {"uz": "Asosiy", "ru": "Основное", "en": "Basics"},
    "settings_contact": {"uz": "Aloqa", "ru": "Контакты", "en": "Contact"},
    "settings_style": {"uz": "Menyu uslubi", "ru": "Стиль меню", "en": "Menu style"},
    "settings_images": {"uz": "Rasmlar", "ru": "Изображения", "en": "Images"},
    "field_description": {"uz": "Tavsif", "ru": "Описание", "en": "Description"},
    "field_hours": {"uz": "Ish vaqti", "ru": "Часы работы", "en": "Opening hours"},
    "field_address": {"uz": "Manzil", "ru": "Адрес", "en": "Address"},
    "field_accent": {"uz": "Asosiy rang", "ru": "Основной цвет", "en": "Accent colour"},
    "field_currency": {"uz": "Valyuta belgisi", "ru": "Обозначение валюты", "en": "Currency label"},
    "field_logo": {"uz": "Logo", "ru": "Логотип", "en": "Logo"},
    "field_cover": {"uz": "Muqova rasmi", "ru": "Обложка", "en": "Cover image"},

    # --- taom formasi ---
    "item_new": {"uz": "Yangi taom", "ru": "Новое блюдо", "en": "New dish"},
    "item_edit": {"uz": "Taomni tahrirlash", "ru": "Редактирование блюда", "en": "Edit dish"},
    "field_category": {"uz": "Kategoriya", "ru": "Раздел", "en": "Category"},
    "field_price": {"uz": "Narx", "ru": "Цена", "en": "Price"},
    "field_prep": {"uz": "Tayyorlanish vaqti (daqiqa)", "ru": "Время приготовления (мин)", "en": "Prep time (minutes)"},
    "field_ingredients": {"uz": "Tarkibi", "ru": "Состав", "en": "Ingredients"},
    "field_allergens": {"uz": "Allergenlar", "ru": "Аллергены", "en": "Allergens"},
    "field_image": {"uz": "Rasm", "ru": "Фото", "en": "Photo"},
    "mark_available": {"uz": "Menyuda ko'rsatilsin", "ru": "Показывать в меню", "en": "Show in the menu"},
    "mark_popular": {"uz": "Ommabop", "ru": "Популярное", "en": "Popular"},
    "mark_special": {"uz": "Bugungi taklif", "ru": "Блюдо дня", "en": "Today's special"},
    "mark_spicy": {"uz": "O'tkir", "ru": "Острое", "en": "Spicy"},
    "mark_vegetarian": {"uz": "Vegetarian", "ru": "Вегетарианское", "en": "Vegetarian"},
    # --- formalar va jadvallar ---
    "need_category_first": {"uz": "Avval kategoriya kerak", "ru": "Сначала нужен раздел", "en": "You need a category first"},
    "add_category": {"uz": "Kategoriya qo'shing", "ru": "Добавьте раздел", "en": "Add a category"},
    "no_categories_yet": {"uz": "Hali kategoriya yo'q", "ru": "Разделов пока нет", "en": "No categories yet"},
    "marks": {"uz": "Belgilar", "ru": "Метки", "en": "Markers"},
    "field_instagram": {"uz": "Instagram havolasi", "ru": "Ссылка на Instagram", "en": "Instagram link"},
    "field_telegram": {"uz": "Telegram havolasi", "ru": "Ссылка на Telegram", "en": "Telegram link"},
    "field_wifi_name": {"uz": "Tarmoq nomi", "ru": "Название сети", "en": "Network name"},
    "range_from": {"uz": "Boshlanishi", "ru": "Начало", "en": "From"},
    "range_to": {"uz": "Tugashi", "ru": "Конец", "en": "To"},
    "stat_days_picked": {"uz": "Kun tanlangan", "ru": "Дней выбрано", "en": "Days selected"},
    "stat_items_opened": {"uz": "Ochilgan taom", "ru": "Просмотрено блюд", "en": "Dishes opened"},
    "col_opened": {"uz": "Ochilgan", "ru": "Просмотров", "en": "Opens"},
    "col_share": {"uz": "Ulush", "ru": "Доля", "en": "Share"},
    "col_rating": {"uz": "Baho", "ru": "Оценка", "en": "Rating"},
    "col_average": {"uz": "O'rtacha", "ru": "Средняя", "en": "Average"},
    "col_votes": {"uz": "Baho soni", "ru": "Оценок", "en": "Ratings"},
    "stats_top_rated": {"uz": "Eng yuqori baholi taomlar", "ru": "Блюда с лучшими оценками", "en": "Best rated dishes"},
    "stats_none_opened": {"uz": "Bu oraliqda taom ochilmagan", "ru": "За этот период блюда не открывали", "en": "No dishes opened in this range"},
    "stats_no_ratings": {"uz": "Hali baho yo'q", "ru": "Оценок пока нет", "en": "No ratings yet"},
    # --- SEO: sahifa sarlavhalari ---
    "seo_landing_title": {
        "uz": "QRdasturxon \u2014 kafe va restoranlar uchun QR menyu",
        "ru": "QRdasturxon \u2014 QR-меню для кафе и ресторанов",
        "en": "QRdasturxon \u2014 QR menu for cafes and restaurants",
    },
    "seo_menu_title": {"uz": "{name} \u2014 menyu", "ru": "{name} \u2014 меню", "en": "{name} \u2014 menu"},
    "item_image_section": {"uz": "Rasm va ko'rinish", "ru": "Фото и вид", "en": "Photo and look"},
    "item_remove_image": {"uz": "Rasmni o'chirish", "ru": "Удалить фото", "en": "Remove photo"},
    "action_cancel": {"uz": "Bekor qilish", "ru": "Отмена", "en": "Cancel"},
}


def t(key: str, lang: str) -> str:
    """Interfeys matni.

    Kalit topilmasa kalitning o'zi qaytadi — sahifa yiqilmaydi, lekin
    yetishmayotgan tarjima ko'zga darrov tashlanadi.
    """
    entry = UI.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key


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
