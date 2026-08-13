// Bildirishnoma.
//
// Afitsant buyurtmani SEZISHI kerak — shovqinli zalda, qo'lida laganda,
// telefon cho'ntakda. Shuning uchun bu yerda hamma narsa eng kuchli
// holatga qo'yilgan: uzun tebranish, ovoz va MAX muhimlik.
//
// Ilgari ilova ochiq turganda ovoz ATAYLAB o'chirilgan edi ("taxta o'zi
// yangilanadi, chalg'itmaylik"). Amalda esa afitsant taxtani ochiq tutib
// yuradi va aynan o'sha paytda bildirishnoma jimgina kelardi — ya'ni eng
// kerak holatda eng kuchsiz bo'lardi. Endi ovoz doim chalinadi.
import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { Platform, Vibration } from "react-native";

import { api } from "./api";

// Uzun va uzuq-uzuq: qisqa "diq-diq" cho'ntakda sezilmaydi.
// [kutish, tebranish, tanaffus, tebranish, ...]
export const TEBRANISH = [0, 700, 300, 700, 300, 700];

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    // `shouldShowAlert` SDK 57 da eskirgan — o'rniga banner va ro'yxat
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

// Ilova ochiq turganda Android kanal tebranishini ishlatmaydi — uni o'zimiz
// chaqiramiz. Busiz taxta ochiq holatda faqat ovoz qolardi.
Notifications.addNotificationReceivedListener(() => {
  Vibration.vibrate(TEBRANISH);
});

function projectId() {
  return (
    Constants.expoConfig?.extra?.eas?.projectId ||
    Constants.easConfig?.projectId ||
    undefined
  );
}

/**
 * Ruxsat so'raydi va qurilmani serverga yozadi.
 *
 * Qaytadi: "granted" | "denied" | "unsupported"
 */
export async function enableNotifications() {
  // Emulyatorda push tokeni berilmaydi — foydalanuvchini chalg'itmaymiz
  if (!Device.isDevice) return "unsupported";

  if (Platform.OS === "android") {
    // Kanalsiz Android bildirishnomani jimgina ko'rsatadi: ovoz ham,
    // tebranish ham bo'lmaydi. Zalda buni hech kim sezmasdi.
    await Notifications.setNotificationChannelAsync("orders", {
      name: "Buyurtmalar",
      description: "Stoldan yangi buyurtma kelganda",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: TEBRANISH,
      enableVibrate: true,
      sound: "buyurtma.wav",
      lightColor: "#b45309",
      // Telefon qulflangan bo'lsa ham matn ko'rinsin: afitsant qaysi stol
      // ekanini ochmasdan biladi
      lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
      // "Muhim emas" deb yig'ib qo'yilmasin
      bypassDnd: false,
      showBadge: true,
    });
  }

  const current = await Notifications.getPermissionsAsync();
  let granted = current.granted;
  if (!granted && current.canAskAgain !== false) {
    const asked = await Notifications.requestPermissionsAsync();
    granted = asked.granted;
  }
  if (!granted) return "denied";

  const { data: expoToken } = await Notifications.getExpoPushTokenAsync({
    projectId: projectId(),
  });
  await api.registerDevice(expoToken, Platform.OS);
  return "granted";
}

export async function currentPermission() {
  if (!Device.isDevice) return "unsupported";
  const state = await Notifications.getPermissionsAsync();
  return state.granted ? "granted" : "denied";
}

/** Chiqishdan oldin qurilmani serverdan olib tashlaydi. */
export async function forgetThisDevice() {
  try {
    if (!Device.isDevice) return;
    const { data: expoToken } = await Notifications.getExpoPushTokenAsync({
      projectId: projectId(),
    });
    await api.forgetDevice(expoToken);
  } catch (err) {
    // Chiqishni bu to'xtatmasligi kerak. Server tomonda o'lik qurilma
    // baribir "DeviceNotRegistered" bo'yicha o'zi tozalanadi.
  }
}

/** Bildirishnoma bosilganda chaqiriladigan funksiyani ulaydi. */
export function onNotificationTap(handler) {
  const subscription = Notifications.addNotificationResponseReceivedListener(handler);
  return () => subscription.remove();
}
