// Matnlar. Kalit nomlari `app/i18n.py` bilan ATAYLAB bir xil — shunda
// serverdagi va ilovadagi atama bitta bo'lib qoladi va tarjima chalkashmaydi.
import { getLocales } from "expo-localization";

export const LANGUAGES = { uz: "O'zbekcha", ru: "Русский", en: "English" };
export const DEFAULT_LANG = "uz";

const UI = {
  hall_title: { uz: "Buyurtmalar", ru: "Заказы", en: "Orders" },
  hall_empty: { uz: "Hozircha buyurtma yo'q", ru: "Заказов пока нет", en: "No orders yet" },
  hall_empty_text: {
    uz: "Stoldan buyurtma kelganda u shu yerda o'zi paydo bo'ladi.",
    ru: "Когда заказ придёт со стола, он появится здесь сам.",
    en: "When an order comes in from a table it will appear here on its own.",
  },
  hall_accept: { uz: "Qabul qildim", ru: "Принять", en: "Accept" },
  hall_serve: { uz: "Berildi", ru: "Подан", en: "Served" },
  hall_cancel: { uz: "Bekor qilish", ru: "Отменить", en: "Cancel" },
  hall_just_now: { uz: "hozirgina", ru: "только что", en: "just now" },
  hall_minutes_ago: { uz: "{n} daqiqa oldin", ru: "{n} мин назад", en: "{n} min ago" },

  order_table: { uz: "{n}-stol", ru: "Стол {n}", en: "Table {n}" },
  kind_stol: { uz: "{n}-stol", ru: "Стол {n}", en: "Table {n}" },
  kind_xona: { uz: "{n}-xona", ru: "Комната {n}", en: "Room {n}" },
  kind_divan: { uz: "{n}-divan", ru: "Диван {n}", en: "Sofa {n}" },
  kind_vip: { uz: "VIP {n}", ru: "VIP {n}", en: "VIP {n}" },
  hall_mine: { uz: "Mening bo'limim", ru: "Моя зона", en: "My area" },
  hall_all: { uz: "Hammasi", ru: "Все", en: "All" },
  order_status_accepted: { uz: "Qabul qilindi", ru: "Принят", en: "Accepted" },

  sign_in: { uz: "Kirish", ru: "Войти", en: "Sign in" },
  sign_out: { uz: "Chiqish", ru: "Выйти", en: "Sign out" },
  staff_login: { uz: "Login", ru: "Логин", en: "Username" },
  staff_password: { uz: "Parol", ru: "Пароль", en: "Password" },
  login_failed: { uz: "Login yoki parol noto'g'ri", ru: "Неверный логин или пароль", en: "Wrong username or password" },
  login_hint: {
    uz: "Restoran egangiz bergan login va parolni kiriting.",
    ru: "Введите логин и пароль, которые дал владелец ресторана.",
    en: "Enter the username and password your restaurant owner gave you.",
  },

  nav_settings: { uz: "Sozlamalar", ru: "Настройки", en: "Settings" },
  app_notify_on: { uz: "Bildirishnoma", ru: "Уведомления", en: "Notifications" },
  app_notify_ready: { uz: "Yoqilgan", ru: "Включены", en: "On" },
  app_notify_off: { uz: "O'chirilgan", ru: "Выключены", en: "Off" },
  app_notify_blocked: {
    uz: "Telefon sozlamalarida bildirishnoma taqiqlangan. Uni o'sha yerdan ochish kerak.",
    ru: "Уведомления запрещены в настройках телефона. Разрешить нужно там же.",
    en: "Notifications are blocked in the phone settings and have to be allowed there.",
  },
  app_notify_why: {
    uz: "Ilova yopiq bo'lsa ham yangi buyurtma haqida xabar beradi.",
    ru: "Сообщит о новом заказе, даже если приложение закрыто.",
    en: "It tells you about a new order even when the app is closed.",
  },
  dl_version: { uz: "Versiya", ru: "Версия", en: "Version" },
  app_update: { uz: "Yangi versiya bor", ru: "Есть новая версия", en: "A new version is out" },
  app_update_go: { uz: "Yuklab olish", ru: "Скачать", en: "Download" },

  offline: {
    uz: "Aloqa yo'q. Qayta urinilmoqda…",
    ru: "Нет связи. Повторяем попытку…",
    en: "No connection. Retrying…",
  },
  retry: { uz: "Qayta urinish", ru: "Повторить", en: "Retry" },
  loading: { uz: "Yuklanmoqda…", ru: "Загрузка…", en: "Loading…" },
};

export function deviceLang() {
  const codes = getLocales?.() || [];
  for (const entry of codes) {
    const code = (entry.languageCode || "").toLowerCase();
    if (LANGUAGES[code]) return code;
  }
  return DEFAULT_LANG;
}

export function makeT(lang) {
  return function t(key, replacements) {
    const entry = UI[key];
    let text = (entry && (entry[lang] || entry[DEFAULT_LANG])) || key;
    if (replacements) {
      for (const [name, value] of Object.entries(replacements)) {
        text = text.replace(`{${name}}`, String(value));
      }
    }
    return text;
  };
}
