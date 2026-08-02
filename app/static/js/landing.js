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
});
