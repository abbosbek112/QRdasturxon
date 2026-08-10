// Bildirishnoma.
//
// Ilova ochiq turganda taxta o'zi yangilanadi va bildirishnoma ortiqcha —
// shuning uchun u faqat ilova fonda yoki yopiq bo'lganda ko'rsatiladi.
// Buyurtmani afitsant o'z ko'zi bilan ko'rib turgan bo'lsa, telefon
// jiringlab uni chalg'itishning ma'nosi yo'q.
import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { AppState, Platform } from "react-native";

import { api } from "./api";

Notifications.setNotificationHandler({
  handleNotification: async () => {
    const inForeground = AppState.currentState === "active";
    return {
      // `shouldShowAlert` SDK 57 da eskirgan — o'rniga banner va ro'yxat
      shouldShowBanner: !inForeground,
      shouldShowList: true,
      shouldPlaySound: !inForeground,
      shouldSetBadge: false,
    };
  },
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
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      sound: "default",
      lightColor: "#b45309",
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
