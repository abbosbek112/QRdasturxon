// Kirish kaliti va til tanlovi.
//
// Kalit `expo-secure-store` da — AsyncStorage EMAS. AsyncStorage oddiy fayl:
// root qilingan yoki o'g'irlangan telefonda uni o'qib olish mumkin. SecureStore
// esa Android Keystore va iOS Keychain'ga tayanadi.
//
// Til esa maxfiy emas, lekin ikkinchi kutubxona qo'shmaslik uchun o'sha yerda.
import * as SecureStore from "expo-secure-store";

const TOKEN = "zal.token";
const LANG = "zal.lang";
const PLACE = "zal.restaurant";

async function read(key) {
  try {
    return await SecureStore.getItemAsync(key);
  } catch (err) {
    return null;
  }
}

async function write(key, value) {
  try {
    if (value === null) await SecureStore.deleteItemAsync(key);
    else await SecureStore.setItemAsync(key, value);
  } catch (err) {
    /* saqlanmasa ilova shu ochilishda baribir ishlaydi */
  }
}

export const session = {
  getToken: () => read(TOKEN),
  setToken: (value) => write(TOKEN, value),
  clearToken: () => write(TOKEN, null),

  getLang: () => read(LANG),
  setLang: (value) => write(LANG, value),

  getRestaurant: async () => {
    const raw = await read(PLACE);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      return null;
    }
  },
  setRestaurant: (value) => write(PLACE, value ? JSON.stringify(value) : null),
};
