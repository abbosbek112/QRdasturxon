import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { ApiError, api } from "./api";
import { theme } from "./theme";
import { Button, Notice } from "./ui";

export default function LoginScreen({ t, onSignedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (busy || !username.trim() || !password) return;
    setBusy(true);
    setError("");
    try {
      const device = `${Platform.OS} ${Platform.Version}`;
      const data = await api.login(username.trim().toLowerCase(), password, device);
      await onSignedIn(data);
    } catch (err) {
      // Serverning o'z xabari aniqroq (cheklov, bloklangan hisob) — uni
      // ko'rsatamiz. Tarmoq uzilgan bo'lsa umumiy matn qoladi.
      setError(err instanceof ApiError ? err.message : t("offline"));
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.fill}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView contentContainerStyle={styles.wrap} keyboardShouldPersistTaps="handled">
        <Text style={styles.brand}>QRdasturxon</Text>
        <Text style={styles.title}>{t("hall_title")}</Text>

        <Notice text={error} />

        <Text style={styles.label}>{t("staff_login")}</Text>
        <TextInput
          style={styles.input}
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="username"
          returnKeyType="next"
          placeholder="afitsant1"
          placeholderTextColor={theme.ink3}
        />

        <Text style={styles.label}>{t("staff_password")}</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoCapitalize="none"
          autoComplete="current-password"
          returnKeyType="go"
          onSubmitEditing={submit}
        />

        <Button
          title={t("sign_in")}
          kind="primary"
          onPress={submit}
          busy={busy}
          disabled={!username.trim() || !password}
          style={styles.submit}
        />

        <Text style={styles.hint}>{t("login_hint")}</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  wrap: { padding: 24, paddingTop: 48, flexGrow: 1, justifyContent: "center" },
  brand: { fontSize: 15, fontWeight: "700", color: theme.accent, marginBottom: 4 },
  title: { fontSize: 28, fontWeight: "800", color: theme.ink, marginBottom: 24 },
  label: { fontSize: 13, color: theme.ink2, marginBottom: 6, marginTop: 12 },
  input: {
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.line,
    borderRadius: theme.radius,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 17,
    color: theme.ink,
  },
  submit: { marginTop: 24 },
  hint: { marginTop: 16, fontSize: 13, color: theme.ink3, lineHeight: 19 },
});
