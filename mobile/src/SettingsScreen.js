import Constants from "expo-constants";
import { useEffect, useState } from "react";
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { API_BASE, api } from "./api";
import { LANGUAGES } from "./i18n";
import { currentPermission, enableNotifications } from "./push";
import { theme } from "./theme";
import { Button, Notice } from "./ui";

const VERSION = Constants.expoConfig?.version || "1.0.0";

export default function SettingsScreen({ t, lang, onLang, onClose, onSignOut }) {
  const [permission, setPermission] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [update, setUpdate] = useState(null);

  useEffect(() => {
    currentPermission().then(setPermission);
    // Ilova do'kondan emas, saytdan tarqatiladi — yangilanish borligini
    // unga o'zimiz aytishimiz kerak, buni boshqa hech kim qilmaydi
    api
      .latest()
      .then((data) => {
        if (data && data.version && data.version !== VERSION) setUpdate(data);
      })
      .catch(() => {});
  }, []);

  async function turnOn() {
    setBusy(true);
    setMessage("");
    try {
      const state = await enableNotifications();
      setPermission(state);
      if (state === "denied") setMessage(t("app_notify_blocked"));
    } catch (err) {
      setMessage(t("offline"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.wrap}>
      <View style={styles.head}>
        <Text style={styles.title}>{t("nav_settings")}</Text>
        <Pressable onPress={onClose} accessibilityRole="button" style={styles.close}>
          <Text style={styles.closeText}>✕</Text>
        </Pressable>
      </View>

      {update ? (
        <View style={styles.block}>
          <Notice text={`${t("app_update")} — ${update.version}`} />
          <Button
            title={t("app_update_go")}
            kind="primary"
            onPress={() => Linking.openURL(update.page_url || update.apk_url)}
          />
        </View>
      ) : null}

      <View style={styles.block}>
        <Text style={styles.label}>{t("app_notify_on")}</Text>
        <Text style={styles.value}>
          {permission === "granted"
            ? t("app_notify_ready")
            : permission === "unsupported"
              ? "—"
              : t("app_notify_off")}
        </Text>
        {permission !== "granted" ? (
          <>
            <Text style={styles.hint}>{t("app_notify_why")}</Text>
            <Button title={t("app_notify_on")} busy={busy} onPress={turnOn} style={styles.gap} />
          </>
        ) : null}
        <Notice text={message} />
      </View>

      <View style={styles.block}>
        <Text style={styles.label}>Til</Text>
        <View style={styles.langs}>
          {Object.entries(LANGUAGES).map(([code, name]) => (
            <Pressable
              key={code}
              onPress={() => onLang(code)}
              style={[styles.lang, lang === code && styles.langOn]}
              accessibilityRole="button"
            >
              <Text style={[styles.langText, lang === code && styles.langTextOn]}>{name}</Text>
            </Pressable>
          ))}
        </View>
      </View>

      <View style={styles.block}>
        <Button title={t("sign_out")} kind="danger" onPress={onSignOut} />
      </View>

      <Text style={styles.foot}>
        {t("dl_version")} {VERSION}
        {"\n"}
        {API_BASE.replace(/^https?:\/\//, "")}
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  wrap: { padding: 16, paddingBottom: 40 },
  head: { flexDirection: "row", alignItems: "center", marginBottom: 16 },
  title: { flex: 1, fontSize: 24, fontWeight: "800", color: theme.ink },
  close: { padding: 8 },
  closeText: { fontSize: 20, color: theme.ink2 },

  block: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.line,
    padding: 14,
    marginBottom: 12,
  },
  label: { fontSize: 13, color: theme.ink2, marginBottom: 4 },
  value: { fontSize: 17, fontWeight: "700", color: theme.ink },
  hint: { fontSize: 13, color: theme.ink3, marginTop: 6, lineHeight: 19 },
  gap: { marginTop: 12 },

  langs: { flexDirection: "row", gap: 8, marginTop: 6 },
  lang: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: theme.radiusFull,
    borderWidth: 1,
    borderColor: theme.line,
    alignItems: "center",
  },
  langOn: { backgroundColor: theme.accent, borderColor: theme.accent },
  langText: { color: theme.ink, fontWeight: "600" },
  langTextOn: { color: theme.accentInk },

  foot: { textAlign: "center", color: theme.ink3, fontSize: 12, marginTop: 8, lineHeight: 18 },
});
