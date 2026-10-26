/* theme.js - light/dark mode toggle.
   Loaded in <head> (no defer) so the saved theme is applied BEFORE the page
   paints, which prevents a flash of the wrong colors. */
(function () {
  var KEY = "sub-tracker-theme";

  function saved() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
  }

  // Use the saved choice; otherwise default to dark (the original look).
  apply(saved() === "light" ? "light" : "dark");

  // One click handler for every toggle button on the page.
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-theme-toggle]");
    if (!btn) return;
    var next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    apply(next);
    try { localStorage.setItem(KEY, next); } catch (e2) {}
  });
})();
