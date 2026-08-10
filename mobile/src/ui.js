// Kichik umumiy bo'laklar. Alohida UI kutubxona qo'shilmagan: ilovada uchta
// ekran bor va ularga kerak bo'ladigan hamma narsa shu faylga sig'adi.
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { TOUCH_HEIGHT, theme } from "./theme";

export function Button({ title, onPress, kind = "plain", busy, disabled, style }) {
  const tone = {
    primary: { bg: theme.accent, fg: theme.accentInk, border: theme.accent },
    danger: { bg: theme.surface, fg: theme.danger, border: theme.line },
    plain: { bg: theme.surface, fg: theme.ink, border: theme.line },
  }[kind];

  const off = disabled || busy;
  return (
    <Pressable
      onPress={off ? undefined : onPress}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: tone.bg, borderColor: tone.border },
        pressed && !off && styles.pressed,
        off && styles.faded,
        style,
      ]}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!off }}
    >
      {busy ? (
        <ActivityIndicator color={tone.fg} />
      ) : (
        <Text style={[styles.buttonText, { color: tone.fg }]} numberOfLines={1}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

export function Notice({ text, tone = "warn" }) {
  if (!text) return null;
  return (
    <View style={[styles.notice, tone === "warn" ? styles.noticeWarn : styles.noticeOk]}>
      <Text style={styles.noticeText}>{text}</Text>
    </View>
  );
}

export function Empty({ title, text }) {
  return (
    <View style={styles.empty}>
      <Text style={styles.emptyTitle}>{title}</Text>
      {text ? <Text style={styles.emptyText}>{text}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: TOUCH_HEIGHT,
    paddingHorizontal: 16,
    borderRadius: theme.radiusFull,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonText: { fontSize: 16, fontWeight: "700" },
  pressed: { opacity: 0.75 },
  faded: { opacity: 0.5 },

  notice: {
    padding: 12,
    borderRadius: theme.radius,
    borderWidth: 1,
    marginBottom: 12,
  },
  noticeWarn: { backgroundColor: "#fdf3e7", borderColor: "#f0d5b0" },
  noticeOk: { backgroundColor: "#eaf6ef", borderColor: "#bfe3cd" },
  noticeText: { color: theme.ink, fontSize: 14, lineHeight: 20 },

  empty: { padding: 32, alignItems: "center" },
  emptyTitle: { fontSize: 17, fontWeight: "700", color: theme.ink, marginBottom: 6 },
  emptyText: { fontSize: 14, color: theme.ink2, textAlign: "center", lineHeight: 20 },
});
