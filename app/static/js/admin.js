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

// Uslub tanlanganda rang maydonini o'sha uslubning rangiga o'tkazadi.
// Restoran keyin rangni o'zi o'zgartirsa, u saqlanib qoladi.
(function () {
  var picker = document.querySelector(".theme-picker");
  var color = document.getElementById("theme_color");
  if (!picker || !color) return;

  picker.addEventListener("change", function (event) {
    var input = event.target;
    if (!input.matches('input[name="theme"]')) return;

    var accent = input.getAttribute("data-accent");
    if (accent) color.value = accent;
  });
})();
