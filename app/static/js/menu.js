// Menyuda skroll qilinganda joriy kategoriya tugmasini yoritadi.
(function () {
  var nav = document.getElementById("catnav");
  if (!nav) return;

  var links = Array.prototype.slice.call(nav.querySelectorAll("a"));
  var sections = links
    .map(function (link) {
      return document.querySelector(link.getAttribute("href"));
    })
    .filter(Boolean);
  if (sections.length !== links.length || !sections.length) return;

  var current = -1;
  var queued = false;

  function highlight() {
    queued = false;
    var offset = nav.offsetHeight + 28;
    var index = 0;

    for (var i = 0; i < sections.length; i++) {
      if (sections[i].getBoundingClientRect().top <= offset) index = i;
    }
    // Sahifa oxirida oxirgi kategoriya faol bo'lsin
    if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 4) {
      index = sections.length - 1;
    }
    if (index === current) return;
    current = index;

    for (var j = 0; j < links.length; j++) {
      links[j].classList.toggle("active", j === index);
    }

    var active = links[index];
    var navBox = nav.getBoundingClientRect();
    var box = active.getBoundingClientRect();
    if (box.left < navBox.left + 8 || box.right > navBox.right - 8) {
      nav.scrollTo({ left: active.offsetLeft - 16, behavior: "smooth" });
    }
  }

  function schedule() {
    if (queued) return;
    queued = true;
    window.requestAnimationFrame(highlight);
  }

  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", schedule);
  highlight();
})();

// Taom tafsilotini sahifadan chiqmasdan pastki oynada ko'rsatadi.
// JS ishlamasa kartalar oddiy havola bo'lib qolaveradi.
(function () {
  var overlay = document.getElementById("sheetOverlay");
  var panel = document.getElementById("sheetPanel");
  var grip = document.getElementById("sheetGrip");
  var body = document.getElementById("sheetBody");
  if (!overlay || !panel || !grip || !body) return;

  var ANIM = 340;
  var SKELETON =
    '<div class="sheet-skeleton"><i></i><i></i><i></i></div>';

  var cache = new Map();
  var isOpen = false;
  var pushedState = false;
  var trigger = null;
  var scrollY = 0;
  var hideTimer = null;
  var fetchToken = 0;

  // Skrollni o'zimiz boshqaramiz — brauzer tarix bo'ylab yurganda aralashmasin
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";

  function partialUrl(href) {
    return href + (href.indexOf("?") === -1 ? "?" : "&") + "partial=1";
  }

  function lockScroll() {
    scrollY = window.scrollY;
    document.body.style.top = -scrollY + "px";
    document.body.classList.add("is-sheet-locked");
  }

  function unlockScroll() {
    document.body.classList.remove("is-sheet-locked");
    document.body.style.top = "";
    window.scrollTo({ top: scrollY, behavior: "instant" });
  }

  // Oyna ochiq bo'lganda orqadagi sahifa klaviatura va skrinriderdan yashirinadi
  function setBackgroundInert(on) {
    var kids = document.body.children;
    for (var i = 0; i < kids.length; i++) {
      var el = kids[i];
      if (el === overlay || el === panel || el.tagName === "SCRIPT") continue;
      if (on) el.setAttribute("inert", "");
      else el.removeAttribute("inert");
    }
  }

  function open(href, source) {
    if (isOpen) return;
    isOpen = true;
    trigger = source || null;
    clearTimeout(hideTimer);

    var url = partialUrl(href);
    body.innerHTML = cache.has(url) ? cache.get(url) : SKELETON;

    overlay.hidden = false;
    panel.hidden = false;
    void panel.offsetWidth; // reflow — bo'lmasa animatsiya ishlamaydi
    document.documentElement.classList.add("is-sheet-open");
    lockScroll();
    setBackgroundInert(true);
    grip.focus();

    if (!cache.has(url)) load(url, href);

    // Orqaga tugmasi oynani yopsin, sahifadan chiqarib yubormasin
    try {
      history.pushState({ qrSheet: true }, "", href);
      pushedState = true;
    } catch (err) {
      pushedState = false;
    }
  }

  function load(url, href) {
    var token = ++fetchToken;
    fetch(url, { headers: { "X-Requested-With": "fetch" } })
      .then(function (res) {
        if (!res.ok) throw new Error("status " + res.status);
        return res.text();
      })
      .then(function (html) {
        cache.set(url, html);
        if (token === fetchToken && isOpen) body.innerHTML = html;
      })
      .catch(function () {
        // Yuklab bo'lmasa — eski usulda tafsilot sahifasiga o'tamiz
        if (token === fetchToken && isOpen) window.location.href = href;
      });
  }

  function close(fromPopstate) {
    if (!isOpen) return;
    isOpen = false;
    fetchToken++;
    var restoreTo = scrollY;

    document.documentElement.classList.remove("is-sheet-open");
    panel.classList.remove("is-dragging");
    panel.style.transform = "";
    unlockScroll();
    setBackgroundInert(false);

    if (trigger && typeof trigger.focus === "function") trigger.focus();
    trigger = null;

    hideTimer = setTimeout(function () {
      if (!isOpen) {
        overlay.hidden = true;
        panel.hidden = true;
        body.innerHTML = "";
      }
    }, ANIM);

    // Manzil qatorini menyuga qaytaramiz
    if (!fromPopstate && pushedState) {
      pushedState = false;
      history.back();
      // Tarix bo'ylab yurish skrollni siljitib yuborishi mumkin — qaytarib qo'yamiz
      requestAnimationFrame(function () {
        window.scrollTo({ top: restoreTo, behavior: "instant" });
      });
    } else {
      pushedState = false;
    }
  }

  // --- ochish: kartaga bosilganda ---
  document.addEventListener("click", function (event) {
    var link = event.target.closest ? event.target.closest("a.dish") : null;
    if (!link) return;
    // Ctrl/Cmd/shift bilan bosilsa yangi oynada ochilsin — aralashmaymiz
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    open(link.getAttribute("href"), link);
  });

  // --- yopish: overlay, Escape, orqaga tugmasi ---
  overlay.addEventListener("click", function () {
    close(false);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && isOpen) close(false);
  });

  window.addEventListener("popstate", function () {
    if (isOpen) close(true);
  });

  // --- yopish: pastga sudrash ---
  var dragStartY = 0;
  var dragLastY = 0;
  var dragLastT = 0;
  var dragging = false;

  grip.addEventListener("pointerdown", function (event) {
    if (!isOpen) return;
    dragging = true;
    dragStartY = dragLastY = event.clientY;
    dragLastT = event.timeStamp;
    panel.classList.add("is-dragging");
    try {
      grip.setPointerCapture(event.pointerId);
    } catch (err) {
      /* ba'zi brauzerlarda ko'rsatkich faol bo'lmasa xato beradi — muhim emas */
    }
  });

  grip.addEventListener("pointermove", function (event) {
    if (!dragging) return;
    var dy = event.clientY - dragStartY;
    dragLastY = event.clientY;
    dragLastT = event.timeStamp;
    panel.style.transform = "translateY(" + Math.max(dy, 0) + "px)";
  });

  function endDrag(event) {
    if (!dragging) return;
    dragging = false;
    panel.classList.remove("is-dragging");

    var dy = Math.max(event.clientY - dragStartY, 0);
    var dt = Math.max(event.timeStamp - dragLastT, 1);
    var velocity = (event.clientY - dragLastY) / dt;
    var threshold = Math.max(80, panel.offsetHeight * 0.25);

    if (dy > threshold || velocity > 0.5) {
      close(false);
    } else {
      panel.style.transform = ""; // joyiga qaytadi
    }
  }

  grip.addEventListener("pointerup", endDrag);
  grip.addEventListener("pointercancel", endDrag);

  // Sahifa oyna ochiq holatda yangilansa, qulf qolib ketmasin
  window.addEventListener("pageshow", function () {
    if (!isOpen) {
      document.body.classList.remove("is-sheet-locked");
      document.body.style.top = "";
    }
  });
})();
