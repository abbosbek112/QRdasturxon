// Ilovani yuklab olish sahifasi: qurilmaga tegishli bo'limni qoldiradi.
//
// Server qurilmani bilmaydi va bilishi ham shart emas — User-Agent bo'yicha
// serverda tarmoqlanish keshni buzadi va noto'g'ri sahifa berilib qolishi
// mumkin. Shuning uchun tanlov bu yerda, brauzerda.
//
// JS o'chiq bo'lsa hamma bo'lim ko'rinib turaveradi: afitsant o'zi keragini
// tanlaydi va hech kim yo'lsiz qolmaydi.
(function () {
  var blocks = document.querySelectorAll("[data-for]");
  if (!blocks.length) return;

  var agent = navigator.userAgent;
  var isAndroid = /android/i.test(agent);
  // iPadOS o'zini Mac deb ko'rsatadi — teginish nuqtalari bilan ajratamiz
  var isIOS =
    /iphone|ipad|ipod/i.test(agent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

  var keep = isAndroid ? "android" : isIOS ? "ios" : "desktop";

  for (var i = 0; i < blocks.length; i++) {
    var which = blocks[i].dataset.for;
    // Kompyuterda ikkala platforma ham ko'rinsin: odam ilovani o'zi uchun
    // emas, xodimiga yuborish uchun qarayotgan bo'lishi mumkin
    var show = keep === "desktop" ? true : which === keep;
    blocks[i].hidden = !show;
  }

  // QR faqat kompyuterda kerak — telefonda o'zini o'zi skanerlab bo'lmaydi
  var qr = document.querySelector('[data-for="desktop"]');
  if (qr) qr.hidden = keep !== "desktop";
})();
