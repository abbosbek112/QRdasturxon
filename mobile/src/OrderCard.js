import { StyleSheet, Text, View } from "react-native";

import { theme } from "./theme";
import { Button } from "./ui";

function money(value) {
  // Serverdagi `format_price` bilan bir xil: mingliklar orasida bo'shliq
  return String(Math.round(value)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

function age(iso, t) {
  const at = Date.parse(iso);
  if (Number.isNaN(at)) return "";
  const minutes = Math.floor((Date.now() - at) / 60000);
  return minutes < 1 ? t("hall_just_now") : t("hall_minutes_ago", { n: minutes });
}

export default function OrderCard({ order, t, currency, busy, onStatus }) {
  const fresh = order.status === "new";

  return (
    <View style={[styles.card, fresh && styles.cardNew]}>
      <View style={styles.head}>
        <View style={styles.table}>
          <Text style={styles.tableText}>{order.table}</Text>
        </View>
        {order.kind && order.kind !== "stol" ? (
          <View style={styles.kind}>
            <Text style={styles.kindText}>{t(`kind_${order.kind}`, { n: "" }).trim()}</Text>
          </View>
        ) : null}
        <Text style={styles.when}>{age(order.created_at, t)}</Text>
        {!fresh ? (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{t("order_status_accepted")}</Text>
          </View>
        ) : null}
      </View>

      {order.lines.map((line, index) => (
        <Text key={index} style={styles.line}>
          <Text style={styles.quantity}>{line.quantity}× </Text>
          {line.name}
        </Text>
      ))}

      {order.note ? <Text style={styles.note}>{order.note}</Text> : null}

      <Text style={styles.total}>
        {money(order.total)} {currency}
      </Text>

      <View style={styles.actions}>
        {fresh ? (
          <Button
            title={t("hall_accept")}
            kind="primary"
            busy={busy}
            onPress={() => onStatus(order.id, "accepted")}
            style={styles.action}
          />
        ) : null}
        <Button
          title={t("hall_serve")}
          busy={busy}
          onPress={() => onStatus(order.id, "served")}
          style={styles.action}
        />
        <Button
          title={t("hall_cancel")}
          kind="danger"
          busy={busy}
          onPress={() => onStatus(order.id, "cancelled")}
          style={styles.action}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.line,
    padding: 14,
    marginBottom: 12,
  },
  // Yangi buyurtma ko'zga darrov tashlansin — afitsant taxtaga uzoqdan qaraydi
  cardNew: { borderColor: theme.accent, borderWidth: 2 },

  head: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 10 },
  table: {
    minWidth: 46,
    height: 46,
    paddingHorizontal: 10,
    borderRadius: 12,
    backgroundColor: theme.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  tableText: { color: theme.accentInk, fontSize: 20, fontWeight: "800" },
  when: { color: theme.ink2, fontSize: 14, flex: 1 },
  kind: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: theme.radiusFull,
    backgroundColor: theme.surface2,
  },
  kindText: { color: theme.ink2, fontSize: 12, fontWeight: "700" },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.radiusFull,
    backgroundColor: "#eaf6ef",
  },
  badgeText: { color: theme.ok, fontSize: 12, fontWeight: "700" },

  line: { fontSize: 17, color: theme.ink, paddingVertical: 3 },
  quantity: { fontWeight: "800" },
  note: {
    marginTop: 8,
    padding: 10,
    borderRadius: 10,
    backgroundColor: theme.surface2,
    color: theme.ink,
    fontSize: 14,
  },
  total: { marginTop: 10, fontSize: 16, fontWeight: "700", color: theme.ink },

  actions: { flexDirection: "row", gap: 8, marginTop: 12 },
  action: { flex: 1 },
});
