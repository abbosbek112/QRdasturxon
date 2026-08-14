// Afitsant ilovasining service worker'i.
//
// Uchta vazifasi bor va boshqa hech narsa qilmaydi: qobiqni keshlaydi,
// bildirishnoma ko'rsatadi, bosilganda taxtani ochadi.
//
// MUHIM: buyurtma ma'lumoti hech qachon keshlanmaydi. Eskirgan buyurtmani
// ko'rsatish hech narsa ko'rsatmaslikdan yomonroq — afitsant allaqachon
// berilgan taomni yana olib kelardi. Shuning uchun sahifalar ham, /zal/list
// ham har doim tarmoqdan olinadi.

var CACHE = "zal-v1";

// Faqat versiyasiz murojaat qilinadigan fayllar. CSS va JS bu yerda YO'Q:
// ular manzilida ?v=... bilan keladi (`templating.py: _asset_version`), ya'ni
// versiyasi oldindan ma'lum emas. Ular birinchi muvaffaqiyatli yuklashda
// keshga tushadi va o'sha manzil bilan yotadi — yangi versiya chiqqanda
// manzil o'zgaradi, kesh o'zi chetlab o'tiladi.
var PRECACHE = ["/static/img/icon-192.png", "/static/favicon.svg"];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches
      .open(CACHE)
      .then(function (cache) {
        return cache.addAll(PRECACHE);
      })
      // Kesh to'lmasa ham ilova ishlayversin — u shunchaki tarmoqdan yuklaydi
      .catch(function () {})
      .then(function () {
        return self.skipWaiting();
      })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches
      .keys()
      .then(function (names) {
        return Promise.all(
          names.map(function (name) {
            if (name !== CACHE) return caches.delete(name);
          })
        );
      })
      .then(function () {
        return self.clients.claim();
      })
  );
});

// --- bildirishnoma --------------------------------------------------------
//
// Server MAZMUNSIZ turtki yuboradi va matn shu yerda yasaladi: buyurtma
// tafsiloti Google/Mozilla push serverlaridan o'tmasin. Worker `/zal/ping`
// dan joriy holatni o'zi so'raydi — u sessiya bilan himoyalangan, ya'ni
// faqat o'z restoranining ma'lumoti keladi.
self.addEventListener("push", function (event) {
  event.waitUntil(
    fetch("/zal/ping", { credentials: "include" })
      .then(function (res) {
        if (!res.ok) throw new Error("status " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (!data.new) return; // hammasi ko'rilgan — bezovta qilmaymiz
        return self.registration.showNotification(data.title, {
          body: data.text,
          icon: "/static/img/icon-192.png",
          badge: "/static/img/icon-192.png",
          // Bir xil belgi: ketma-ket buyurtmalar ekranni to'ldirib
          // yubormaydi, oxirgisi oldingisining o'rnini oladi
          tag: "zal-order",
          renotify: true,
          requireInteraction: true,
          // Uzun va uzuq-uzuq: qisqa titrash cho'ntakda sezilmaydi.
          // Ilovadagi naqsh bilan bir xil.
          vibrate: [0, 1000, 400, 1000, 400, 1000, 400, 1000],
          silent: false,
          data: { url: "/zal" },
        });
      })
      .catch(function () {
        // Sessiya tugagan yoki tarmoq yo'q — baribir xabar beramiz, aks
        // holda afitsant buyurtma kelganini umuman bilmay qolardi
        return self.registration.showNotification("QRdasturxon", {
          icon: "/static/img/icon-192.png",
          tag: "zal-order",
          data: { url: "/zal" },
        });
      })
  );
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var target = (event.notification.data && event.notification.data.url) || "/zal";

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then(function (windows) {
        // Ilova allaqachon ochiq bo'lsa yangisini ochmaymiz — afitsantda
        // o'nta bir xil oyna yig'ilib qolardi
        for (var i = 0; i < windows.length; i++) {
          if (windows[i].url.indexOf(target) !== -1 && "focus" in windows[i]) {
            return windows[i].focus();
          }
        }
        if (self.clients.openWindow) return self.clients.openWindow(target);
      })
  );
});

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;

  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.indexOf("/static/") !== 0) return;

  // Keshdan aynan shu manzil bo'yicha (?v= bilan birga) qidiriladi.
  // `ignoreSearch` ATAYLAB ishlatilmagan: u bilan yangilanishdan keyin ham
  // eski CSS berilaverardi va dizayn tuzatishlari afitsantga yetib bormasdi.
  event.respondWith(
    caches.match(request).then(function (hit) {
      if (hit) return hit;
      return fetch(request).then(function (response) {
        if (response && response.ok) {
          var copy = response.clone();
          caches.open(CACHE).then(function (cache) {
            cache.put(request, copy);
          });
        }
        return response;
      });
    })
  );
});
