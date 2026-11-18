/* The map of a project story (docs/concepts/gallery-project-stories.md §8).

   Two kinds of map, both on the site's own basemap (basemap.js), both drawing
   data/galleryAreas.yaml and nothing else — coarse circles, never a photo's
   position:

   - the overview map ([data-story-map]): one circle per area with a chip that
     leads to the chapter or outing; built when it nears the viewport and kept;
   - the mini maps beside journal entries ([data-mini-map]): pictures, not
     tools — no dragging, no zoom — framed on their one circle.

   Every basemap is its own MapLibre instance with its own WebGL context, and a
   browser keeps only so many alive (Chromium 16, dropping the oldest). A
   journal that grows for years would get there, and every instance costs a
   phone memory long before. So a mini map exists only near the viewport: built
   within half a viewport height, removed beyond two, and never more than
   MINI_LIMIT at once (the furthest goes). Removing it frees its context:
   maplibre-gl-leaflet's onRemove calls MapLibre's remove(), which loses it.

   No WebGL2, no map: circles on an empty field say nothing. The area list and
   the chips in the mini map boxes are in the HTML for that case, and they stay
   for everyone as the legend. Zoom stops at 13: at 47°N a 1,000 m radius is
   then about 150 px across, a place in its landscape and not a target. */

import * as params from "@params";
import { addBasemap, currentFlavor, BASEMAP_ATTRIBUTION, webgl2Available } from "./basemap.js";

const TILEJSON = params.basemapTileJson || "";
const MAX_ZOOM = 13;
const MINI_LIMIT = 4;

let overview = null; // { map, base, circles: Map(slug → { circle, bounds }) }
let pendingHighlight = "";
const minis = new Set(); // live mini maps: { el, holder, map, base }

const escapeHtml = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );

function accent() {
  return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#d8a657";
}

function circleStyle(strong) {
  const color = accent();
  return {
    color,
    weight: strong ? 3 : 1.5,
    dashArray: "5 5",
    fillColor: color,
    fillOpacity: strong ? 0.3 : 0.14,
  };
}

/* The bounds of an area's circle. L.Circle#getBounds needs the circle on a
   map that already has a view, which is exactly what fitting the view is for. */
function areaBounds(lat, lng, radius) {
  const dLat = radius / 111320;
  const dLng = radius / (111320 * Math.cos((lat * Math.PI) / 180));
  return L.latLngBounds([lat - dLat, lng - dLng], [lat + dLat, lng + dLng]);
}

function phone() {
  return window.matchMedia("(max-width: 768px)").matches;
}

function readAreas(el) {
  try {
    return JSON.parse(el.dataset.areas || "[]").filter(
      (a) => a && Number.isFinite(a.lat) && Number.isFinite(a.lng) && Number.isFinite(a.radius),
    );
  } catch (err) {
    return [];
  }
}

function chipHtml(a, journal) {
  const badge = journal ? String(a.count || "") : a.badge;
  const text = journal ? a.name : a.title || a.name;
  return (
    `<span class="story-area-chip" title="${escapeHtml(a.name)}">` +
    (badge ? `<b>${escapeHtml(badge)}</b>` : "<b>·</b>") +
    `<span class="story-area-chip-text">${escapeHtml(text)}</span>` +
    (!journal && a.count ? `<span class="story-area-chip-count">${a.count}</span>` : "") +
    "</span>"
  );
}

/* Where each chip goes. Areas sit close together (five of Inn-Valley's within
   8 km), and at the zoom that shows them all there is no room for every name.
   So, in priority order, each chip takes the first side of its circle that is
   clear of the chips already placed and of every other circle: east, west,
   south, north. A chip with no such side shrinks to a badge on its circle,
   which shows the name on hover.

   The layout depends on the zoom alone, never on where the map is panned to:
   panning moves every chip and circle alike, so nothing changes and nothing
   jumps when an area is dragged to the edge and back. Only the starting view
   (`framed`) also keeps every chip inside the map and off its controls, so the
   page does not open on a cut-off name; after a zoom a chip may run past the
   edge like any map label, and the starting zoom gets the starting layout
   back (`sides`). Returns the side chosen for each chip. */
const CHIP_GAP = 6;
const CHIP_SIDES = ["e", "w", "s", "n"];
const CHIP_CLASSES = ["is-e", "is-w", "is-s", "is-n", "is-badge"];

function placeChips(map, chips, { framed = false, sides = null } = {}) {
  const size = map.getSize();
  const blocked = [];
  if (framed) {
    const box = map.getContainer().getBoundingClientRect();
    map
      .getContainer()
      .querySelectorAll(".leaflet-control-zoom, .leaflet-control-attribution")
      .forEach((el) => {
        const r = el.getBoundingClientRect();
        blocked.push({ x0: r.left - box.left, y0: r.top - box.top, x1: r.right - box.left, y1: r.bottom - box.top });
      });
  }

  const geo = chips.map(({ a }) => {
    const c = map.latLngToContainerPoint([a.lat, a.lng]);
    const r = map.latLngToContainerPoint([a.lat, areaBounds(a.lat, a.lng, a.radius).getEast()]).x - c.x;
    return { c, r };
  });
  const overlaps = (p, q) => p.x0 < q.x1 && q.x0 < p.x1 && p.y0 < q.y1 && q.y0 < p.y1;
  /* A chip against a circle itself, not its bounding box: the box's corners
     would turn chips into badges that had room. */
  const hitsCircle = (p, g) => {
    const x = Math.max(p.x0, Math.min(g.c.x, p.x1));
    const y = Math.max(p.y0, Math.min(g.c.y, p.y1));
    return (x - g.c.x) ** 2 + (y - g.c.y) ** 2 < g.r ** 2;
  };
  const inside = (p) => !framed || (p.x0 >= 4 && p.y0 >= 4 && p.x1 <= size.x - 4 && p.y1 <= size.y - 4);

  return chips.map(({ chip }, i) => {
    const el = chip.getElement()?.firstElementChild;
    if (!el) return "badge";
    const { c, r } = geo[i];
    el.style.setProperty("--r", `${Math.max(r, 0).toFixed(1)}px`);
    let side = sides ? sides[i] : "";
    if (!side) {
      /* Measure the full chip: the badge state hides its text. */
      el.classList.remove(...CHIP_CLASSES);
      el.classList.add("is-e");
      const w = el.offsetWidth;
      const h = el.offsetHeight;
      const others = geo.filter((_, j) => j !== i);
      const rect = {
        e: { x0: c.x + r + CHIP_GAP, y0: c.y - h / 2 },
        w: { x0: c.x - r - CHIP_GAP - w, y0: c.y - h / 2 },
        s: { x0: c.x - w / 2, y0: c.y + r + CHIP_GAP },
        n: { x0: c.x - w / 2, y0: c.y - r - CHIP_GAP - h },
      };
      side = "badge";
      for (const s of CHIP_SIDES) {
        const p = { ...rect[s], x1: rect[s].x0 + w, y1: rect[s].y0 + h };
        if (inside(p) && !blocked.some((q) => overlaps(p, q)) && !others.some((g) => hitsCircle(p, g))) {
          side = s;
          blocked.push(p);
          break;
        }
      }
    }
    el.classList.remove(...CHIP_CLASSES);
    el.classList.add(`is-${side}`);
    if (side === "badge") {
      const half = el.offsetWidth / 2;
      blocked.push({ x0: c.x - half, y0: c.y - half, x1: c.x + half, y1: c.y + half });
    }
    return side;
  });
}

/* ---- overview ------------------------------------------------------------ */

async function buildOverview(canvas) {
  const areas = readAreas(canvas);
  if (!areas.length) return;
  const journal = canvas.closest(".story-map-journal") !== null;

  /* The wheel zooms only after a click into the map, so scrolling through an
     essay is not caught by it — as the route maps do. */
  /* Leaflet draws a path only inside the view plus `padding` (default 0.1 of
     its size on each side) and redraws on moveend, so a circle dragged in from
     further out popped up on release. A handful of circles costs nothing to
     draw, so the drawn area reaches two map sizes past every edge. */
  const map = L.map(canvas, {
    scrollWheelZoom: false,
    maxZoom: MAX_ZOOM,
    zoomSnap: 0.5,
    renderer: L.svg({ padding: 2 }),
  });
  map.on("click", () => map.scrollWheelZoom.enable());
  map.on("mouseout", () => map.scrollWheelZoom.disable());
  map.attributionControl.addAttribution(BASEMAP_ATTRIBUTION);

  const circles = new Map();
  const chips = [];
  const bounds = L.latLngBounds([]);
  areas.forEach((a, order) => {
    const circle = L.circle([a.lat, a.lng], { radius: a.radius, interactive: Boolean(a.href), ...circleStyle(false) });
    circle.addTo(map);
    circles.set(a.slug, { circle, bounds: areaBounds(a.lat, a.lng, a.radius) });
    bounds.extend(areaBounds(a.lat, a.lng, a.radius));
    /* The chip is anchored at the circle's centre; placeChips() decides on
       which side of the circle it sits, or shrinks it to a badge on it. */
    const chip = L.marker([a.lat, a.lng], {
      icon: L.divIcon({ className: "story-area-marker", html: chipHtml(a, journal), iconSize: null }),
      keyboard: false,
      interactive: Boolean(a.href),
      title: a.name,
      riseOnHover: true,
    }).addTo(map);
    chips.push({ a, chip, order });
    if (a.href) {
      const go = () => {
        window.location.hash = a.href.slice(1);
      };
      circle.on("click", go);
      chip.on("click", go);
    }
  });
  /* Room on the right for the chips, which prefer each circle's east side. */
  const fit = phone()
    ? { padding: [40, 40] }
    : { paddingTopLeft: [40, 40], paddingBottomRight: [journal ? 170 : 200, 40] };
  map.fitBounds(bounds, { ...fit, maxZoom: MAX_ZOOM });
  /* Busiest areas get their name first; ties keep the list's order. */
  chips.sort((x, y) => (y.a.count || 0) - (x.a.count || 0) || x.order - y.order);
  const startZoom = map.getZoom();
  const startSides = placeChips(map, chips, { framed: true });
  map.on("zoomend", () => placeChips(map, chips, map.getZoom() === startZoom ? { sides: startSides } : {}));

  overview = { map, base: null, circles };
  const base = await addBasemap(map, { tileJson: TILEJSON });
  if (!base) {
    /* The scripts or the TileJSON did not load: no map, the list stays. */
    map.remove();
    overview = null;
    canvas.hidden = true;
    return;
  }
  overview.base = base;
  if (pendingHighlight) highlight(pendingHighlight);
}

/* A mini map's link leads here: show its area. */
function highlight(slug) {
  pendingHighlight = slug;
  if (!overview) return;
  pendingHighlight = "";
  const area = overview.circles.get(slug);
  const item = document.querySelector(`.story-area-list li[data-area="${CSS.escape(slug)}"]`);
  if (item) {
    item.classList.add("is-active");
    window.setTimeout(() => item.classList.remove("is-active"), 2500);
  }
  if (!area) return;
  area.circle.setStyle(circleStyle(true));
  overview.map.flyToBounds(area.bounds, { padding: [48, 48], maxZoom: MAX_ZOOM, duration: 0.6 });
  window.setTimeout(() => area.circle.setStyle(circleStyle(false)), 2500);
}

/* ---- mini maps --------------------------------------------------------- */

function buildMini(el) {
  if (el.dataset.live) return;
  const lat = Number(el.dataset.lat);
  const lng = Number(el.dataset.lng);
  const radius = Number(el.dataset.radius);
  if (![lat, lng, radius].every(Number.isFinite)) return;

  const holder = document.createElement("div");
  holder.className = "journal-mini-canvas";
  el.prepend(holder);
  const map = L.map(holder, {
    zoomControl: false,
    dragging: false,
    touchZoom: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    boxZoom: false,
    keyboard: false,
    tap: false,
    maxZoom: MAX_ZOOM,
    zoomSnap: 0.25,
  });
  map.attributionControl.setPrefix(false);
  map.attributionControl.addAttribution(BASEMAP_ATTRIBUTION);
  const circle = L.circle([lat, lng], { radius, interactive: false, ...circleStyle(false) }).addTo(map);
  map.fitBounds(areaBounds(lat, lng, radius), { padding: [10, 10], maxZoom: MAX_ZOOM });

  const entry = { el, holder, map, circle, base: null };
  minis.add(entry);
  el.dataset.live = "1";
  enforceLimit();

  addBasemap(map, { tileJson: TILEJSON }).then((base) => {
    if (!minis.has(entry)) {
      if (base) base.remove();
      return;
    }
    if (!base) {
      destroyMini(entry);
      return;
    }
    entry.base = base;
  });
}

function destroyMini(entry) {
  if (!minis.has(entry)) return;
  minis.delete(entry);
  entry.map.remove();
  entry.holder.remove();
  delete entry.el.dataset.live;
}

/* How far an element is from the visible part of the page, in pixels. */
function distance(el) {
  const r = el.getBoundingClientRect();
  if (r.bottom < 0) return -r.bottom;
  if (r.top > window.innerHeight) return r.top - window.innerHeight;
  return 0;
}

function enforceLimit() {
  while (minis.size > MINI_LIMIT) {
    let furthest = null;
    for (const m of minis) if (!furthest || distance(m.el) > distance(furthest.el)) furthest = m;
    destroyMini(furthest);
  }
}

/* ---- wiring ---------------------------------------------------------------- */

function init() {
  const canvases = document.querySelectorAll("[data-story-map]");
  const miniEls = document.querySelectorAll("[data-mini-map]");
  if (!canvases.length && !miniEls.length) return;
  if (typeof L === "undefined" || !TILEJSON || !webgl2Available()) return;

  /* The space for the map is reserved now, so nothing jumps when it is built. */
  canvases.forEach((c) => (c.hidden = false));

  const nearOverview = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        nearOverview.unobserve(e.target);
        buildOverview(e.target);
      }
    },
    { rootMargin: "50% 0px" },
  );
  canvases.forEach((c) => nearOverview.observe(c));

  /* Two observers with a gap between them, so fast scrolling does not build and
     tear down the same map over and over. */
  const near = new IntersectionObserver(
    (entries) => {
      for (const e of entries) if (e.isIntersecting) buildMini(e.target);
    },
    { rootMargin: "50% 0px" },
  );
  const far = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) continue;
        for (const m of minis) if (m.el === e.target) destroyMini(m);
      }
    },
    { rootMargin: "200% 0px" },
  );
  miniEls.forEach((el) => {
    near.observe(el);
    far.observe(el);
  });

  document.querySelectorAll(".journal-mini-link[data-area]").forEach((a) => {
    a.addEventListener("click", () => highlight(a.dataset.area));
  });

  /* PaperMod sets data-theme on <html>: switch every live basemap's flavor and
     recolour the circles, whose accent changes with the theme. */
  new MutationObserver((mutations) => {
    if (!mutations.some((m) => m.attributeName === "data-theme")) return;
    const flavor = currentFlavor();
    if (overview) {
      if (overview.base) overview.base.setFlavor(flavor);
      overview.circles.forEach((a) => a.circle.setStyle(circleStyle(false)));
    }
    for (const m of minis) {
      if (m.base) m.base.setFlavor(flavor);
      m.circle.setStyle(circleStyle(false));
    }
  }).observe(document.documentElement, { attributes: true });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
else init();
