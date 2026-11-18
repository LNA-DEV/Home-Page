/* Resolve a colour token from assets/css/core/theme-vars.css to a concrete
   colour string, for scripts that hand colours to a canvas or an SVG library
   (Leaflet, MapLibre).

   A token holds light-dark(<light>, <dark>), and getPropertyValue() returns
   that text unresolved, which no library understands. Setting it as the
   `color` of an element and reading the computed value back resolves it
   against the page's color-scheme, the same way the stylesheet does.

   There is deliberately no fallback colour: a fallback is a second copy of
   the palette, and it drifts (docs/concepts/design-system.md §3.3). Call it
   again after a theme switch — the result follows `color-scheme`. */

let probe = null;

export function tokenColor(name) {
  if (!probe) {
    probe = document.createElement("span");
    probe.hidden = true;
    probe.setAttribute("aria-hidden", "true");
    document.documentElement.appendChild(probe);
  }
  probe.style.color = `var(${name})`;
  return getComputedStyle(probe).color;
}
