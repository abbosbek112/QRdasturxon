import { useCallback, useEffect, useRef, useState } from "react";
import {
  AppState,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";

import OrderCard from "./OrderCard";
import { ApiError, api } from "./api";
import { dismissClosed, dismissOrder } from "./push";
import { theme } from "./theme";
import { Empty, Notice } from "./ui";

// Brauzer taxtasi bilan bir xil oraliq (`app/static/js/hall.js`)
const EVERY = 8000;

export default function BoardScreen({ t, restaurant, onSignedOut, onOpenSettings }) {
  const [orders, setOrders] = useState([]);
  const [showAll, setShowAll] = useState(false);
  const [hasArea, setHasArea] = useState(false);
  const [ready, setReady] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [offline, setOffline] = useState(false);
  const [busyId, setBusyId] = useState(null);

  // Ekrandan chiqib ketgandan keyin holat yangilanmasin
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  const load = useCallback(async () => {
    try {
      const data = await api.orders(showAll);
      if (!alive.current) return;
      const kelgan = data.orders || [];
      setOrders(kelgan);
      // Boshqa afitsant qabul qilgan bo'lsa uning bildirishnomasi bu
      // telefonda osilib qolmasin
      dismissClosed(kelgan.filter((o) => o.status === "new").map((o) => o.id));
      // Biriktirilmagan afitsantga tugma keraksiz — u baribir hammasini ko'radi
      setHasArea(!!data.has_area);
      setOffline(false);
    } catch (err) {
      if (!alive.current) return;
      // 401 — kalit bekor qilingan: egasi xodimni bloklagan yoki o'chirgan.
      // Bunda ilovada ushlab turishning ma'nosi yo'q, kirish ekraniga.
      if (err instanceof ApiError && err.status === 401) {
        onSignedOut();
        return;
      }
      setOffline(true);
    } finally {
      if (alive.current) setReady(true);
    }
  }, [onSignedOut, showAll]);

  useEffect(() => {
    load();
    const timer = setInterval(load, EVERY);

    // Telefon uyquga ketib qaytganda darrov yangilansin — afitsant
    // ekranni yoqqanda eski ro'yxatni ko'rmasin
    const watch = AppState.addEventListener("change", (state) => {
      if (state === "active") load();
    });

    return () => {
      clearInterval(timer);
      watch.remove();
    };
  }, [load]);

  async function setStatus(orderId, status) {
    if (busyId) return;
    setBusyId(orderId);

    // Buyurtmani darrov ro'yxatdan olib tashlaymiz: afitsant tugmani bosgach
    // javobni kutib turmasin va ikkinchi marta bosmasin
    const before = orders;
    setOrders((current) => current.filter((o) => o.id !== orderId));
    // Javob berildi — bildirishnoma ekranda turishining ma'nosi yo'q
    dismissOrder(orderId);

    try {
      const updated = await api.setStatus(orderId, status);
      if (updated && updated.status === "accepted") {
        // Qabul qilingan buyurtma taxtada qoladi, faqat holati o'zgaradi
        setOrders((current) =>
          [...current, updated].sort((a, b) =>
            a.created_at.localeCompare(b.created_at)
          )
        );
      }
    } catch (err) {
      setOrders(before); // amal o'tmadi — ro'yxatni qaytaramiz
      setOffline(true);
    } finally {
      setBusyId(null);
    }
  }

  async function pull() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  return (
    <View style={styles.fill}>
      <View style={styles.top}>
        <View style={styles.grow}>
          <Text style={styles.place} numberOfLines={1}>
            {restaurant?.name || "QRdasturxon"}
          </Text>
          <Text style={styles.subtitle}>{t("hall_title")}</Text>
        </View>
        <Pressable onPress={onOpenSettings} style={styles.gear} accessibilityRole="button">
          <Text style={styles.gearText}>⚙</Text>
        </Pressable>
      </View>

      {hasArea ? (
        <View style={styles.filter}>
          <Pressable
            onPress={() => setShowAll(false)}
            style={[styles.chip, !showAll && styles.chipOn]}
            accessibilityRole="button"
          >
            <Text style={[styles.chipText, !showAll && styles.chipTextOn]}>{t("hall_mine")}</Text>
          </Pressable>
          <Pressable
            onPress={() => setShowAll(true)}
            style={[styles.chip, showAll && styles.chipOn]}
            accessibilityRole="button"
          >
            <Text style={[styles.chipText, showAll && styles.chipTextOn]}>{t("hall_all")}</Text>
          </Pressable>
        </View>
      ) : null}

      <FlatList
        data={orders}
        keyExtractor={(order) => String(order.id)}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={pull} tintColor={theme.accent} />
        }
        ListHeaderComponent={offline ? <Notice text={t("offline")} /> : null}
        ListEmptyComponent={
          ready ? <Empty title={t("hall_empty")} text={t("hall_empty_text")} /> : null
        }
        renderItem={({ item }) => (
          <OrderCard
            order={item}
            t={t}
            currency={restaurant?.currency || ""}
            busy={busyId === item.id}
            onStatus={setStatus}
          />
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  top: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: theme.line,
    backgroundColor: theme.surface,
  },
  grow: { flex: 1 },
  place: { fontSize: 18, fontWeight: "800", color: theme.ink },
  subtitle: { fontSize: 13, color: theme.ink2 },
  gear: { padding: 8 },
  gearText: { fontSize: 22, color: theme.ink2 },
  list: { padding: 12, flexGrow: 1 },

  filter: { flexDirection: "row", gap: 8, paddingHorizontal: 12, paddingTop: 12 },
  chip: {
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: theme.radiusFull,
    borderWidth: 1,
    borderColor: theme.line,
    backgroundColor: theme.surface,
  },
  chipOn: { backgroundColor: theme.accent, borderColor: theme.accent },
  chipText: { color: theme.ink, fontWeight: "600" },
  chipTextOn: { color: theme.accentInk },
});
