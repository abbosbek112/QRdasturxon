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
