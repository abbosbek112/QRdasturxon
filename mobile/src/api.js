// Server bilan aloqa.
//
// Manzil `app.json` dagi `extra.apiUrl` dan olinadi. Lokalda sinash uchun
// uni o'zgartirish shart emas — `EXPO_PUBLIC_API_URL` muhit o'zgaruvchisi
// ustunlik qiladi:
//
//   EXPO_PUBLIC_API_URL=http://192.168.1.5:8000 npx expo start
//
// (telefon `localhost` ni o'zining ichida qidiradi, shuning uchun
// kompyuterning tarmoqdagi IP manzili yoziladi)
import Constants from "expo-constants";

import { session } from "./session";

const BASE =
  process.env.EXPO_PUBLIC_API_URL ||
  Constants.expoConfig?.extra?.apiUrl ||
  "https://qrdasturxon.tech";

export const API_BASE = BASE.replace(/\/+$/, "");

// Tarmoq sekin bo'lsa ilova muzlab qolmasin — afitsant kutib turmaydi
const TIMEOUT = 12000;

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`);
    this.status = status;
  }
}

async function call(path, { method = "GET", body, token, auth = true } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT);

  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const key = token || (await session.getToken());
    if (key) headers.Authorization = `Bearer ${key}`;
  }

  try {
    const response = await fetch(API_BASE + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });

    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (err) {
      data = null; // server HTML qaytardi — pastda xato bo'lib chiqadi
    }

    if (!response.ok) {
      throw new ApiError(response.status, data && data.detail);
    }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  login: (username, password, device) =>
    call("/api/v1/login", {
      method: "POST",
      auth: false,
      body: { username, password, device },
    }),

  logout: () => call("/api/v1/logout", { method: "POST" }),

  orders: (showAll) => call("/api/v1/orders" + (showAll ? "?all=1" : "")),

  setStatus: (orderId, status) =>
    call(`/api/v1/orders/${orderId}/status`, { method: "POST", body: { status } }),

  registerDevice: (expoToken, platform) =>
    call("/api/v1/devices", {
      method: "POST",
      body: { expo_token: expoToken, platform },
    }),

  forgetDevice: (expoToken) =>
    call(`/api/v1/devices?expo_token=${encodeURIComponent(expoToken)}`, {
      method: "DELETE",
    }),

  latest: () => call("/api/v1/app/latest", { auth: false }),
};
