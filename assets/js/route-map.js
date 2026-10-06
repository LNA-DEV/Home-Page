/* {{< map >}}: a drive through a finished trip, in a post body.

   Each `[data-route-map]` element carries its waypoints (`data-points`, the
   shortcode's [{x: lat, y: lng}, …]) and, when the shortcode named a route, the
   committed road geometry (`data-route`, [[lng, lat], …] from
   assets/data/maps/routes/, written once by scripts/map-route.py). Nothing is
   routed in the browser and the basemap is the site's own (basemap.js), so the
   map sends the visitor to no third party
   (docs/concepts/self-hosted-maps.md §7). Without a route the waypoints are
   joined by straight lines. */

import * as params from "@params";
import { addBasemap, currentFlavor, BASEMAP_ATTRIBUTION } from "./basemap.js";

const TILEJSON = params.basemapTileJson || "";
const ROUTE_ATTRIBUTION = `${BASEMAP_ATTRIBUTION} · route &copy; OSRM`;

/* basemap handles, so a theme toggle can switch their flavor */
const bases = [];

function readJson(text, fallback) {
  try {
    return JSON.parse(text || "");
  } catch (err) {
    return fallback;
  }
}

function render(el) {
  const points = readJson(el.dataset.points, [])
    .filter((p) => p && typeof p.x === "number" && typeof p.y === "number")
    .map((p) => [p.x, p.y]);
  if (points.length < 2) return;
  const route = readJson(el.dataset.route, [])
    .filter((c) => Array.isArray(c) && c.length >= 2)
    .map(([lng, lat]) => [lat, lng]);
  const line = route.length > 1 ? route : points;

  /* The wheel zooms only after a click into the map, so a map in the middle of
     a post does not hijack scrolling past it — as the trip embed does. */
  const map = L.map(el, { scrollWheelZoom: false, maxZoom: 18 });
  map.on("click", () => map.scrollWheelZoom.enable());
  map.on("mouseout", () => map.scrollWheelZoom.disable());
  map.attributionControl.addAttribution(route.length > 1 ? ROUTE_ATTRIBUTION : BASEMAP_ATTRIBUTION);

  /* A white casing under the line keeps it readable on either flavor. */
  L.polyline(line, { color: "#fff", weight: 7, opacity: 0.8, lineCap: "round", lineJoin: "round" }).addTo(map);
  L.polyline(line, { color: "#185FA5", weight: 4, opacity: 0.95, lineCap: "round", lineJoin: "round" }).addTo(map);
  for (const p of points) L.marker(p, { keyboard: false }).addTo(map);
  map.fitBounds(L.latLngBounds(line), { padding: [30, 30] });

  /* After fitBounds: the layer reads the map's view the moment it is added. */
  addBasemap(map, { tileJson: TILEJSON }).then((base) => {
    if (base) bases.push(base);
  });
}

function init() {
  const maps = document.querySelectorAll("[data-route-map]");
  if (!maps.length || typeof L === "undefined") return;
  maps.forEach(render);
  new MutationObserver((mutations) => {
    if (!mutations.some((m) => m.attributeName === "data-theme")) return;
    const flavor = currentFlavor();
    bases.forEach((base) => base.setFlavor(flavor));
  }).observe(document.documentElement, { attributes: true });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
else init();
