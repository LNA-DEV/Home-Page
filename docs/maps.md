# Maps: the site's own basemap

Design: `docs/concepts/self-hosted-maps.md`. **No map on the site sends a visitor to a third party** — not the dex, not the trips, not the `{{< map >}}` shortcode — and `tests/static/maps.spec.ts` fails the build if any built file names `tile.openstreetmap.org`, `basemaps.cartocdn.com`, `router.project-osrm.org`, `api.transitous.org` or `api.gbif.org` again.

- **The basemap** is the Protomaps planet build of OpenStreetMap (vector tiles, z0–15, schema 4.x), which the companion copies into its own S3 bucket every month and serves as `<companion>/api/tiles/basemap.json` (TileJSON) → `<companion>/api/tiles/basemap/<YYYYMMDD>/{z}/{x}/{y}.mvt`. `head.html` passes that TileJSON URL to every map script through `@params` (`basemapTileJson`; `localhost:8080` under `hugo server`, like `tripsBaseUrl`).
- **`assets/js/basemap.js`** is the one shared module: `addBasemap(map, {tileJson, pane})` adds the basemap to an ordinary Leaflet map and resolves to a handle (`setFlavor`, `remove`), or to **null** when it cannot be shown — then the caller's map simply stays as it was. Without WebGL2 it also puts a translated note into the map field (`.basemap-notice`, i18n `basemap_no_webgl`, styles in `assets/css/extended/basemap.css`; it takes no clicks), which the dex removes again when "detailed map" is switched off; `tests/support/webgl.ts` simulates such a browser. It loads MapLibre GL only when asked (the dex: after its click), fetches the TileJSON once per page however many maps there are, and marks its container `data-flavor="light|dark"`, which the tests read.
- **MapLibre draws inside Leaflet** via `@maplibre/maplibre-gl-leaflet`, so `dex-map.js` keeps its panes, ±360° copies and ocean mask, and `travel.js` its lines and pins. MapLibre 6 is **ES modules only**; the plugin and `@protomaps/basemaps` are classic scripts that read `window.maplibregl` / define `window.basemaps`, so `basemap.js` imports the module, publishes it, then loads the two scripts — the load order matters. MapLibre 6 needs **WebGL2**; without it (Tor Browser at stricter levels, old phones) `addBasemap` resolves to null.
- **Dark mode is a flavor, not other tiles**: `light` / `dark` from `@protomaps/basemaps`, switched with `setStyle` when PaperMod's `data-theme` changes. Labels are in the page language (`lang`, en/de/sv). `waterColor(flavor)` is the flavor's sea, which the dex's ocean mask must match.
- **Vendored under `static/packages/`**, nothing from a CDN: `maplibre-gl/` (6.12.0, the three `.mjs` files + CSS, ~300 KB gzipped), `maplibre-gl-leaflet/` (0.1.4), `protomaps-basemaps/` (5.7.2 — **its major version is paired with the tile schema's**: 5.x draws schema 4.x; a schema-5 tileset needs a new style package), `protomaps-assets/` (glyphs + v4 sprites, pinned commit and licences in its README). Upstream's Devanagari font ranges are symlinks; they are real copies here because Hugo does not publish symlinks.
- **Trips route nothing in the browser.** The companion computes each leg's road (OSRM) or rail (Transitous) geometry when a trip is saved and delivers it as `transportIn.geometry`; a leg without one stays a straight line. The attribution links `transitous.org/sources/`, which Transitous's policy asks for.
- **`{{< map coordinates=… route="<name>" >}}`** draws `assets/data/maps/routes/<name>.geojson`, inlined into the page (not a bundle resource — that would publish it). Write one with `python3 scripts/map-route.py <name> <lat,lng> <lat,lng> …` (OSRM's full geometry, thinned to ~50 m, once). A `route` with no file is an `errorf` naming the page; without `route` the waypoints are joined by straight lines. `assets/js/route-map.js` is the wiring, loaded by `head.html` on pages with the shortcode. leaflet-routing-machine is gone.

## A route map in a post

`{{< map coordinates="…" route="<name>" >}}` draws a committed route over the
site's own basemap; nothing is routed in the visitor's browser
(`docs/concepts/self-hosted-maps.md` §7). The route is fetched once:

```
python3 scripts/map-route.py <name> <lat,lng> <lat,lng> [<lat,lng> …]
python3 scripts/map-route.py <name> … --dry-run     # print the request only
python3 scripts/map-route.py <name> … --force       # replace an existing route
```

- One OSRM request (driving, the public demo server) per run, then a one-second
  pause, so a shell loop over several routes stays within its limit.
- It writes `assets/data/maps/routes/<name>.geojson`: OSRM's full geometry,
  thinned to `--tolerance` degrees (default 0.0005, ~50 m), rounded to 5
  decimals. A 1,400 km drive comes out at ~1,200 points and ~25 KB, inlined into
  the page.
- `<name>` is lowercase-with-dashes; give the points in driving order, the same
  ones the shortcode's `coordinates` lists.
- Then add `route="<name>"` to the shortcode. A `route` with no file stops the
  build; leaving `route` off draws straight lines.

The script only writes the file; commit it yourself. Do **not** run
`./deploy.sh` afterwards — that is a separate, explicitly authorised step.
