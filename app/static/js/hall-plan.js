// Zal sahifasi: stollarni belgilash va sudrab ko'chirish.
//
// Sahifa bu fayl umuman yuklanmasa ham to'liq ishlaydi: belgilash oddiy
// katakcha, ko'chirish esa bo'limdagi tugma bilan yuboriladigan forma.
// Bu yerdagi kod faqat qulaylik qo'shadi — hisob tasmasi va sudrash.
//
// Hodisalar `data-` atributlari orqali topiladi, inline `onclick` emas:
// CSP `script-src 'self'` inline ishlovchini bloklaydi va u jimgina
// ishlamay qo'yardi (`admin.js` da ham shu sabab shunday qilingan).

(function () {
  var form = document.getElementById("hall-move");
  if (!form) return;

  var plan = document.querySelector(".building");
  var tray = null;

  function ticks() {
    return Array.prototype.slice.call(
      document.querySelectorAll('.brick-tick input[type="checkbox"]')
    );
  }

  function chosen() {
    return ticks().filter(function (box) { return box.checked; });
  }

  // --- tanlov tasmasi ------------------------------------------------------
  //
  // Belgilangan stol pastda qolib ketishi mumkin — sanog'ini ko'rsatib
  // turmasak, egasi nechtasini belgilaganini bilmay qoladi.

  function buildTray() {
    var node = document.createElement("div");
    node.className = "hall-tray";
    node.hidden = true;

    var count = document.createElement("strong");
    var clear = document.createElement("button");
    clear.type = "button";
    clear.textContent = form.getAttribute("data-t-clear") || "×";
    clear.addEventListener("click", function () {
      ticks().forEach(function (box) { box.checked = false; });
      refresh();
    });

    node.appendChild(count);
    node.appendChild(clear);
    document.querySelector(".app-inner").appendChild(node);
    return { node: node, count: count };
  }

  function refresh() {
    if (!tray) tray = buildTray();
    var many = chosen().length;
    tray.node.hidden = many === 0;
    var pattern = form.getAttribute("data-t-selected") || "{n}";
    tray.count.textContent = pattern.replace("{n}", String(many));
  }

  document.addEventListener("change", function (event) {
    if (event.target.matches('.brick-tick input[type="checkbox"]')) refresh();
  });

  // --- sudrab tashlash -----------------------------------------------------
  //
  // Faqat kompyuterda: HTML5 drag telefonda ishlamaydi va uni taqlid qilish
  // uzun kod talab qiladi. Telefonda belgilash yo'li qoladi va u baribir
  // barmoq uchun qulayroq.
  //
  // Tashlangan stol shunchaki belgilanadi va o'sha bo'limning "Shu yerga"
  // tugmasi bosiladi — ya'ni server tomoni bitta va JS'siz yo'l bilan
  // aynan bir xil.

  if (!plan) return;

  var dragged = null;

  document.addEventListener("dragstart", function (event) {
    var brick = event.target.closest ? event.target.closest(".brick") : null;
    if (!brick) return;
    dragged = brick;
    brick.classList.add("is-dragging");
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      // Firefox bo'sh ma'lumotli sudrashni boshlamaydi
      event.dataTransfer.setData("text/plain", brick.getAttribute("data-table") || "");
    }
  });

  document.addEventListener("dragend", function () {
    if (dragged) dragged.classList.remove("is-dragging");
    document.querySelectorAll(".zone.is-target").forEach(function (zone) {
      zone.classList.remove("is-target");
    });
    dragged = null;
  });

  document.addEventListener("dragover", function (event) {
    var zone = event.target.closest ? event.target.closest(".zone") : null;
    if (!zone || !dragged) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
    zone.classList.add("is-target");
  });

  document.addEventListener("dragleave", function (event) {
    var zone = event.target.closest ? event.target.closest(".zone") : null;
    if (zone && !zone.contains(event.relatedTarget)) zone.classList.remove("is-target");
  });

  document.addEventListener("drop", function (event) {
    var zone = event.target.closest ? event.target.closest(".zone") : null;
    if (!zone || !dragged) return;
    event.preventDefault();

    var box = dragged.querySelector('input[type="checkbox"]');
    if (box) box.checked = true;

    // O'sha bo'limning o'z tugmasi bosiladi: `zone_id` qiymati aynan shu
    // tugmada yozilgan, ya'ni manzilni qaytadan hisoblash kerak emas.
    var button = zone.querySelector("[data-drop]");
    if (button) button.click();
  });
})();
