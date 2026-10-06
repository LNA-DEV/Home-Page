/* Trip map + itinerary feed.
   Renders every `.trip-app[data-trip-slug]` on the page: fetches the trip,
   draws a Leaflet map with each leg's route, and a synced itinerary feed with a
   photo lightbox. Used by the /travel/<slug>/ detail page and the {{< trip >}} shortcode.

   Data source: the companion API `${tripsBaseUrl}/<slug>` (e.g.
   https://companion.lna-dev.net/api/trips/<slug>). `tripsBaseUrl` is wired in
   head.html and points at the local companion in dev. Photo `src` values are
   server-relative (`/api/trips/media/...`) and are resolved against the API
   origin (see `photoSrc`).

   The browser routes nothing. The companion computes each leg's road or rail
   geometry once, when the trip is saved, and delivers it as
   `transportIn.geometry` ([[lat, lng], …]); a leg without one — a flight, or a
   route not computed yet — is drawn straight through its manual via-points
   (`transportIn.waypoints`), A → via-points → B. The basemap is the site's own
   (basemap.js), so a trip page sends the visitor to no third party at all
   (docs/concepts/self-hosted-maps.md). Colors come from CSS variables so dark
   mode recolors the lines, and the basemap switches flavor with them. */

import * as params from "@params";
import { addBasemap, currentFlavor, BASEMAP_ATTRIBUTION } from "./basemap.js";

const TRIPS_BASE = (params.tripsBaseUrl || "/api/trips").replace(/\/$/, "");
const TILEJSON = params.basemapTileJson || "";

/* Photos come back with server-relative URLs (/api/trips/media/...) served by the
   companion, which is a different origin than the site — resolve them to absolute. */
const MEDIA_ORIGIN = (() => { try { return new URL(TRIPS_BASE, location.href).origin; } catch (e) { return ""; } })();
function photoSrc(p) { return p.src && p.src.charAt(0) === "/" ? MEDIA_ORIGIN + p.src : (p.src || ""); }

const T = {
  here: params.badgeHere || "here now",
  upcoming: params.badgeUpcoming || "upcoming",
  photosPending: params.photosPending || "Photos once we arrive",
  train: params.legendTrain || "train",
  flight: params.legendFlight || "flight",
  car: params.legendCar || "car",
  nowIn: params.nowIn || "Now in",
  updated: params.updated || "updated",
  youAreHere: params.youAreHere || "you are here",
  upcomingLegend: params.legendUpcoming || "upcoming",
  cities: params.statCities || "cities",
  countries: params.statCountries || "countries",
  days: params.statDays || "days",
  km: params.statKm || "km",
  close: params.closeTitle || "Close",
  prev: params.arrowPrevTitle || "Previous",
  next: params.arrowNextTitle || "Next",
  error: params.errorMsg || "Could not load this trip.",
  loading: params.loadingMsg || "Loading…",
  empty: params.emptyMsg || "No trips yet.",
  notFound: params.notFoundMsg || "Trip not found.",
};

const ICONS = { train: "🚆", flight: "✈", car: "🚗" };

/* The routes are the companion's (OSRM for roads, Transitous for rail), and
   Transitous asks for a visible link to its sources. */
const ATTRIBUTION = `${BASEMAP_ATTRIBUTION} · routes &copy; OSRM &amp; ` +
  `<a href="https://transitous.org/sources/">Transitous</a>`;

/* registry of rendered apps, so a theme toggle can recolor lines + the basemap */
const apps = [];

/* ---- helpers ---- */
function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}
function lineColors() {
  return {
    train: cssVar("--trip-train", "#1D9E75"),
    flight: cssVar("--trip-flight", "#BA7517"),
    car: cssVar("--trip-car", "#185FA5"),
  };
}
function relTime(iso) {
  if (!iso) return "";
  const diff = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(diff)) return "";
  const min = 60000, hr = 60 * min, day = 24 * hr;
  const rtf = new Intl.RelativeTimeFormat(document.documentElement.lang || "en", { numeric: "auto" });
  const abs = Math.abs(diff);
  if (abs < hr) return rtf.format(Math.round(diff / min), "minute");
  if (abs < day) return rtf.format(Math.round(diff / hr), "hour");
  return rtf.format(Math.round(diff / day), "day");
}

/* ---- shared lightbox (one per page, reused by every trip app) ---- */
let lb = null;
function ensureLightbox() {
  if (lb) return lb;
  const root = document.createElement("div");
  root.className = "trip-lb";
  root.setAttribute("role", "dialog");
  root.setAttribute("aria-modal", "true");
  root.innerHTML =
    `<button class="trip-lb-btn trip-lb-close" aria-label="${T.close}">&times;</button>` +
    `<button class="trip-lb-btn trip-lb-prev" aria-label="${T.prev}">&#8249;</button>` +
    `<button class="trip-lb-btn trip-lb-next" aria-label="${T.next}">&#8250;</button>` +
    `<div class="trip-lb-stage"><div class="trip-lb-img"></div>` +
    `<div class="trip-lb-cap"></div><div class="trip-lb-count"></div></div>`;
  document.body.appendChild(root);
  const img = root.querySelector(".trip-lb-img"),
    cap = root.querySelector(".trip-lb-cap"),
    count = root.querySelector(".trip-lb-count");
  const state = { photos: [], i: 0 };
  function render() {
    const ph = state.photos; if (!ph.length) return;
    const p = ph[state.i];
    if (p.src) { img.style.background = "#000"; img.innerHTML = `<img src="${photoSrc(p)}" alt="${p.cap || ""}">`; }
    else { img.style.background = p.tint || "#000"; img.style.color = "#5b574f"; img.innerHTML = `<span>${p.cap || ""}</span>`; }
    cap.textContent = p.cap || "";
    count.textContent = `${state.i + 1} / ${ph.length}`;
  }
  function open(photos, i) { state.photos = photos; state.i = i; render(); root.classList.add("open"); }
  function close() { root.classList.remove("open"); }
  function step(d) { const n = state.photos.length; if (!n) return; state.i = (state.i + d + n) % n; render(); }
  root.querySelector(".trip-lb-close").onclick = close;
  root.querySelector(".trip-lb-prev").onclick = () => step(-1);
  root.querySelector(".trip-lb-next").onclick = () => step(1);
  root.addEventListener("click", (e) => { if (e.target === root) close(); });
  document.addEventListener("keydown", (e) => {
    if (!root.classList.contains("open")) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowRight") step(1);
    if (e.key === "ArrowLeft") step(-1);
  });
  let sx = 0;
  img.addEventListener("touchstart", (e) => { sx = e.changedTouches[0].clientX; }, { passive: true });
  img.addEventListener("touchend", (e) => { const dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 40) step(dx < 0 ? 1 : -1); }, { passive: true });
  lb = { open };
  return lb;
}

/* shared thumbnail row used by both stays and transport legs */
function renderThumbs(container, photos) {
  const box = ensureLightbox();
  const MAX = 4, n = Math.min(photos.length, MAX);
  for (let k = 0; k < n; k++) {
    const p = photos[k], last = (k === MAX - 1 && photos.length > MAX);
    const b = document.createElement("button");
    b.className = "trip-thumb";
    b.setAttribute("aria-label", `Photo ${k + 1}: ${p.cap || ""}`);
    if (p.src) { b.innerHTML = `<img src="${photoSrc(p)}" alt="${p.cap || ""}">`; }
    else { b.style.background = p.tint; b.innerHTML = `<span class="trip-ph">${(p.cap || "").split(" ")[0]}</span>`; }
    if (last) b.innerHTML += `<span class="trip-more">+${photos.length - MAX + 1}</span>`;
    b.addEventListener("click", (e) => { e.stopPropagation(); box.open(photos, k); });
    container.appendChild(b);
  }
}

/* ---- render one trip into its container ---- */
function renderTrip(appEl, data, mode) {
  const stops = data.stops || [];
  if (!stops.length) { appEl.innerHTML = `<p class="trip-error">${T.error}</p>`; return; }

  appEl.innerHTML = "";

  /* header: title (embed only — page has its own <h1>), now-line, stats */
  const header = document.createElement("header");
  header.className = "trip-header";
  const current = stops.find((s) => s.status === "current") || stops.find((s) => s.id === data.current);
  let nowHtml = "";
  if (current) {
    const rel = relTime(data.updatedAt);
    nowHtml = `<span class="trip-now"><span class="trip-dot"></span>${T.nowIn} <b>${current.name}</b>` +
      (rel ? ` · ${T.updated} ${rel}` : "") + `</span>`;
  }
  const stats = buildStats(data);
  const statsHtml = stats.length
    ? `<div class="trip-stats">${stats.map((s) => `<div class="trip-stat"><b>${s.value}</b><span>${s.label}</span></div>`).join("")}</div>`
    : "";
  header.innerHTML =
    (mode === "embed" && data.title ? `<h3 class="trip-app-title">${data.title}</h3>` : "") +
    nowHtml + statsHtml;
  appEl.appendChild(header);

  /* layout: map + feed */
  const main = document.createElement("div");
  main.className = "trip-main";
  const mapEl = document.createElement("div");
  mapEl.className = "trip-map";
  const feedWrap = document.createElement("div");
  feedWrap.className = "trip-feed-wrap";
  const feed = document.createElement("div");
  feed.className = "trip-feed";
  feedWrap.appendChild(feed);
  main.appendChild(mapEl);
  main.appendChild(feedWrap);
  appEl.appendChild(main);

  if (typeof L === "undefined") { return; } // Leaflet failed to load

  /* ---- map ---- */
  const C = lineColors();
  const embed = mode === "embed";
  /* maxZoom is set here: it used to come from the raster tile layer, and the
     basemap layer below is not a tile layer Leaflet could read it from. */
  const map = L.map(mapEl, { scrollWheelZoom: !embed, zoomControl: true, maxZoom: 19 });
  if (embed) {
    // don't hijack page scroll inside a post — click the map to enable wheel-zoom, leave it to disable
    map.on("click", () => map.scrollWheelZoom.enable());
    map.on("mouseout", () => map.scrollWheelZoom.disable());
  }
  map.attributionControl.addAttribution(ATTRIBUTION);

  const reg = {}; // id -> { marker, card, leg, polyline }
  const polylines = []; // { pl, mode, upcoming }

  stops.forEach((s) => {
    const cls = s.status === "current" ? "trip-pin-current"
      : s.status === "upcoming" ? "trip-pin-upcoming" : "trip-pin-visited";
    const marker = L.marker([s.lat, s.lng], {
      icon: L.divIcon({ className: "trip-pin-host", html: `<span class="trip-pin ${cls}"></span>`, iconSize: [14, 14], iconAnchor: [7, 7] }),
      keyboard: true, title: s.name,
    }).addTo(map);
    marker.bindTooltip(s.name, { direction: "top", offset: [0, -8] });
    reg[s.id] = { marker };
  });

  /* route polylines, keyed to the leg's destination stop */
  for (let i = 1; i < stops.length; i++) {
    const a = stops[i - 1], b = stops[i];
    const m = b.transportIn ? b.transportIn.mode : "train";
    const upcoming = b.status === "upcoming";
    /* Manual via-points (transportIn.waypoints) correct the drawn route: the
       straight fallback here, and the companion's routing, run A → via-points → B. */
    const vias = (b.transportIn && Array.isArray(b.transportIn.waypoints) ? b.transportIn.waypoints : [])
      .filter((w) => w && (w.lat || w.lng));
    const path = [a, ...vias, b];
    const pl = L.polyline(path.map((p) => [p.lat, p.lng]), {
      color: C[m] || C.train, weight: 3, opacity: upcoming ? 0.45 : 0.9,
      dashArray: m === "flight" ? "2 8" : (upcoming ? "7 7" : null), lineCap: "round",
    }).addTo(map);
    reg[b.id].polyline = pl;
    polylines.push({ pl, mode: m, upcoming });

    /* The companion's stored road/rail geometry. Without one the straight
       line through the via-points stays, dashed for a flight. */
    const preset = b.transportIn && b.transportIn.geometry;
    if (preset && preset.length > 1) {
      pl.setLatLngs(preset);
      pl.setStyle({ dashArray: upcoming ? "7 7" : null });
    }
  }

  map.fitBounds(stops.map((s) => [s.lat, s.lng]), { padding: [45, 45] });
  setTimeout(() => map.invalidateSize(), 0);

  /* After fitBounds: the layer reads the map's view the moment it is added.
     Resolves to null without WebGL2, and the lines and pins stay on their own. */
  const app = { map, base: null, polylines };
  addBasemap(map, { tileJson: TILEJSON }).then((base) => {
    if (!base) return;
    // the view was torn down meanwhile
    if (!apps.includes(app)) { try { base.remove(); } catch (e) {} return; }
    app.base = base;
  });

  /* legend (swatch colors come from CSS, so they recolor with the theme) */
  const legend = L.control({ position: "bottomright" });
  legend.onAdd = function () {
    const d = L.DomUtil.create("div", "trip-legend");
    d.innerHTML =
      `<div class="row"><span class="ln train"></span>${T.train}</div>` +
      `<div class="row"><span class="ln flight"></span>${T.flight}</div>` +
      `<div class="row"><span class="ln car"></span>${T.car}</div>` +
      `<div class="row"><span class="pt here"></span>${T.youAreHere}</div>` +
      `<div class="row"><span class="pt upcoming"></span>${T.upcomingLegend}</div>`;
    return d;
  };
  legend.addTo(map);

  /* ---- feed ---- */
  function activate(id, { scroll = false, marker = false } = {}) {
    const r = reg[id]; if (!r) return;
    r.card.classList.add("active");
    const el = r.marker.getElement(); if (el) el.classList.add("active");
    if (marker) r.marker.openTooltip();
    if (scroll) feed.scrollTo({ top: r.card.offsetTop - 14, behavior: "smooth" });
  }
  function deactivate(id) {
    const r = reg[id]; if (!r) return;
    r.card.classList.remove("active");
    const el = r.marker.getElement(); if (el) el.classList.remove("active");
    r.marker.closeTooltip();
  }
  function bumpLine(id, on) {
    const r = reg[id]; if (!r || !r.polyline) return;
    r.polyline.setStyle({ weight: on ? 6 : 3, opacity: on ? 1 : (r.card.classList.contains("upcoming") ? 0.45 : 0.9) });
  }

  stops.forEach((s, i) => {
    // A transport leg connects to the *previous* stop, so it only renders from
    // the second stop on (mirrors the polyline loop starting at i=1). Guards
    // against API data where the first stop carries a transportIn.
    if (s.transportIn && i > 0) {
      const leg = document.createElement("div");
      leg.className = "trip-leg" + (s.status === "upcoming" ? " upcoming" : "");
      const m = s.transportIn.mode;
      leg.innerHTML =
        `<div class="trip-leg-row">` +
        `<span class="trip-ic ${m}">${ICONS[m] || ICONS.train}</span>` +
        `<span>${stops[i - 1].name} → ${s.name}</span>` +
        `<span class="trip-meta">${s.transportIn.label} · ${s.transportIn.duration}${s.status === "upcoming" ? " · " + T.upcoming : ""}</span>` +
        `</div>`;
      if (s.transportIn.photos && s.transportIn.photos.length) {
        const t = document.createElement("div"); t.className = "trip-thumbs compact";
        renderThumbs(t, s.transportIn.photos);
        leg.appendChild(t);
      }
      leg.addEventListener("mouseenter", () => { leg.classList.add("active"); bumpLine(s.id, true); });
      leg.addEventListener("mouseleave", () => { leg.classList.remove("active"); bumpLine(s.id, false); });
      feed.appendChild(leg);
      reg[s.id].leg = leg;
    }

    const card = document.createElement("div");
    card.className = "trip-stay" + (s.status === "current" ? " current" : "") + (s.status === "upcoming" ? " upcoming" : "");
    card.tabIndex = 0;
    const badge = s.status === "current" ? `<span class="trip-badge here">${T.here}</span>`
      : s.status === "upcoming" ? `<span class="trip-badge soon">${T.upcoming}</span>` : "";
    card.innerHTML =
      `<div class="trip-stay-head"><span class="trip-stay-name">${s.name}${badge}</span>` +
      `<span class="trip-dates">${s.dates || ""}</span></div>` +
      (s.note ? `<p class="trip-note">${s.note}</p>` : "");

    const thumbs = document.createElement("div"); thumbs.className = "trip-thumbs";
    if (!s.photos || !s.photos.length) { thumbs.innerHTML = `<span class="trip-empty-note">${T.photosPending}</span>`; }
    else { renderThumbs(thumbs, s.photos); }
    card.appendChild(thumbs);

    card.addEventListener("mouseenter", () => activate(s.id, { scroll: false, marker: true }));
    card.addEventListener("mouseleave", () => deactivate(s.id));
    card.addEventListener("focus", () => activate(s.id, { scroll: false, marker: true }));
    card.addEventListener("blur", () => deactivate(s.id));
    card.addEventListener("click", () => map.flyTo([s.lat, s.lng], Math.max(map.getZoom(), 6), { duration: 0.6 }));
    feed.appendChild(card);
    reg[s.id].card = card;
  });

  stops.forEach((s) => {
    const m = reg[s.id].marker;
    m.on("mouseover", () => activate(s.id, { scroll: true }));
    m.on("mouseout", () => deactivate(s.id));
    m.on("click", () => activate(s.id, { scroll: true }));
  });

  apps.push(app);
}

/* The API returns stats as an object { daysElapsed, daysTotal, cities, countries,
   distanceKm }; cities/countries fall back to deriving from the stops. */
function buildStats(data) {
  const stops = data.stops || [];
  const st = data.stats || {};
  const out = [];

  const cities = typeof st.cities === "number" ? st.cities : stops.length;
  out.push({ value: String(cities), label: T.cities });

  let countries = typeof st.countries === "number" ? st.countries : null;
  if (countries == null) {
    const set = new Set(stops.map((s) => s.country).filter(Boolean));
    countries = set.size || null;
  }
  if (countries) out.push({ value: String(countries), label: T.countries });

  if (st.daysElapsed != null && st.daysTotal != null)
    out.push({ value: `${st.daysElapsed} / ${st.daysTotal}`, label: T.days });

  if (st.distanceKm != null)
    out.push({ value: Number(st.distanceKm).toLocaleString(document.documentElement.lang || "en"), label: T.km });

  return out;
}

/* recolor lines + switch the basemap's flavor when the site theme toggles */
function refreshTheme() {
  const C = lineColors();
  const flavor = currentFlavor();
  apps.forEach(({ base, polylines }) => {
    if (base) base.setFlavor(flavor);
    polylines.forEach(({ pl, mode, upcoming }) => {
      pl.setStyle({ color: C[mode] || C.train, opacity: upcoming ? 0.45 : 0.9 });
    });
  });
}

/* ---- index page: card list + #slug hash router ---- */

/* Leaflet maps from a previous view must be explicitly disposed, otherwise the
   theme observer keeps recoloring detached maps and they leak between routes. */
function teardownApps() {
  apps.forEach((a) => { try { a.map.remove(); } catch (e) {} });
  apps.length = 0;
}

function loadTrip(appEl, slug, mode) {
  appEl.innerHTML = `<div class="trip-loading">${T.loading}</div>`;
  return fetch(`${TRIPS_BASE}/${slug}`)
    .then((r) => {
      // Unknown slug → 404: a "not found", not a load failure.
      if (r.status === 404) { appEl.innerHTML = `<p class="trip-empty">${T.notFound}</p>`; return null; }
      if (!r.ok) throw new Error(r.status);
      return r.json();
    })
    .then((data) => { if (data) renderTrip(appEl, data, mode); })
    .catch(() => { appEl.innerHTML = `<p class="trip-error">${T.error}</p>`; });
}

/* compact "N cities · M countries" line for a list card */
function statSummary(st) {
  if (!st) return "";
  const parts = [];
  if (typeof st.cities === "number") parts.push(`${st.cities} ${T.cities}`);
  if (typeof st.countries === "number" && st.countries) parts.push(`${st.countries} ${T.countries}`);
  return parts.join(" · ");
}

function renderList(host) {
  host.innerHTML = `<div class="trip-loading">${T.loading}</div>`;
  fetch(TRIPS_BASE)
    .then((r) => {
      // No trip collection yet (or none published) reads as 404/204 — that's an
      // empty list, not a load failure, so don't fall through to the error state.
      if (r.status === 404 || r.status === 204) return [];
      if (!r.ok) throw new Error(r.status);
      return r.json();
    })
    .then((trips) => {
      if (!Array.isArray(trips) || !trips.length) {
        host.innerHTML = `<p class="trip-empty">${T.empty}</p>`;
        return;
      }
      const cards = trips.map((t) => {
        const cover = t.cover && t.cover.src ? photoSrc(t.cover) : "";
        const sub = statSummary(t.stats);
        return `<a class="trip-card${cover ? "" : " trip-card-nocover"}" href="#${encodeURIComponent(t.slug)}"` +
          (cover ? ` style="--trip-cover: url('${cover}')"` : "") + `>` +
          `<div class="trip-card-body">` +
          `<h2 class="trip-card-title">${t.title || ""}</h2>` +
          (sub ? `<p class="trip-card-sub">${sub}</p>` : "") +
          (t.dateRange ? `<span class="trip-card-dates">${t.dateRange}</span>` : "") +
          `</div></a>`;
      }).join("");
      host.innerHTML = `<section class="trip-cards">${cards}</section>`;
    })
    .catch(() => { host.innerHTML = `<p class="trip-error">${T.error}</p>`; });
}

function renderDetail(host, slug, onTitle) {
  host.innerHTML = `<div class="trip-loading">${T.loading}</div>`;
  fetch(`${TRIPS_BASE}/${slug}`)
    .then((r) => {
      // Unknown slug → 404: show "not found" rather than the generic error.
      if (r.status === 404) { host.innerHTML = `<p class="trip-empty">${T.notFound}</p>`; return null; }
      if (!r.ok) throw new Error(r.status);
      return r.json();
    })
    .then((data) => {
      if (!data) return;                                // 404 handled above
      if (onTitle) onTitle(data.title || "");           // fill the "/ <trip>" path + title
      host.innerHTML = "";
      const appEl = document.createElement("div");
      appEl.className = "trip-app trip-mode-page";
      host.appendChild(appEl);
      renderTrip(appEl, data, "page");
    })
    .catch(() => { host.innerHTML = `<p class="trip-error">${T.error}</p>`; });
}

/* hash route: #<slug> shows a trip, empty hash shows the card list. The shared
   centered header (breadcrumb path + title) is rebuilt per route — gallery-style. */
function initIndex(host) {
  const head = document.querySelector("[data-trip-head]");
  const meta = head ? head.dataset : {};
  const listHeadHTML = head ? head.innerHTML : "";

  function crumb(parts) {
    return `<nav class="trip-breadcrumb" aria-label="Breadcrumb">` +
      parts.map((p, i) =>
        (p.href != null ? `<a href="${p.href}">${p.label}</a>` : `<span>${p.label}</span>`) +
        (i < parts.length - 1 ? "<span>/</span>" : "")
      ).join("") +
      `</nav>`;
  }
  function setListHead() { if (head) head.innerHTML = listHeadHTML; }
  function setDetailHead(title) {
    if (!head) return;
    const parts = [{ label: meta.homeLabel || "Home", href: meta.homeUrl || "/" }];
    if (title) {
      parts.push({ label: meta.section || "", href: "#" });   // back to the list
      parts.push({ label: title });
    } else {
      parts.push({ label: meta.section || "" });               // loading: trip name not known yet
    }
    head.innerHTML = crumb(parts) + (title ? `<h1 class="trip-index-title">${title}</h1>` : "");
  }

  function route() {
    teardownApps();
    const slug = decodeURIComponent((location.hash || "").replace(/^#/, "")).trim();
    if (slug) { setDetailHead(""); renderDetail(host, slug, setDetailHead); }
    else { setListHead(); renderList(host); }
    window.scrollTo({ top: 0 });
  }
  window.addEventListener("hashchange", route);
  route();
}

/* ---- boot ---- */
function init() {
  const indexEl = document.querySelector("[data-trip-index]");
  const embeds = document.querySelectorAll(".trip-app[data-trip-slug]");
  if (!indexEl && !embeds.length) return;

  if (indexEl) initIndex(indexEl);

  // {{< trip >}} shortcode embeds (and any standalone app) render in place
  embeds.forEach((appEl) => {
    const mode = appEl.classList.contains("trip-mode-embed") ? "embed" : "page";
    loadTrip(appEl, appEl.dataset.tripSlug, mode);
  });

  new MutationObserver((muts) => {
    if (muts.some((m) => m.attributeName === "data-theme")) refreshTheme();
  }).observe(document.documentElement, { attributes: true });
  window.addEventListener("resize", () => apps.forEach(({ map }) => map.invalidateSize()));
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
else init();
