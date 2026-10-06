/* The site's own basemap, shared by every Leaflet map that wants one.

   Vector tiles of OpenStreetMap (the Protomaps planet build) come from the
   companion, which copies the build into our own storage every month — so no
   map on this site sends a visitor to a tile server, a CDN or a font host
   (docs/concepts/self-hosted-maps.md). MapLibre GL draws them *inside* an
   ordinary Leaflet map through @maplibre/maplibre-gl-leaflet, which is what lets
   dex-map.js keep its panes, its ±360° copies and its ocean mask, and travel.js
   its markers and lines.

   MapLibre is ~300 KB gzipped, so nothing here loads until a caller asks for a
   basemap: the dex only after its "detailed map" click. Glyphs and sprites are
   vendored under /packages/protomaps-assets/.

   Everything degrades rather than breaks. MapLibre needs WebGL2; where there is
   none (Tor Browser at a stricter security level, an old phone) or the scripts
   fail to load, addBasemap() resolves to null and the caller's map stays as it
   was — the dex keeps its drawn world, a trip its lines and pins. Without WebGL
   the map also says so, in a note inside the map field, so nobody is left
   looking at an empty map without knowing why. */

import * as params from "@params";

const PACKAGES = "/packages";

/* Every map script passes this through its own @params (head.html). */
const NO_WEBGL_TEXT =
  params.basemapNoWebgl || "The background map needs WebGL, which is turned off or unavailable in this browser.";

export const BASEMAP_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' +
  ' · <a href="https://protomaps.com">Protomaps</a>';

/* Labels the style knows; anything else falls back to English. */
const LANGS = ["en", "de", "sv"];

let loading = null;
/* TileJSON URL → promise of the source it describes, so a page with six maps
   asks the companion once rather than once per map. */
const sources = new Map();

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = resolve;
    s.onerror = () => reject(new Error(`could not load ${src}`));
    document.head.appendChild(s);
  });
}

function loadStylesheet(href) {
  if (document.querySelector(`link[href="${href}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = href;
  document.head.appendChild(link);
}

function webgl2Available() {
  try {
    return !!document.createElement("canvas").getContext("webgl2");
  } catch (err) {
    return false;
  }
}

/* MapLibre 6 ships as ES modules only, while the Leaflet plugin and the style
   builder are classic scripts that read `maplibregl` / define `basemaps` on
   window. So: import the module, publish it, then load the two scripts. Once
   per page, whoever asks first. */
export function loadBasemap() {
  if (!loading) {
    loading = (async () => {
      if (typeof L === "undefined") throw new Error("Leaflet is not loaded");
      if (!webgl2Available()) throw new Error("no WebGL2");
      loadStylesheet(`${PACKAGES}/maplibre-gl/maplibre-gl.css`);
      const maplibre = await import(`${location.origin}${PACKAGES}/maplibre-gl/maplibre-gl.mjs`);
      window.maplibregl = maplibre;
      await Promise.all([
        loadScript(`${PACKAGES}/maplibre-gl-leaflet/leaflet-maplibre-gl.js`),
        loadScript(`${PACKAGES}/protomaps-basemaps/basemaps.js`),
      ]);
      if (typeof L.maplibreGL !== "function" || typeof window.basemaps === "undefined") {
        throw new Error("basemap scripts did not initialise");
      }
    })();
  }
  return loading;
}

/* The note inside the map field when the basemap cannot be drawn for want of
   WebGL. It takes no clicks, so the map underneath stays usable. */
function showNoWebglNotice(map) {
  const container = map.getContainer();
  if (container.querySelector(".basemap-notice")) return;
  const note = L.DomUtil.create("div", "basemap-notice", container);
  note.setAttribute("role", "note");
  note.textContent = NO_WEBGL_TEXT;
}

/* Take the note away again (the dex, when "detailed map" is switched off). */
export function clearBasemapNotice(map) {
  const note = map.getContainer().querySelector(".basemap-notice");
  if (note) note.remove();
}

/* The flavor follows the site theme: PaperMod sets data-theme on <html>. */
export function currentFlavor() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function pageLang() {
  const lang = (document.documentElement.lang || "en").slice(0, 2).toLowerCase();
  return LANGS.includes(lang) ? lang : "en";
}

/* The style's water colour, for anything drawn on top that has to match the
   sea beneath it (the dex's ocean mask). Only valid once loadBasemap() resolved. */
export function waterColor(flavor) {
  return window.basemaps.namedFlavor(flavor).water;
}

/* The companion's TileJSON names the active version's tile URL; the version is
   in that URL, which is what lets the tiles themselves be cached for good. */
function loadSource(tileJson) {
  if (!sources.has(tileJson)) {
    sources.set(
      tileJson,
      fetch(tileJson)
        .then((response) => {
          if (!response.ok) throw new Error(`${tileJson} answered ${response.status}`);
          return response.json();
        })
        .then((tj) => {
          if (!Array.isArray(tj.tiles) || !tj.tiles.length) throw new Error(`${tileJson} names no tiles`);
          const source = { type: "vector", tiles: tj.tiles };
          for (const key of ["minzoom", "maxzoom", "bounds"]) if (tj[key] != null) source[key] = tj[key];
          return source;
        })
    );
  }
  return sources.get(tileJson);
}

function style(source, flavor, lang) {
  /* MapLibre resolves glyph and sprite URLs on its own, outside the page's
     base, so both are absolute. */
  return {
    version: 8,
    glyphs: `${location.origin}${PACKAGES}/protomaps-assets/fonts/{fontstack}/{range}.pbf`,
    sprite: `${location.origin}${PACKAGES}/protomaps-assets/sprites/v4/${flavor}`,
    sources: { protomaps: source },
    layers: window.basemaps.layers("protomaps", window.basemaps.namedFlavor(flavor), { lang }),
  };
}

/* Add the basemap to a Leaflet map. Resolves to a handle, or to null when the
   basemap cannot be shown — the caller then simply goes on without one.

     handle.flavor           the flavor currently drawn
     handle.setFlavor(f)     redraw in another flavor (theme toggle)
     handle.remove()         take it off the map again

   The attribution is the caller's to place, via BASEMAP_ATTRIBUTION: MapLibre's
   own control is off, because inside a Leaflet map it would draw a second one. */
export async function addBasemap(map, { tileJson, pane } = {}) {
  if (!tileJson) return null;
  if (!webgl2Available()) {
    showNoWebglNotice(map);
    return null;
  }
  let source;
  try {
    [source] = await Promise.all([loadSource(tileJson), loadBasemap()]);
  } catch (err) {
    console.warn(`[basemap] not shown: ${err.message}`);
    return null;
  }

  const lang = pageLang();
  let flavor = currentFlavor();
  const layer = L.maplibreGL({
    style: style(source, flavor, lang),
    attributionControl: false,
    pane: pane || "tilePane",
  });
  try {
    layer.addTo(map);
  } catch (err) {
    /* WebGL2 was there a moment ago but MapLibre could not get a context after
       all. Leaflet already registered the layer, so undo that by hand —
       removeLayer() would call into the map MapLibre never created. */
    console.warn(`[basemap] not shown: ${err.message}`);
    showNoWebglNotice(map);
    if (map.hasLayer(layer)) {
      map.off(layer.getEvents(), layer);
      delete map._layers[L.stamp(layer)];
    }
    const el = layer.getContainer && layer.getContainer();
    if (el && el.parentNode) el.parentNode.removeChild(el);
    return null;
  }

  const glMap = layer.getMaplibreMap();
  if (!glMap) {
    /* The map was removed while the scripts loaded, so Leaflet only queued the
       layer for a "load" that will never come. */
    delete map._layers[L.stamp(layer)];
    return null;
  }
  /* A tile that fails to load is not worth a console error on the page, and
     MapLibre logs one when nobody listens. */
  glMap.on("error", (e) => console.warn(`[basemap] ${(e && e.error && e.error.message) || e}`));

  const container = layer.getContainer();
  container.dataset.flavor = flavor;

  return {
    get flavor() {
      return flavor;
    },
    setFlavor(next) {
      if (next === flavor || !layer.getMaplibreMap()) return;
      flavor = next;
      container.dataset.flavor = flavor;
      layer.getMaplibreMap().setStyle(style(source, flavor, lang));
    },
    remove() {
      if (map.hasLayer(layer)) map.removeLayer(layer);
    },
  };
}
