/* Bosh sahifa animatsiyalari.
 *
 * Ikki qoida:
 *
 * 1. JS o'chgan yoki yuklanmagan bo'lsa sahifa TO'LIQ ko'rinadi. Yashirish
 *    faqat `html.js` bo'lganda ishlaydi, o'sha klassni esa shu fayl qo'yadi.
 *    Shuning uchun bu fayl <head> ichida, `defer` siz ulanadi: aks holda
 *    mazmun avval chizilib, keyin yashirinib, keyin qayta chiqardi.
 *
 * 2. Tizimda "harakatni kamaytir" yoqilgan bo'lsa hech narsa harakatlanmaydi.
 */

document.documentElement.classList.add("js");

document.addEventListener("DOMContentLoaded", function () {
  var calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var targets = document.querySelectorAll("[data-reveal]");
  var counters = document.querySelectorAll("[data-count]");

  function showAll() {
    for (var i = 0; i < targets.length; i++) targets[i].classList.add("is-in");
    for (var j = 0; j < counters.length; j++) {
      counters[j].textContent = counters[j].getAttribute("data-count");
    }
  }

  if (calm || !("IntersectionObserver" in window)) {
    showAll();
    return;
  }

  /*
    Xavfsizlik to'ri: nima bo'lganda ham mazmun ko'rinsin.

    `data-reveal` elementlari CSS bilan yashirilgan va faqat JS ularni
    ochadi. Ya'ni kuzatuvchi ishlamay qolsa sahifaning yarmi BO'SH
    qoladi — bu eng yomon nosozlik va u haqiqatan sodir bo'ldi: joylashuv
    xatosi tufayli matn ustuni ekran tashqarisiga surilib, kuzatuvchi uni
    hech qachon "ko'rinadi" deb hisoblamadi va u ko'rinmay qoldi.

    Endi uch soniyadan keyin qolganlari baribir ochiladi. Animatsiya
    yo'qoladi, mazmun esa qoladi.
  */
  setTimeout(showAll, 3000);

  // Guruh ichidagi elementlar navbat bilan chiqsin: CSS kechikishni
  // --i dan oladi, biz shu raqamni qo'yamiz.
  var groups = document.querySelectorAll("[data-stagger]");
  for (var g = 0; g < groups.length; g++) {
    var kids = groups[g].children;
    for (var k = 0; k < kids.length; k++) kids[k].style.setProperty("--i", k);
  }

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-in");
        // Bir marta ko'rsatamiz — orqaga skroll qilganda qayta yashirinmasin
        observer.unobserve(entry.target);
        if (entry.target.hasAttribute("data-count")) countUp(entry.target);
      });
    },
    { rootMargin: "0px 0px -10% 0px", threshold: 0.1 }
  );

  for (var t = 0; t < targets.length; t++) observer.observe(targets[t]);
  for (var c = 0; c < counters.length; c++) {
    if (!counters[c].hasAttribute("data-reveal")) observer.observe(counters[c]);
  }

  /* Raqam noldan o'sib chiqadi. Matn oxirida aynan data-count qiymati
   * qoladi — ya'ni animatsiya to'xtagan joyda ham son to'g'ri bo'ladi. */
  function countUp(node) {
    var target = node.getAttribute("data-count");
    var digits = parseInt(target.replace(/\D/g, ""), 10);
    if (!digits) {
      node.textContent = target;
      return;
    }
    var started = null;
    var duration = 1100;

    function step(now) {
      if (started === null) started = now;
      var passed = Math.min((now - started) / duration, 1);
      // Oxiriga borib sekinlashadi — bir tekis o'sish sun'iy ko'rinadi
      var eased = 1 - Math.pow(1 - passed, 3);
      if (passed < 1) {
        node.textContent = Math.round(digits * eased).toLocaleString("ru-RU");
        requestAnimationFrame(step);
      } else {
        node.textContent = target;
      }
    }
    requestAnimationFrame(step);
  }

  // --- Narxlar bo'limi: oylik/yillik almashtirgich ---
  var billingToggle = document.getElementById("billing-toggle");
  var toggleWrap = document.querySelector(".lp-toggle-wrap");
  var plansContainer = document.querySelector(".lp-plans");
  var lblMonthly = document.getElementById("lbl-monthly");
  var lblYearly = document.getElementById("lbl-yearly");

  if (billingToggle) {
    function setBilling(isYearly) {
      billingToggle.setAttribute("aria-checked", isYearly ? "true" : "false");
      if (plansContainer) plansContainer.classList.toggle("is-yearly", isYearly);
      if (toggleWrap) toggleWrap.classList.toggle("is-yearly", isYearly);
    }

    billingToggle.addEventListener("click", function (e) {
      e.preventDefault();
      setBilling(billingToggle.getAttribute("aria-checked") !== "true");
    });

    if (lblMonthly) {
      lblMonthly.addEventListener("click", function () { setBilling(false); });
    }
    if (lblYearly) {
      lblYearly.addEventListener("click", function () { setBilling(true); });
    }
  }
});

/*
  Shablonlar karuseli.

  Uch narsa qiladi: strelka bilan surish, nuqta bilan sakrash va
  markazdagi kartochkani belgilash. Uchalasi ham QULAYLIK — bularsiz
  ham tasma barmoq yoki sichqoncha bilan surilaveradi.

  O'ZI AYLANMAYDI. Avtomatik surilish eng ko'p shikoyat qilinadigan
  naqsh: odam o'qib turganda kartochka ostidan sirg'alib ketadi.
*/
document.addEventListener("DOMContentLoaded", function () {
  var box = document.querySelector("[data-carousel]");
  if (!box) return;

  var track = box.querySelector("[data-carousel-track]");
  var slides = Array.prototype.slice.call(track.children);
  var dots = Array.prototype.slice.call(box.querySelectorAll(".carousel-dot"));
  var prev = box.querySelector("[data-carousel-prev]");
  var next = box.querySelector("[data-carousel-next]");
  if (!slides.length) return;

  var joriy = 0;

  function belgila(i) {
    joriy = i;
    slides.forEach(function (s, n) { s.classList.toggle("is-active", n === i); });
    dots.forEach(function (d, n) { d.classList.toggle("is-on", n === i); });
    if (prev) prev.disabled = i === 0;
    if (next) next.disabled = i === slides.length - 1;
  }

  function surish(i) {
    i = Math.max(0, Math.min(i, slides.length - 1));
    var s = slides[i];
    // `scrollIntoView` sahifani ham vertikal siljitardi — faqat
    // tasmaning ichki siljishini o'zgartiramiz
    track.scrollTo({
      left: s.offsetLeft - (track.clientWidth - s.offsetWidth) / 2,
      behavior: "smooth",
    });
    belgila(i);
  }

  if (prev) prev.addEventListener("click", function () { surish(joriy - 1); });
  if (next) next.addEventListener("click", function () { surish(joriy + 1); });
  dots.forEach(function (d) {
    d.addEventListener("click", function () { surish(parseInt(d.getAttribute("data-go"), 10) || 0); });
  });

  // Barmoq bilan surilganda ham markazdagisi belgilansin
  var kutish;
  track.addEventListener("scroll", function () {
    clearTimeout(kutish);
    kutish = setTimeout(function () {
      var markaz = track.scrollLeft + track.clientWidth / 2;
      var eng = 0, farq = Infinity;
      slides.forEach(function (s, n) {
        var d = Math.abs(s.offsetLeft + s.offsetWidth / 2 - markaz);
        if (d < farq) { farq = d; eng = n; }
      });
      belgila(eng);
    }, 90);
  }, { passive: true });

  belgila(0);
});
