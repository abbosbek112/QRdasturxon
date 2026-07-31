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
