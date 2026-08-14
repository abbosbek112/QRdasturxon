// Afitsant taxtasi: ro'yxatni o'zi yangilab turadi, yangi buyurtma kelganda
// ovoz beradi va bildirishnoma chiqaradi.
//
// Oddiy tortish (polling) ishlatiladi, uzun ulanish emas: bir necha ishchi
// jarayon va sinxron baza bilan SSE/WebSocket qo'shadigan murakkablik bu
// yerda o'zini oqlamaydi. Sakkiz soniyada bir kichik so'rov — planshet uchun
// sezilarsiz yuk.
(function () {
  var wrap = document.getElementById("hallWrap");
  if (!wrap) return;

  var EVERY = 8000;
  // Tanlangan ko'rinish (o'z bo'limi yoki hammasi) manzilda turadi
  var LIST_URL = wrap.dataset.listUrl || "/zal/list";
  var TITLE = document.title;
  var known = count();
  var busy = false;

  function count() {
    var list = document.getElementById("hallList");
    return list ? parseInt(list.dataset.new, 10) || 0 : 0;
  }

  function markTitle(n) {
    document.title = n ? "(" + n + ") " + TITLE : TITLE;
  }

  // "12 daqiqa oldin" — afitsant uchun soatdan foydaliroq: u qaysi stol
  // uzoq kutganini bir qarashda ko'radi. Matn serverdan keladi, ya'ni til
  // to'g'ri qoladi.
  var JUST_NOW = wrap.dataset.justNow || "";
  var AGO = wrap.dataset.ago || "";

  function stampAges() {
    var now = Date.now();
    var marks = wrap.querySelectorAll(".hall-when[data-since]");
    for (var i = 0; i < marks.length; i++) {
      var at = Date.parse(marks[i].dataset.since);
      if (isNaN(at)) continue;
      var minutes = Math.floor((now - at) / 60000);
      marks[i].textContent = minutes < 1 ? JUST_NOW : AGO.replace("{n}", minutes);
    }
  }

  // --- ovoz ---------------------------------------------------------------
  //
  // Ovoz fayl bilan emas, brauzerning o'zida yasaladi — qo'shimcha yuklash
  // ham, CSP uchun yangi manba ham kerak bo'lmaydi.
  //
  // AudioContext BITTA marta yasaladi va birinchi teginishda uyg'otiladi:
  // brauzer foydalanuvchi hech narsaga tegmaguncha ovozga ruxsat bermaydi va
  // ilgari signal shu sababdan jim qolardi.
  var audio = null;

  function wakeAudio() {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    try {
      if (!audio) audio = new Ctx();
      if (audio.state === "suspended") audio.resume();
    } catch (err) {
      /* ovoz bo'lmasa ham taxta ishlayveradi */
    }
  }

  // Ovoz va titrash. Ikkalasi ham ataylab uzun: zalda qisqa "biq" ham,
  // qisqa titrash ham sezilmaydi.
  //
  // Ilgari bitta 0.45 soniyalik sof sinus edi — u fon shovqiniga singib
  // ketardi. Endi ikki tonli, uch marta takrorlanadigan chaqiruv: quloq
  // bir xil tovushdan ko'ra o'zgarishni yaxshiroq ilg'aydi.
  var CHAQIRUV = [
    { gerts: 880, boshi: 0.00, davomi: 0.18 },
    { gerts: 1175, boshi: 0.20, davomi: 0.22 },
    { gerts: 880, boshi: 0.50, davomi: 0.18 },
    { gerts: 1175, boshi: 0.70, davomi: 0.22 },
    { gerts: 880, boshi: 1.00, davomi: 0.18 },
    { gerts: 1175, boshi: 1.20, davomi: 0.30 },
  ];

  function beep() {
    // Titrash ovozdan mustaqil: telefon jim rejimda bo'lsa ham sezilsin
    if (navigator.vibrate) {
      try {
        navigator.vibrate([0, 1000, 400, 1000, 400, 1000, 400, 1000]);
      } catch (err) {
        /* brauzer ruxsat bermadi */
      }
    }

    if (!audio || audio.state !== "running") return;
    try {
      CHAQIRUV.forEach(function (nota) {
        var osc = audio.createOscillator();
        var gain = audio.createGain();
        var t = audio.currentTime + nota.boshi;
        // Uchburchak to'lqin sof sinusdan o'tkirroq eshitiladi va
        // telefonning kichkina karnayida yo'qolib ketmaydi
        osc.type = "triangle";
        osc.frequency.value = nota.gerts;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.6, t + 0.01);
        gain.gain.setValueAtTime(0.6, t + nota.davomi - 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + nota.davomi);
        osc.connect(gain);
        gain.connect(audio.destination);
        osc.start(t);
        osc.stop(t + nota.davomi + 0.02);
      });
    } catch (err) {
      /* muhim emas */
    }
  }

  ["pointerdown", "keydown"].forEach(function (type) {
    document.addEventListener(type, wakeAudio, { once: true, passive: true });
  });

  // --- ekran o'chmasin ----------------------------------------------------
  //
  // Planshet devorga osilgan bo'lsa bu eng ko'p seziladigan qulaylik:
  // afitsant har safar ekranni yoqib o'tirmaydi.
  var lock = null;

  function holdScreen() {
    if (!navigator.wakeLock || document.hidden || lock) return;
    navigator.wakeLock.request("screen").then(
      function (got) {
        lock = got;
        got.addEventListener("release", function () {
          lock = null;
        });
      },
      function () {
        /* batareya kam yoki brauzer ruxsat bermadi — majburlamaymiz */
      }
    );
  }

  // --- bildirishnoma ------------------------------------------------------

  var NEW_ORDER = wrap.dataset.newOrder || "";

  function notify(n) {
    // Ilova ko'z oldida bo'lsa bildirishnoma ortiqcha — taxtaning o'zi ko'rinib turibdi
    if (!document.hidden) return;
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    try {
      var note = new Notification(NEW_ORDER, {
        body: wrap.dataset.newBody || "",
        icon: "/static/img/icon-192.png",
        badge: "/static/img/icon-192.png",
        tag: "zal-order", // ketma-ket buyurtmalar bir-birining ustiga tushsin
        renotify: true,
      });
      note.onclick = function () {
        window.focus();
        note.close();
      };
    } catch (err) {
      /* ba'zi brauzerlar konstruktorni sahifada taqiqlaydi — push bilan keladi */
    }
  }

  // --- yangilash ----------------------------------------------------------

  function refresh() {
    if (busy) return;
    busy = true;

    fetch(LIST_URL, { headers: { "X-Requested-With": "fetch" } })
      .then(function (res) {
        if (!res.ok) throw new Error("status " + res.status);
        return res.text();
      })
      .then(function (html) {
        // Afitsant tugma bosayotgan bo'lsa ro'yxatni tortib olmaymiz —
        // qo'l ostidan almashgan tugma noto'g'ri buyurtmani yopib qo'yardi
        if (document.activeElement && wrap.contains(document.activeElement)) return;

        wrap.innerHTML = html;
        stampAges();
        var now = count();
        if (now > known) {
          beep();
          notify(now);
        }
        known = now;
        markTitle(now);
      })
      .catch(function () {
        /* tarmoq uzildi — keyingi urinishda o'zi tiklanadi */
      })
      .then(function () {
        busy = false;
      });
  }

  markTitle(known);
  stampAges();
  holdScreen();
  setInterval(refresh, EVERY);
  // Yosh har daqiqada o'zi o'sib borsin — ro'yxat tortilishini kutmasdan
  setInterval(stampAges, 30000);

  // Planshet uyquga ketib qaytganda darrov yangilansin va qulf tiklansin
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) return;
    holdScreen();
    refresh();
  });
})();

// Ilova qobig'i: service worker, o'rnatish taklifi va bildirishnoma ruxsati.
(function () {
  var standalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;

  // iOS'da o'rnatish tugmasi yo'q — foydalanuvchi buni qo'lda qiladi va
  // unga aynan qayerni bosishni aytish kerak.
  var isIOS =
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

  var ready = null;
  if ("serviceWorker" in navigator) {
    ready = navigator.serviceWorker.register("/sw.js").then(
      function () {
        return navigator.serviceWorker.ready;
      },
      function () {
        /* ro'yxatdan o'tmasa taxta oddiy sahifa bo'lib ishlayveradi */
        return null;
      }
    );
  }

  var board = document.getElementById("hallWrap");
  var VAPID = board ? board.dataset.vapid || "" : "";
  var CSRF = board ? board.dataset.csrf || "" : "";

  // Brauzer base64url kutmaydi — xom baytlar kerak
  function keyBytes(text) {
    var padded = (text + "===").slice(0, text.length + ((4 - (text.length % 4)) % 4));
    var raw = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
    var out = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }

  function keyOf(subscription, name) {
    var raw = subscription.getKey(name);
    if (!raw) return "";
    var bytes = new Uint8Array(raw);
    var text = "";
    for (var i = 0; i < bytes.length; i++) text += String.fromCharCode(bytes[i]);
    return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function subscribe() {
    if (!ready || !VAPID) return Promise.resolve(false);

    return ready
      .then(function (reg) {
        if (!reg || !reg.pushManager) return null;
        // Mavjud obuna bo'lsa qaytadan yasamaymiz — serverga uni yana
        // yozib qo'yish yetarli (endpoint yagona, yozuv ko'paymaydi)
        return reg.pushManager.getSubscription().then(function (existing) {
          if (existing) return existing;
          return reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: keyBytes(VAPID),
          });
        });
      })
      .then(function (subscription) {
        if (!subscription) return false;
        var body = new URLSearchParams({
          csrf_token: CSRF,
          endpoint: subscription.endpoint,
          p256dh: keyOf(subscription, "p256dh"),
          auth: keyOf(subscription, "auth"),
        });
        return fetch("/zal/push/subscribe", { method: "POST", body: body }).then(
          function (res) {
            return res.ok;
          }
        );
      })
      .catch(function () {
        return false;
      });
  }

  // Ruxsat allaqachon berilgan bo'lsa obunani jimgina tiklaymiz: brauzer
  // ma'lumotini tozalasa yoki obuna eskirsa afitsant hech narsa qilmasdan
  // bildirishnomasiz qolib ketardi
  if ("Notification" in window && Notification.permission === "granted") {
    subscribe();
  }

  var HIDDEN = "qrd:hidden:";

  function dismissed(key) {
    try {
      return localStorage.getItem(HIDDEN + key) === "1";
    } catch (err) {
      return false;
    }
  }

  function dismiss(key) {
    try {
      localStorage.setItem(HIDDEN + key, "1");
    } catch (err) {
      /* muhim emas */
    }
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest ? event.target.closest("[data-app-dismiss]") : null;
    if (!button) return;
    var key = button.dataset.appDismiss;
    dismiss(key);
    var bar = button.closest(".app-bar");
    if (bar) bar.hidden = true;
  });

  // --- o'rnatish ----------------------------------------------------------

  var bar = document.getElementById("installBar");
  var go = document.getElementById("installGo");
  var text = document.getElementById("installText");
  var waiting = null;

  function showInstall() {
    if (!bar || standalone || dismissed("install")) return;
    bar.hidden = false;
  }

  if (bar && go) {
    window.addEventListener("beforeinstallprompt", function (event) {
      // Brauzerning o'z taklifini to'xtatib, o'z tugmamizga bog'laymiz —
      // shunda u afitsantga tushunarli matn bilan chiqadi
      event.preventDefault();
      waiting = event;
      showInstall();
    });

    if (isIOS) {
      // iOS `beforeinstallprompt` ni umuman yubormaydi: tasmani o'zimiz
      // ko'rsatamiz va tugma yo'riqnomaga aylanadi
      showInstall();
    }

    go.addEventListener("click", function () {
      if (waiting) {
        waiting.prompt();
        waiting = null;
        bar.hidden = true;
        return;
      }
      if (text) text.textContent = go.dataset.ios;
      go.hidden = true;
    });

    window.addEventListener("appinstalled", function () {
      bar.hidden = true;
      dismiss("install");
    });
  }

  // --- bildirishnoma ruxsati ---------------------------------------------

  var notifyBar = document.getElementById("notifyBar");
  var notifyGo = document.getElementById("notifyGo");
  var notifyText = document.getElementById("notifyText");

  if (notifyBar && notifyGo && "Notification" in window) {
    // Ruxsat DARROV so'ralmaydi. So'rovsiz kelgan oynani odam o'ylamasdan
    // rad etadi va uni keyin ortga qaytarish brauzer sozlamalari orqali
    // bo'ladi — ya'ni amalda qaytarilmaydi.
    if (Notification.permission === "default" && !dismissed("notify")) {
      notifyBar.hidden = false;
    }

    notifyGo.addEventListener("click", function () {
      if (isIOS && !standalone) {
        // iPhone'da bildirishnoma faqat o'rnatilgan ilovada ishlaydi
        if (notifyText) notifyText.textContent = notifyGo.dataset.ios;
        return;
      }
      Notification.requestPermission().then(function (state) {
        if (state !== "granted") {
          if (notifyText) notifyText.textContent = notifyGo.dataset.blocked;
          return;
        }
        // Ruxsat — bu hali obuna emas. Qurilmani serverga yozib qo'ymasak
        // ilova yopiq bo'lganda hech narsa kelmaydi.
        subscribe().then(function (ok) {
          if (ok) {
            notifyBar.hidden = true;
            dismiss("notify");
          } else if (notifyText) {
            notifyText.textContent = notifyGo.dataset.ready;
          }
        });
      });
    });
  }
})();
