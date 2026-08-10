// Savat. Mazmuni brauzerda yig'iladi, serverga esa bitta yuborishda ketadi.
//
// Bu yerdagi narx faqat KO'RSATISH uchun: server buyurtmani qabul qilganda
// narxni bazadan qayta o'qiydi. Ya'ni konsoldan `localStorage` ni tahrirlab
// arzonga buyurtma berib bo'lmaydi.
document.documentElement.classList.add("js");

(function () {
  var form = document.getElementById("cart");
  if (!form || !window.localStorage) return;

  var lines = document.getElementById("cartLines");
  var openBtn = document.getElementById("cartOpen");
  var panel = document.getElementById("cartPanel");
  var countEl = document.getElementById("cartCount");
  var sumEl = document.getElementById("cartSum");
  var clearBtn = document.getElementById("cartClear");
  var sendBtn = document.getElementById("cartSend");
  if (!lines || !openBtn || !panel || !countEl || !sumEl) return;

  var KEY = "qrd:cart:" + form.dataset.slug;
  var CURRENCY = form.dataset.currency || "";
  var EMPTY = form.dataset.empty || "";
  var MAX_QTY = 20; // server ham shu chegarani qo'yadi

  var cart = read();

  function read() {
    try {
      var saved = JSON.parse(localStorage.getItem(KEY));
      return saved && typeof saved === "object" ? saved : {};
    } catch (err) {
      return {}; // buzuq yozuv — bo'sh savatdan boshlaymiz
    }
  }

  function write() {
    try {
      localStorage.setItem(KEY, JSON.stringify(cart));
    } catch (err) {
      /* xotira to'lgan yoki taqiqlangan — savat shu sahifada baribir ishlaydi */
    }
  }

  // Serverdagi `format_price` bilan bir xil: mingliklar orasida bo'shliq
  function money(value) {
    return String(Math.round(value)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  function ids() {
    return Object.keys(cart);
  }

  function totals() {
    var count = 0;
    var sum = 0;
    ids().forEach(function (id) {
      count += cart[id].q;
      sum += cart[id].p * cart[id].q;
    });
    return { count: count, sum: sum };
  }

  function setQty(id, quantity) {
    if (!cart[id]) return;
    cart[id].q = Math.max(0, Math.min(quantity, MAX_QTY));
    if (!cart[id].q) delete cart[id];
    write();
    render();
  }

  function add(button) {
    var id = button.dataset.id;
    if (!cart[id]) {
      cart[id] = {
        n: button.dataset.name || "",
        p: parseInt(button.dataset.price, 10) || 0,
        q: 0,
      };
    }
    if (cart[id].q >= MAX_QTY) return;
    cart[id].q += 1;
    write();
    render();

    // Qisqa "qo'shildi" ishorasi — savat pastda, ko'z uni sezmay qolmasin
    button.classList.remove("is-added");
    void button.offsetWidth;
    button.classList.add("is-added");
  }

  function render() {
    var t = totals();
    form.hidden = t.count === 0;
    // Sahifa oxiri savat tasmasi ostida qolib ketmasin
    document.body.classList.toggle("has-cart", t.count > 0);
    countEl.textContent = t.count;
    sumEl.textContent = t.count ? money(t.sum) + " " + CURRENCY : "";
    if (sendBtn) sendBtn.disabled = t.count === 0;

    if (!t.count) {
      lines.textContent = EMPTY;
      closePanel();
      return;
    }

    lines.textContent = "";
    ids().forEach(function (id) {
      lines.appendChild(row(id, cart[id]));
    });
  }

  function row(id, entry) {
    var wrap = document.createElement("div");
    wrap.className = "cart-line";

    var name = document.createElement("span");
    name.className = "cart-line-name";
    name.textContent = entry.n;

    var price = document.createElement("span");
    price.className = "cart-line-sum";
    price.textContent = money(entry.p * entry.q);

    var steps = document.createElement("span");
    steps.className = "qty";
    steps.appendChild(step("−", id, entry.q - 1));
    var value = document.createElement("b");
    value.textContent = entry.q;
    steps.appendChild(value);
    steps.appendChild(step("+", id, entry.q + 1));

    wrap.appendChild(name);
    wrap.appendChild(steps);
    wrap.appendChild(price);
    return wrap;
  }

  function step(label, id, next) {
    var button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.setAttribute("aria-label", label === "+" ? "+1" : "-1");
    button.addEventListener("click", function () {
      setQty(id, next);
    });
    return button;
  }

  function openPanel() {
    panel.hidden = false;
    openBtn.setAttribute("aria-expanded", "true");
  }

  function closePanel() {
    panel.hidden = true;
    openBtn.setAttribute("aria-expanded", "false");
  }

  openBtn.addEventListener("click", function () {
    if (panel.hidden) openPanel();
    else closePanel();
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      cart = {};
      write();
      render();
    });
  }

  // Taom kartasidagi "+" — kartalar sahifa bo'ylab tarqoq, shuning uchun
  // hodisa hujjat darajasida ushlanadi
  document.addEventListener("click", function (event) {
    var button = event.target.closest ? event.target.closest(".dish-add") : null;
    if (!button) return;
    event.preventDefault();
    add(button);
  });

  // Yuborishdan oldin savatni yashirin maydonlarga aylantiramiz.
  // `item_id` va `qty` juft bo'lib, bir xil tartibda ketadi.
  form.addEventListener("submit", function (event) {
    var old = form.querySelectorAll("input[data-line]");
    for (var i = 0; i < old.length; i++) old[i].remove();

    var chosen = ids();
    if (!chosen.length) {
      event.preventDefault();
      return;
    }

    chosen.forEach(function (id) {
      form.appendChild(hidden("item_id", id));
      form.appendChild(hidden("qty", cart[id].q));
    });

    // Buyurtma ketdi — orqaga qaytilsa eski savat qayta chiqmasin
    try {
      localStorage.removeItem(KEY);
    } catch (err) {
      /* muhim emas */
    }
    if (sendBtn) sendBtn.disabled = true;
  });

  function hidden(name, value) {
    var input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    input.setAttribute("data-line", "");
    return input;
  }

  render();
})();
