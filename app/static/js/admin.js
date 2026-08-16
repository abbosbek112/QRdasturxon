// Xavfli amal oldidan tasdiq so'raydi.
//
// Ataylab shu yerda, `onsubmit="return confirm(...)"` da emas: CSP
// `script-src 'self'` inline hodisa ishlovchilarini ham bloklaydi, ya'ni
// atributdagi confirm() umuman chaqirilmaydi va o'chirish jimgina bajarilib
// ketadi. `data-confirm` esa oddiy atribut — u hech qanday kod emas.
document.addEventListener("submit", function (event) {
  var form = event.target;
  if (!form || !form.getAttribute) return;

  var question = form.getAttribute("data-confirm");
  if (question && !window.confirm(question)) event.preventDefault();
});

// Chop etish tugmasi — shuningdek CSP sababli inline onclick o'rniga
document.addEventListener("click", function (event) {
  var button = event.target.closest ? event.target.closest("[data-print]") : null;
  if (button) window.print();
});

// Parol maydoni: ko'rsatish/yashirish, yasash va nusxa olish.
//
// Faqat YANGI qo'yilayotgan parol uchun. Bazadagi parol Argon2 bilan
// qaytmaydigan qilib xeshlangan — uni na bu yerda, na boshqa joyda ochib
// bo'ladi. Unutilgan parolni ko'rsatish emas, almashtirish kerak.
(function () {
  // Chalkashtirmaydigan alifbo: 0/O va 1/l/I yo'q. Parol og'zaki aytiladi
  // va qog'ozga yoziladi — o'sha yerda adashish eng ko'p uchraydi.
  var ALPHABET = "abcdefghijkmnpqrstuvwxyzACDEFGHJKLMNPQRSTUVWXYZ23456789";
  var LENGTH = 12;

  function make() {
    var bytes = new Uint32Array(LENGTH);
    (window.crypto || window.msCrypto).getRandomValues(bytes);
    var out = "";
    for (var i = 0; i < LENGTH; i++) out += ALPHABET[bytes[i] % ALPHABET.length];
    return out;
  }

  function fieldOf(button) {
    var box = button.closest(".pw");
    return box ? box.querySelector("input") : null;
  }

  function flash(button, text) {
    var was = button.getAttribute("title");
    button.setAttribute("title", text);
    button.classList.add("is-done");
    setTimeout(function () {
      button.setAttribute("title", was);
      button.classList.remove("is-done");
    }, 1400);
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest ? event.target.closest(".pw-btn") : null;
    if (!button) return;
    var input = fieldOf(button);
    if (!input) return;

    if (button.hasAttribute("data-pw-toggle")) {
      var hidden = input.type === "password";
      input.type = hidden ? "text" : "password";
      button.classList.toggle("is-shown", hidden);
      var label = hidden ? button.dataset.hide : button.dataset.show;
      button.setAttribute("title", label);
      button.setAttribute("aria-label", label);
      return;
    }

    if (button.hasAttribute("data-pw-make")) {
      input.value = make();
      input.type = "text"; // yasalgan parol darrov ko'rinsin — uni yozib olish kerak
      var eye = button.closest(".pw").querySelector("[data-pw-toggle]");
      if (eye) eye.classList.add("is-shown");
      return;
    }

    if (button.hasAttribute("data-pw-copy")) {
      if (!input.value) return;

      // Zaxira yo'l: parolni ochib, matnni tanlab qo'yamiz — foydalanuvchi
      // Ctrl+C bilan o'zi oladi. Brauzer clipboard'ga ruxsat bermasligi
      // mumkin va o'shanda tugma javobsiz qolmasligi kerak.
      var selectIt = function () {
        input.type = "text";
        var eye = button.closest(".pw").querySelector("[data-pw-toggle]");
        if (eye) eye.classList.add("is-shown");
        input.focus();
        input.select();
      };
      var done = function () {
        flash(button, button.dataset.done);
      };

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(input.value).then(done, function () {
          selectIt();
        });
      } else {
        selectIt();
        done();
      }
    }
  });
})();

// Dizayn bo'limidagi ikkita qulaylik. Ikkalasi ham FAQAT qulaylik:
// JS o'chirilgan brauzerda forma baribir to'g'ri ishlaydi.
(function () {
  var grid = document.querySelector(".tpl-grid");
  var own = document.getElementById("own_color");
  var ownRadio = document.querySelector('input[name="theme_color"][value="__own__"]');

  // 1. Shablon tanlanganda rang ham o'sha shablonnikiga o'tadi. Odam
  //    rangni o'zi o'zgartirgan bo'lsa, keyingi shablongacha shu qoladi.
  if (grid) {
    grid.addEventListener("change", function (event) {
      var input = event.target;
      if (!input.matches('input[name="theme"]')) return;

      var accent = input.getAttribute("data-accent");
      if (!accent) return;

      var swatch = document.querySelector(
        'input[name="theme_color"][value="' + accent + '"]'
      );
      if (swatch) {
        swatch.checked = true;
      } else if (own && ownRadio) {
        own.value = accent;
        ownRadio.checked = true;
      }
      paintOwn();
    });
  }

  // 2. Rang tanlagichga tegilsa "o'z rangim" o'zi belgilanadi — aks holda
  //    odam rang tanlab, radioni belgilashni unutib saqlab yuborardi.
  if (own && ownRadio) {
    own.addEventListener("input", function () {
      ownRadio.checked = true;
      paintOwn();
    });
  }

  function paintOwn() {
    if (own && ownRadio) ownRadio.closest(".swatch").style.setProperty("--sw", own.value);
  }
})();

/*
  Bino: qaysi raqamlar chiqishini BOSISHDAN OLDIN ko'rsatish.

  Ilgari natija kutilmagan bo'lib chiqardi. Haqiqiy holat: qavatda 2 va
  3 turgan, egasi to'rtta qo'shgan va 21, 22, 23, 24 chiqqan — chunki
  raqam butun restorandagi eng kattadan davom etardi.

  Endi server bo'shliqlarni to'ldiradi, bu yerdagi hisob esa AYNAN o'sha
  qoidani takrorlaydi. Ikki joyda bir xil mantiq bo'lgani yoqimsiz, lekin
  muqobili — har tugmachada serverga so'rov yuborish.
*/
(function () {
  var bino = document.querySelector(".building[data-taken]");
  if (!bino) return;

  var band = (bino.getAttribute("data-taken") || "")
    .split(",")
    .filter(Boolean);

  function keyingiRaqamlar(count, start) {
    var olingan = band.slice();
    var son = start && start >= 1 ? start : 1;
    var chiqdi = [];
    var chek = son + olingan.length + count + 1;
    while (chiqdi.length < count && son < chek) {
      var nom = String(son);
      if (olingan.indexOf(nom) === -1) chiqdi.push(nom);
      son += 1;
    }
    return chiqdi;
  }

  function yangila(forma) {
    var joy = forma.querySelector("[data-preview]");
    if (!joy) return;
    var count = parseInt(forma.querySelector('[name="count"]').value, 10);
    var startEl = forma.querySelector('[name="start"]');
    var start = startEl ? parseInt(startEl.value, 10) : NaN;
    if (!count || count < 1) {
      joy.textContent = "";
      return;
    }
    // Ko'p bo'lsa hammasini yozib chiqish o'qishga xalaqit beradi
    var raqamlar = keyingiRaqamlar(Math.min(count, 50), isNaN(start) ? null : start);
    var matn = raqamlar.slice(0, 8).join(", ");
    if (raqamlar.length > 8) matn += " …";
    joy.textContent = matn;
  }

  var formalar = bino.querySelectorAll(".zone-add");
  Array.prototype.forEach.call(formalar, function (forma) {
    if (!forma.querySelector('[name="count"]')) return;
    yangila(forma);
    forma.addEventListener("input", function () { yangila(forma); });
  });
})();
