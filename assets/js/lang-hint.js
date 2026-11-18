/* The two clicks the language layer remembers (docs/concepts/multilingual-home.md
 * §4, §6a):
 *
 *   - a link carrying data-lang-choice (the header's language switcher, and the
 *     link in the hint bar) stores that language as `lang-choice`. From then on
 *     it counts instead of the browser's language: head.html's inline script
 *     reads it for data-top, and the root page (home.rootpicker.html) for where
 *     to send the visitor.
 *   - the ✕ of the hint bar stores `lang-hint-dismissed` and hides every bar at
 *     once by setting the attribute lang-more.css keys on.
 *
 * Nothing is shown or moved from here on page load; that is decided before first
 * paint, by the inline script and CSS. Storage may be blocked (private windows,
 * cleared site data), so every access is wrapped: the click still works, it is
 * just not remembered. */

function store(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (e) {
    /* not remembered, nothing else lost */
  }
}

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;

  const close = target.closest(".lang-hint__close");
  if (close) {
    store("lang-hint-dismissed", "1");
    document.documentElement.dataset.hintDismissed = "";
    /* The button is gone with its bar; keep keyboard focus somewhere sensible. */
    const main = document.getElementById("main") || document.querySelector("main");
    if (main) {
      if (!main.hasAttribute("tabindex")) main.setAttribute("tabindex", "-1");
      main.focus({ preventScroll: true });
    }
    return;
  }

  const choice = target.closest("[data-lang-choice]");
  if (choice) store("lang-choice", choice.getAttribute("data-lang-choice"));
});
