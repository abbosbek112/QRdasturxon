// Afitsant ilovasi.
//
// Navigatsiya kutubxonasi ATAYLAB yo'q: ekran uchta va ular oddiy holat
// bilan almashadi. `expo-router` yoki `react-navigation` bu yerga uchta
// bog'liqlik va bir necha yuz kilobayt qo'shardi, evaziga hech narsa bermay.
import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, View } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";

import BoardScreen from "./src/BoardScreen";
import LoginScreen from "./src/LoginScreen";
import SettingsScreen from "./src/SettingsScreen";
import { api } from "./src/api";
import { DEFAULT_LANG, deviceLang, makeT } from "./src/i18n";
import { enableNotifications, forgetThisDevice, onNotificationTap } from "./src/push";
import { session } from "./src/session";
import { theme } from "./src/theme";

export default function App() {
  const [ready, setReady] = useState(false);
  const [token, setToken] = useState(null);
  const [restaurant, setRestaurant] = useState(null);
  const [lang, setLang] = useState(DEFAULT_LANG);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const t = makeT(lang);

  // Ochilishda: saqlangan kalit va til
  useEffect(() => {
    (async () => {
      const [saved, savedLang, place] = await Promise.all([
        session.getToken(),
        session.getLang(),
        session.getRestaurant(),
      ]);
      setToken(saved);
      setLang(savedLang || deviceLang());
      setRestaurant(place);
      setReady(true);
    })();
  }, []);

  // Bildirishnoma bosilganda sozlamalar oynasi ochiq bo'lsa yopamiz —
  // afitsant buyurtmani ko'rmoqchi, sozlamani emas
  useEffect(() => onNotificationTap(() => setSettingsOpen(false)), []);

  const signOut = useCallback(async () => {
    setSettingsOpen(false);
    // Serverga xabar berish SHART emas — kalit baribir mahalliy o'chadi.
    // Lekin urinib ko'ramiz: shunda telefon boshqa bildirishnoma olmaydi.
    await forgetThisDevice();
    try {
      await api.logout();
    } catch (err) {
      /* tarmoq yo'q — kalit serverda qoladi, lekin telefonda o'chadi */
    }
    await session.clearToken();
    await session.setRestaurant(null);
    setToken(null);
    setRestaurant(null);
  }, []);

  async function signedIn(data) {
    await session.setToken(data.token);
    await session.setRestaurant(data.restaurant);
    setToken(data.token);
    setRestaurant(data.restaurant);

    // Kirgandan keyin darrov so'raymiz: afitsant aynan shu daqiqada
    // ilovani ochib turibdi va nima uchun so'ralayotgani unga tushunarli
    enableNotifications().catch(() => {});
  }

  async function chooseLang(code) {
    setLang(code);
    await session.setLang(code);
  }

  if (!ready) {
    return (
      <View style={styles.splash}>
        <ActivityIndicator color={theme.accent} size="large" />
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <SafeAreaView style={styles.fill} edges={["top", "bottom"]}>
        {!token ? (
          <LoginScreen t={t} onSignedIn={signedIn} />
        ) : settingsOpen ? (
          <SettingsScreen
            t={t}
            lang={lang}
            onLang={chooseLang}
            onClose={() => setSettingsOpen(false)}
            onSignOut={signOut}
          />
        ) : (
          <BoardScreen
            t={t}
            restaurant={restaurant}
            onSignedOut={signOut}
            onOpenSettings={() => setSettingsOpen(true)}
          />
        )}
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1, backgroundColor: theme.page },
  splash: {
    flex: 1,
    backgroundColor: theme.page,
    alignItems: "center",
    justifyContent: "center",
  },
});
