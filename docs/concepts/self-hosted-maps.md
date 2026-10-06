# Concept: maps without third parties — own basemap, server-side routing

**Status:** implemented on 2026-10-06 in Home-Page and HomePageCompanion, **not deployed and not committed**. The open decisions were settled by the owner the same day. What differs from the plan below, and what is still open, is in *As built* at the end. Spans three repositories:
- this one: frontend and tests;
- `HomePageCompanion`: tile serving, the update job, routing, the GBIF proxy;
- `Web-Services`: secrets and the image tag.

**Read against:**
- Home-Page `c2eb7f8`, HomePageCompanion `43708a7`.
- The Protomaps build `20261005` (schema `4.15.2`), read on 2026-10-06 through range requests.
- MapLibre GL JS 6.12.0, go-pmtiles v1.31.2.
- Hetzner's documentation of the same day.

Every map on the site except the dex's default view sends the visitor's browser to third parties. Some of them are demo servers, and the travel page does it on load. This concept makes the companion the only map host a browser ever talks to:
- **The basemap** is Protomaps' planet build of OpenStreetMap, copied into our own S3 bucket every month and served by the companion as vector tiles.
- **Routing** is done once, when a trip is saved, and stored.
- **GBIF's density overlay** goes through the companion.

A static test then holds the result: no built file may name another map host.

## Settled decisions

| | |
|---|---|
| Basemap | Protomaps planet build, vector tiles, **z0–15, copied whole**: 138.6 GB (build `20261005`). No extract |
| Storage | Hetzner Object Storage, bucket in **`nbg1`**, the web server's location (whois on `lna-dev.net`: `CLOUD-NBG1`). Companion↔S3 traffic is then internal and free. The base package suffices (§3) |
| Key layout | **One folder for the companion, one subfolder per module:** `home-page-companion/<module>/…`. The basemap lives under `home-page-companion/maps/basemap/<YYYYMMDD>.pmtiles`. Settled by the owner on 2026-10-06 so other companion modules can share the bucket later (§3) |
| What the browser talks to | `companion.lna-dev.net` only. The bucket is private and never addressed by a browser |
| Update | A companion cron job, **monthly**. It streams the file part by part into a multipart upload, with no local copy. The new version goes live only after verification (§5) |
| Renderer | MapLibre GL JS **inside Leaflet**, via `@maplibre/maplibre-gl-leaflet`, so the Leaflet code stays. This holds only if the spike passes (§11 step 0) |
| Dark mode | Protomaps flavors `light` / `dark`: the same tiles with a different style. It follows `data-theme` |
| Labels | In the page language (`en` / `de` / `sv`), through the style's `lang` option |
| Fonts, sprites | Vendored under `static/packages/protomaps-assets/`. Same origin, ~11.7 MB, OFL |
| Routing | Computed by the companion when a trip is saved, stored, and delivered as `transportIn.geometry`. The browser routes nothing |
| GBIF density | Through the companion with a fixed parameter set, **cached on the companion's disk** (§8) |
| Dex "detailed map" button | **Kept as the opt-in, for now.** The local first paint stays the default. Revisit once the basemap has run for a while |
| Tor | **The onion origin goes into the companion's CORS** (§9). Maps, trips and likes then work on the onion, through a Tor exit node |
| `{{< map >}}` (4 maps in `posts/resa/sverige/2024`) | **Routes precomputed once** and committed as GeoJSON under `assets/data/maps/routes/` (§7) |
| Guard | A static test fails if any built file names a map host other than the companion (§10) |

## Still open

The spike (§11 step 0) answered all but one of its questions; see *As built*. Open: **WebGL in Tor Browser** was not checked — there was no Tor Browser to check it in. Without WebGL2 the maps fall back as §9 describes.

---

## 1. What reaches third parties today

| Where | Host, from the visitor's browser | When |
|---|---|---|
| `assets/js/dex-map.js:346`, "detailed map" | `{s}.tile.openstreetmap.org` | after a click |
| `assets/js/dex-map.js:353` | `api.gbif.org` (density tiles) | after a click |
| `assets/js/travel.js:76` | `{s}.basemaps.cartocdn.com` (light / dark) | **on load** |
| `assets/js/travel.js:51` | `router.project-osrm.org`, `api.transitous.org` | **on load, once per leg** |
| `layouts/shortcodes/map.html` | `{s}.tile.openstreetmap.org`, plus leaflet-routing-machine → OSRM demo | on load |

Problems with these, apart from privacy:
- **OSM tiles.** OSM's tile policy asks for exactly `tile.openstreetmap.org`. Other hostnames "may be slower or withdrawn without notice", and the `{s}` subdomains are exactly that.
- **OSRM demo server.** At most 1 request/s, non-commercial use only, no uptime guarantee. The travel page calls it from every visitor's browser.
- **Transitous.** Its policy asks to be contacted *before* anyone uses the routing endpoints, and to link `https://transitous.org/sources/` visibly. The travel page's attribution has no such link.

## 2. The basemap data

Read from the build's own header and metadata (range requests, 2026-10-06):

| | |
|---|---|
| Format | PMTiles spec v3, MVT tiles, gzip, internal compression gzip |
| Zoom | 0–15, whole world (±85.05°) |
| Size | 138,605,245,404 bytes; 138.3 GB of it tile data |
| Tiles | 1,431,655,765 addressed, 136,227,651 unique |
| `version` | `4.15.2` |
| OSM data as of | `planetiler:osm:osmosisreplicationtime` = 2026-10-05T04:00Z |
| `attribution` | `© OpenStreetMap`, linked to `openstreetmap.org/copyright` |

- **Builds.** Protomaps publishes daily and keeps "all builds for the past week" plus "the latest build for each patch version". Their downloads page says: "hotlinking to these downloads are discouraged. Instead, you should copy the tileset to your own Cloud Storage." This concept does exactly that.
- **Vector tiles are drawn by the client**, so z15 is not the zoom limit. MapLibre scales z15 tiles up and stays sharp past it.
- **The tile schema has its own version**, and the style package has another one:
  - The tiles are `4.15.2`. The style package `@protomaps/basemaps` is at `5.7.2`. Its major version is not the schema's.
  - The spike fixes the pair that works.
  - The update job refuses a tileset whose `version` major differs from the configured one (`schemaMajor: 4`). A schema 5 build would otherwise go live under a style written for schema 4.
- **Licence.** OSM data under the ODbL. The tiles are a produced work, so attribution is the obligation: `© OpenStreetMap` from the metadata, plus Protomaps. The file itself stays ODbL. We do not put it under other terms, and need not.
- **Escape hatch.** Protomaps builds the basemap with Planetiler. If the builds ever stop, the same schema can be built from a planet PBF ourselves. Planetiler's README: 3 h 35 min on 8 cores / 16 GB. Out of scope here (§12).

## 3. Storage: Hetzner Object Storage

- **Endpoint** `https://nbg1.your-objectstorage.com`, virtual-hosted style. One private bucket, **`lna-dev`** (created by the owner on 2026-10-06).
- **Key layout:** the companion owns one folder, `home-page-companion/`, and each of its modules a subfolder of it. The basemap's objects are `home-page-companion/maps/basemap/<YYYYMMDD>.pmtiles`.
- The bucket is shared, so nothing outside the module's own prefix is ever written or deleted.
- The companion's config gets a `storage` block (bucket URL + the folder name) that every module derives its prefix from (`storage.Prefix("maps/basemap")`).
- **Budget**, against the base package:

  | | Included | Needed |
  |---|---|---|
  | Storage | 1 TB = 744 TB-hours in a 31-day month | 0.139 TB × 744 h ≈ 103 TB-h steady. The old version is kept 7 days after a switch: + ≈ 23 TB-h. **≈ 126 TB-h** |
  | Ingress (the copy) | free | 139 GB / month |
  | Companion → S3 reads | free inside `eu-central` | one ranged GET per tile miss |
  | Egress | 1 TB | none: visitors get tiles from the web server, not from the bucket |
  | Requests | free | — |

- **Price.** €6.49/month since April 2026, according to a third-party report of September 2026. Hetzner's own page did not render its prices for automated reading, so **check it on hetzner.com before ordering**. It is billed hourly for as long as a bucket exists, even an empty one.
- **Limits that shape the job:**
  - Single PUT at most 5 GB, so multipart is mandatory.
  - At most 10,000 parts, so parts must be at least 13.9 MB. We use **64 MiB → 2,066 parts**.
  - 750 requests/s and 10 Gbit/s per bucket.
- **Unfinished multipart uploads take up space.** The job aborts its own stale ones (§5 step 7).
- **Credentials** go into the SOPS `.env` of `Web-Services/homepage` as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`. These are the names go-pmtiles' S3 driver reads.

## 4. Companion: serving tiles

**go-pmtiles as a library** (`github.com/protomaps/go-pmtiles/pmtiles`, v1.31.2):
- `NewServer(bucketURL, prefix, logger, cacheSize, publicURL)`, `Start()`, `Get(ctx, path) (status, headers, body)`.
- Bucket URL in production: `s3://lna-dev?endpoint=https://nbg1.your-objectstorage.com&region=nbg1`.
- In development: `file:///…` with a small local extract (§11 step 0), so a laptop needs no S3 keys.

**Routes:**

| Route | Answer | `Cache-Control` |
|---|---|---|
| `GET /api/tiles/basemap.json` | TileJSON of the **active** version, from `Get("/<version>.json")` | `public, max-age=3600` |
| `GET /api/tiles/basemap/:version/:z/:x/:y.mvt` | the tile, gzip as stored | `public, max-age=31536000, immutable` |

- **`:version` must be the active or a retained version**, anything else is 404. Nobody can enumerate the bucket through the companion.
- **The tile coordinates are bounds-checked:** `z ≤ 15`, and `x` and `y` below `2^z`.
- **Version in the URL** is what makes `immutable` safe. A switch changes the TileJSON, which is cached for an hour, and with it every tile URL. A browser that loaded the old TileJSON keeps getting tiles for the 7 days the old version is retained.
- **`Get`, not `ServeHTTP`**, because the companion sets its own cache headers and does the version check first.
- **A tile miss costs one ranged GET inside `nbg1`.** The file's directories are cached in memory by go-pmtiles.
- **CORS** is already handled by the existing middleware for `/api/*` (`main.go:79–91`).

**Alternative considered: `pmtiles serve` as its own container.** It is zero code. It was rejected because the version switch, the allowlist and the cache headers would then need a home outside it. The companion already has the database, the cron and the admin UI that the update job needs anyway.

## 5. Companion: the update job

1. **Trigger.**
   - Cron `0 0 3 1 * *` (robfig/cron v1, seconds first, as in `main.go:67`): 03:00 on the 1st of the month.
   - `POST /api/admin/basemap/update` behind the API key, for a manual run.
   - One run at a time.
2. **Pick a build.** HEAD `https://build.protomaps.com/<YYYYMMDD>.pmtiles`, from yesterday back six days. The newest `200` wins. If it is the active version, the run is done.
3. **Check before copying.** This step uses three small range requests, before a single byte goes into S3:
   - the 127-byte header: magic `PMTiles`, spec 3, tile type MVT, max zoom 15;
   - the metadata's `version` major must equal `schemaMajor`;
   - any mismatch ends the run with an error in the admin UI.
4. **Copy, resumably.**
   - `CreateMultipartUpload` for `home-page-companion/maps/basemap/<date>.pmtiles`.
   - For part *n*: `GET` with `Range: bytes=n·64MiB–…` and `If-Match: <source ETag>`, then `UploadPart`.
   - Each finished part's ETag is written to the database, so a crash or a container restart resumes at the next missing part.
   - 4 parts in flight, so ~256 MiB of memory. Retries per part with backoff.
   - If the source build vanishes mid-copy (it is only kept a week), the run aborts and the next one picks a newer build.
5. **Verify.**
   - `CompleteMultipartUpload`, then HEAD: the size must equal the source's `Content-Length`.
   - Open the object with go-pmtiles. Its header must be byte-identical to the source header, and the root directory and metadata must read cleanly.
   - Fetch fixed sample tiles at z0, z8 and z15 (around Munich) and check each is a non-empty gzip stream.
   - Protomaps documents BLAKE3 hashes for daily builds, but where they are published was not found. If a hash file turns up, checking it belongs here.
6. **Activate.** One database transaction: new version `active`, the previous one `retained` with `deleteAfter = now + 7 days`.
7. **Clean up** (daily cron):
   - delete retained versions whose date has passed;
   - abort multipart uploads older than two days that no running job owns.
   
   Both act **only under the module's prefix**, `home-page-companion/maps/basemap/`, since the bucket is shared (§3).
8. **Show it.** A new admin page `web/src/routes/basemap/` shows:
   - the active version and its OSM date (`osmosisreplicationtime`);
   - the last run, the progress in parts done / 2,066, and the last error.
   
   Everything also goes to the app log.

**Duration:** unknown until the first run. 138.6 GB at a sustained 1 Gbit/s would be ~19 minutes, but the real throughput between Cloudflare (Protomaps' host) and Hetzner has to be measured. Every request carries an identifying User-Agent.

**Data model:**
```go
type BasemapVersion struct {
	ID            uint
	Version       string     // "20261005", unique
	Key           string     // "home-page-companion/maps/basemap/20261005.pmtiles"
	Size          int64
	SourceETag    string
	SchemaVersion string     // "4.15.2"
	OSMTime       string     // planetiler:osm:osmosisreplicationtime
	Status        string     // copying | verifying | active | retained | deleted | failed
	UploadID      string
	DeleteAfter   *time.Time
	Error         string
	CreatedAt, ActivatedAt time.Time
}

type BasemapPart struct {
	VersionID uint
	Number    int    // 1-based, as S3 counts
	ETag      string
}
```

**Config** (`config.yaml`, which already understands `${VAR}`). It is read once at startup: a changed bucket, prefix or schedule needs a restart of the companion.
```yaml
storage:
  bucketUrl: "s3://lna-dev?endpoint=https://nbg1.your-objectstorage.com&region=nbg1"
  prefix: "home-page-companion"
basemap:
  enabled: true
  source: "https://build.protomaps.com"
  schemaMajor: 4
  schedule: "0 0 3 1 * *"
  retainDays: 7
  publicUrl: "https://companion.lna-dev.net/api/tiles/basemap"
```

**Risk to check in the spike:** go-pmtiles reaches S3 through gocloud and the AWS SDK v2. Recent versions of that SDK send checksums by default, and some S3-compatible services have rejected them. A test bucket answers this in five minutes. If Hetzner rejects them, the fix is setting the SDK's checksum calculation to "when required".

## 6. Companion: routing

**Today.** `travel.js` asks OSRM (car) and Transitous (train, falling back to OSRM) from the browser, for every leg, on every view. It already uses a stored geometry when the API delivers one: `transportIn.geometry`, an array of `[lat, lng]` (`travel.js:329`). The companion simply never sends one; `TripStop` has no such field.

**A separate table, not a field on `TripStop`.** `UpdateTrip` deletes and re-creates every stop of a trip on each save (`trips_handlers.go:246`). A field on the stop would be lost, and recomputed, on every edit.

```go
type RouteGeometry struct {
	Key       string // sha256 of mode + the ordered points A → via-points → B, rounded to 1e-6
	Mode      string // car | train
	Source    string // osrm | transitous | none
	Points    [][2]float64 `gorm:"serializer:json"` // [lat, lng]
	FetchedAt time.Time
	Error     string
}
```

- **On save:** after the transaction, every leg whose key is missing goes into a queue. A worker computes them with the logic `travel.js` has today, moved to Go:
  - car → OSRM `driving`;
  - train → Transitous `plan` per segment with `RAIL`, else OSRM;
  - flight → nothing, the straight line stays.
  
  It sends one request per second and an identifying User-Agent. Transitous requires name, version and a contact.
- **Public API:** `publicTransport` gains `Geometry [][2]float64 json:"geometry,omitempty"`, looked up by key. A leg whose route is not computed yet simply has none, and the browser draws the straight line, as it does today when routing fails.
- **Backfill:** one admin action computes the routes of every published trip. The admin editor gets a "recompute route" per leg, which deletes the key.
- **`travel.js` loses** `OSRM`, `TRANSITOUS`, `fetchOSRM`, `fetchTrainLeg`, `fetchTrain`, `fetchRoute`, `decodePolyline` and `railQueryTime`.
- **Attribution:** the map credits OpenStreetMap and Protomaps, and the routes to OSRM and Transitous with the `transitous.org/sources/` link their policy requires.
- **Before going live**, send Transitous the short note their policy asks for. One request per saved leg is light, but the policy wants contact regardless.

## 7. Frontend

**Vendored** under `static/packages/`, like Leaflet. Sizes measured from the npm releases:

| Package | Version | Minified | gzip |
|---|---|---|---|
| `maplibre-gl` (.js + .css) | 6.12.0 | 1.06 MB + 83 KB | 275 KB + 10 KB |
| `@maplibre/maplibre-gl-leaflet` | 0.1.4 (2026-08-16) | 9 KB | 2.7 KB |
| `@protomaps/basemaps` | 5.7.2 | 39 KB | 7 KB |
| `protomaps-assets`: fonts (Noto Sans Regular / Medium / Italic, Devanagari; 256 ranges each) + sprites v4 | — | 11.5 MB + 0.15 MB | only the ranges a view needs are loaded |

For scale: Leaflet is 39 KB gzipped. MapLibre is loaded only where a map is: `head.html` already loads Leaflet per page (`head.html:329`, `:366`). In the dex it loads only after the click, so the dex's default view stays exactly as light as now.

**Why MapLibre and not `protomaps-leaflet`:** Protomaps' own documentation says `protomaps-leaflet` "is in maintenance mode" and points new projects to MapLibre. `maplibre-gl-leaflet` lets MapLibre draw the base layer inside an ordinary Leaflet map. That keeps everything Leaflet does here today: the panes, the ±360° copies, the dex mask, markers, the legend.

**`assets/js/basemap.js`, new and shared:**
- `basemapLayer({ flavor, lang, pane })` returns `L.maplibreGL({ style })`, with this style:
  - `sources.protomaps` = `{ type: "vector", url: <TileJSON URL> }`;
  - `layers` from `basemaps.layers("protomaps", basemaps.namedFlavor(flavor), { lang })`;
  - `glyphs` and `sprite` pointing at `/packages/protomaps-assets/`, made absolute with `location.origin`.
- A theme switch calls `getMaplibreMap().setStyle(…)` with the other flavor.
- `waterColor(flavor)` returns `namedFlavor(flavor).water`.
- The TileJSON URL comes through `@params` from `head.html`: `CompanionUrl + "/api/tiles/basemap.json"` in production, `localhost:8080` in development. Same pattern as `tripsBaseUrl` (`head.html:331`).

**`travel.js`:**
- The CARTO `tileLayer`, `tileUrl()` and the tile swap in `refreshTheme` become `basemapLayer` + `setStyle`.
- Routing goes (§6).

**`dex-map.js`:**
- "Detailed map" adds `basemapLayer` instead of OSM tiles. Unlike OSM, it now follows dark mode.
- The GBIF URL points at the companion (§8).
- `OSM_SEA` becomes `waterColor(flavor)`. The ocean mask must match whatever lies beneath it (`dex-map.js:106`).
- `maxZoom` 14 stays.

**`{{< map >}}`** (`layouts/shortcodes/map.html`, used four times in `posts/resa/sverige/2024/index.sv.md`). Today it uses leaflet-routing-machine, which calls OSRM's demo on every view. Decided: precompute each route once.

- **`scripts/map-route.py`** (Python, stdlib only, like every script here; it never runs git):
  - `map-route.py <name> <lat,lng> <lat,lng> …` asks OSRM `driving` once, with `overview=simplified`, an identifying User-Agent and at most one request per second.
  - It writes `assets/data/maps/routes/<name>.geojson`: one LineString, `[lng, lat]`, rounded to 5 decimals (~1 m). That keeps a route to a few KB.
- **Under `assets/`, not in the page bundle.**
  - A bundle resource would be published as a file of its own: a new URL for the golden list, and a GeoJSON nobody asked for.
  - From `assets/`, the shortcode reads it with `resources.Get` and inlines `.Content`. Nothing is published, and the page needs no extra request.
  - The dex's range files live the same way (`assets/data/dex/ranges/`).
- **The shortcode gains an optional `route=`.**
  - With `route=`, the file must exist, or the build stops with an `errorf` naming the page and the route.
  - Without `route=`, it draws straight lines between `coordinates`, which also makes no request.
  - The markers and `fitBounds` still come from `coordinates`. The base layer is `basemapLayer`.
- **Attribution** on these maps: `© OpenStreetMap · Protomaps · route: OSRM`.
- The four existing maps are converted once, in this step. After that, `static/packages/leaflet-routing-machine/` goes.

**i18n:** `dex_map_detailed_note` names OpenStreetMap and GBIF as the hosts the map loads from. It is reworded in all three languages; the data is still theirs, delivered through lna-dev.net. The button itself stays (settled decisions).

## 8. GBIF through the companion

- **`GET /api/tiles/gbif/:taxonKey/:z/:x/:y.png`.** `taxonKey` digits only, `z ≤ 14`, `x`/`y` in range. The upstream URL is built server-side with the fixed parameter set from `dex-map.js:353`; no query string from the client passes through.
- **Caching on the companion (decided).** GBIF answers with `Cache-Control: public, max-age=1200` and a dated weak ETag (`W/"2026-10-03T05:00Z--gzip"`, checked 2026-10-06), so a shared cache is intended.
  - The cache lives on disk under `data/cache/gbif/<taxonKey>/<z>/<x>/<y>.png`, with the ETag and fetch time beside each file. `data/` is the companion's volume (`/home/lnadev/storage/homepage/companion` in `Web-Services/homepage/docker-compose.yaml`), so the cache survives a new image.
  - Fresher than `max-age`: served from disk, GBIF is not asked.
  - Older: revalidated with `If-None-Match`. A `304` only refreshes the fetch time.
  - **GBIF unreachable or erroring: the stale file is served.** A dex map should not lose its overlay because GBIF is down for an hour.
  - Capped at 1 GB. A daily cron removes the files that were used least recently.
  - Concurrent requests for the same tile share one upstream fetch.
- **Licence.** The density tiles aggregate datasets under CC0, CC BY 4.0 and CC BY-NC 4.0. What follows is attribution, which stays (the link to the GBIF species page), and non-commercial use, which this site is. GBIF's terms pages refused automated reading (403), so their exact wording was not checked.

## 9. Tor

The companion's CORS admits `*.lna-dev.net` and `localhost` and nothing else (`main.go:76–82`). By that code, a page on the onion cannot read the companion's answers today: trips and likes fail there, and the tiles would too.

**Decided: the onion origin goes into the CORS list.**
- **Config, not code.** A new `security.extraOrigins` in `config.yaml`, a list of **exact** origins, never patterns: `http://lnadevwj2vzomixiunv7i4lahwpoxh6zw56cxbce3uui5ijmwt4czpyd.onion`, the address in `deploy.sh:24`. `AllowOriginFunc` then admits the subdomain regex, `localhost`, or an exact entry of that list.
- **Nothing changes on the site.** The onion build already points at the clearnet companion: `head.html` uses `CompanionUrl` for every production build.
- **What it means.** Tor Browser fetches `companion.lna-dev.net` through an exit node. The request leaves the onion network but reaches no third party, and the visitor's address stays hidden as on any Tor connection. In return, maps, trips, likes and the GBIF overlay work on the onion, after a click for the dex, as on the clearnet.
- **Likes from Tor.** Native likes are de-duplicated by hashed IP (companion README), and over Tor that IP is the exit node's. Two Tor visitors on one exit count as one like, and one visitor on a new circuit can like twice. That is acceptable for a like counter and is noted here so nobody calls it a bug later.
- **WebGL in Tor Browser** depends on the security level and is checked in the spike. Where MapLibre cannot start, `basemap.js` leaves the map as it was:
  - the dex keeps its local view;
  - travel keeps its lines and pins on an empty background.
  
  At "Safest" there is no JavaScript at all, and so no map either way.
- **The dex's local first paint stays the default** (the button stays, settled decisions). That remains what an onion visitor sees without asking for more.

## 10. Tests

**Home-Page** (all against `.test-site/`, as always):
- **Static, new: the guard.**
  - No built file contains `tile.openstreetmap.org`, `basemaps.cartocdn.com`, `router.project-osrm.org`, `api.transitous.org` or `api.gbif.org`.
  - Attribution links (`openstreetmap.org/copyright`, `transitous.org/sources/`, `gbif.org/species/…`) are not request hosts and stay allowed.
- **`dex-map.spec.ts`:**
  - "Detailed map" requests only same-origin files and `companion.lna-dev.net/api/tiles/…` (mocked).
  - The mask takes the flavor's water colour.
  - A theme switch changes the style.
- **`tests/support/network.ts`:**
  - `mockDetailedMap` becomes a tile mock: a TileJSON fixture, and an empty 200 for `.mvt`. Whether MapLibre accepts an empty body is a spike item; if not, a tiny fixture tile.
  - The GBIF mock moves to the companion path.
  - `ALLOW_MAP_TILES` goes.
- **Travel, new** (there is no travel e2e test today): a mocked trip with `geometry` draws that line and makes no routing request.
- **`{{< map >}}`:**
  - The Swedish post's four maps draw their committed routes and request nothing beyond same-origin files and the tile mock.
  - A `route=` naming a missing file stops the build. This is checked on a fixture page, not on the real post.
- **WebGL:** whether headless Firefox, Chromium and mobile-chrome give MapLibre a WebGL context is a spike item. Without one, MapLibre fails to start. `basemap.js` must catch that and leave the map as it was, and the test asserts that instead.
- `docs/concepts/testing.md`: the *Dex map* row is updated.

**Companion** (Go, `httptest`):
- CORS:
  - the onion origin from `extraOrigins` is admitted;
  - `http://other.onion` and `https://lna-dev.net.example.com` are not.
- Tile route: version allowlist, coordinate bounds, headers.
- Update job against a fake source and a fake S3 (the four multipart calls):
  - resume after a failed part;
  - refusal of a different schema major;
  - a size mismatch is not activated;
  - retention cleanup.
- Routing: the same points give the same key, rounding included; the train → OSRM fallback.
- GBIF:
  - the parameter allowlist;
  - a fresh hit makes no upstream request;
  - a stale hit revalidates;
  - an upstream error serves the stale file;
  - the size cap evicts.

## 11. Build order

0. **Spike, local, nothing deployed.**
   - `pmtiles extract` a small region straight from the remote build (bbox + max zoom, through range requests) and serve it with `pmtiles serve`.
   - Prototype `basemap.js` in `dex-map.js` and `travel.js`.
   - Check:
     - the ±360° copies, the panes and the dex mask over a MapLibre layer;
     - `setStyle` on theme switch, and labels in `lang`;
     - the style ↔ schema pair (5.7.2 ↔ 4.15.2);
     - WebGL in the three Playwright browsers;
     - Hetzner + SDK checksums against the bucket `lna-dev`, under a `spike/` prefix that is removed afterwards. The owner's test keys are passed as environment variables of that one shell and are never written to a file;
     - WebGL in Tor Browser at the "Standard" and "Safer" levels.
   - **Go / no-go for `maplibre-gl-leaflet`.** The fallback is `protomaps-leaflet`, in maintenance mode.
1. **Routing in the companion (§6)** and the routing removal in `travel.js`, plus **`extraOrigins` for the onion (§9)**. This step can be deployed alone. It already ends the on-load calls to the demo servers and makes trips and likes work on the onion.
2. **Bucket and secrets**: Hetzner `nbg1`, SOPS `.env` and `config.yaml` in `Web-Services`. The owner's manual step.
3. **Companion tiles (§4, §5):** serving, update job, admin page, first copy.
4. **Frontend basemap (§7):** vendored packages and assets, `basemap.js`, `travel.js`, `dex-map.js`, `head.html` params, i18n.
5. **GBIF proxy (§8)** and the dex switch to it.
6. **`{{< map >}}` (§7):** `scripts/map-route.py`, the four routes of the Swedish post under `assets/data/maps/routes/`, the shortcode's `route=`, and the removal of leaflet-routing-machine.
7. **Tests (§10) and docs:** `CLAUDE.md` (*Photo dex* map paragraph, *Structured data* is untouched), `testing.md`.

Each companion step ships as a new image tag in `Web-Services/homepage/docker-compose.yaml`, each site step through `deploy.sh`. Both are the owner's to trigger.

## 12. Out of scope

- **Rendering from raw OSM** (PostGIS + Mapnik, or our own Planetiler run). It was discussed and is not needed while Protomaps publishes builds. Planetiler is the escape hatch (§2).
- **Regional extracts or a lower max zoom.** The decision was the whole planet at z15.
- **An onion address for the companion itself.** The onion reaches the clearnet companion through an exit node (§9). A hidden service for the companion would keep those requests inside Tor, but it is a deployment of its own.
- **Geocoding and search.**
- **The map in `gallery-project-stories.md` §8.** That concept's "catch" was that the local first paint is blank at valley scale. A same-site z15 basemap removes it, but the technique decision stays in that document.

## As built (2026-10-06)

**Spike verdicts.**
- **`maplibre-gl-leaflet` carries every map.** The ±360° copies, the panes and the dex mask work over a MapLibre layer; `npm test` covers them in firefox, chromium and mobile-chrome (271 passed, 6 skipped — the opt-in WebKit projects).
- **Style ↔ schema:** `@protomaps/basemaps` 5.7.2 draws schema 4.15.2.
- **WebGL2** is there in all three headless test browsers. Tor Browser: not checked (*Still open*).
- **Hetzner** accepts multipart uploads once the SDK sends checksums only "when required" (`basemap/store.go`), and the ranged GETs go-pmtiles makes through gocloud need no change.

**Live test against the real bucket**, with a 103 MB stand-in build (world z0–6 plus Munich and Malmö z7–15, cut from build `20261005`) served by a local fake of the build host:
- The copy was killed after 4 of 13 parts and resumed at part 5 on restart. Exactly the 9 missing parts and the header were fetched again.
- Tiles read back from S3 through the companion were byte-identical to the local file.
- A second build switched over; the first was retained and still served.
- The S3 store's own integration test (`BASEMAP_S3_TEST_URL`) passed.
- Everything was written under `spike/` and has been deleted; the bucket is empty.

**The full 139 GB copy runs on the server, not on a home connection.** This machine uploads at ~5.2 MB/s whatever the parallelism (measured), which would be ~7.5 hours of a saturated uplink. On the server the copy is internal Hetzner traffic.

**Deviations from the plan above.**
- **Key layout** (owner's request during the build): a `storage` block in the companion's config (`bucketUrl`, `prefix: home-page-companion`), and every module under `<prefix>/<module>/`. The basemap is `home-page-companion/maps/basemap/<YYYYMMDD>.pmtiles`, and `basemap.enabled` switches it on (§3, §5).
- **Config is read once at startup.** Unlike the rest of the config, which `main.go` reloads every five minutes, a changed bucket, prefix or schedule needs a restart.
- **`go-pmtiles` as a library does not register gocloud's S3 driver**; its CLI does. `basemap.go` imports `gocloud.dev/blob/s3blob` itself, and a test holds that.
- **The AWS SDK stays at the versions go-pmtiles pins.** The newest SDK releases require Go 1.26, and the companion's Dockerfile builds with `golang:1.25`.
- **Routes in the companion** are thinned to ~5 m (Douglas–Peucker) and rounded to 5 decimals. A Munich→Augsburg leg came back with 196 points, the whole test trip at 8.7 KB.
- **`{{< map >}}` routes** use OSRM's full geometry thinned to ~50 m, not `overview=simplified`. That overview is cut for the zoom that fits the whole route (47 points for 1,365 km) and turns angular as soon as you zoom in. `scripts/map-route.py` records source, tolerance and waypoints in each file's properties; only the coordinates reach the page.
- **MapLibre 6 ships ES modules only**, while the Leaflet plugin and the style builder are classic scripts. `basemap.js` imports the module, publishes it as `window.maplibregl`, then loads the two scripts — the order matters.
- **The trip editor** in the companion's admin shows each leg's route status (computed / failed / pending) with a *Recompute* button. A new *Basemap* page shows the copy's progress, the stored builds and the route counts.

**Found on the way, not fixed** (outside this concept):
- The companion **cannot start on an empty database**: migration `001_itemname_to_guid` expects tables that do not exist yet, and `log.Fatal`s. The live test seeded the migration row by hand.
- `go vet` fails on `webpush/notify.go:27,29` (`%s` for a `uint`), so `go test ./...` reports that package as a build failure. It was like that before this work.
- **The companion's own admin UI** (`LocationPicker.svelte`, `RoutePicker.svelte`) still loads OSM tiles and Nominatim from the owner's browser. It is not public, so it was left alone.

**To go live** (the owner's steps):
1. In the SOPS `.env` of `Web-Services/homepage`: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — production keys, not the test keys used here.
2. In `Web-Services/homepage/companion/config.yaml`:
   - `security.extraOrigins` with the onion address;
   - `storage` (`bucketUrl`, `prefix: home-page-companion`);
   - `basemap` (`enabled: true`, `schedule`, `publicUrl: https://companion.lna-dev.net/api/tiles/basemap`).
3. New companion and companion-web images, then the tags in `docker-compose.yaml`.
4. Trigger the first copy from the *Basemap* admin page, or wait for the schedule. Until a build is active, the maps simply show no basemap: the TileJSON answers 503 and `basemap.js` resolves to null. **So the companion can go out before the site does, not the other way round.**
5. Then the site's `deploy.sh`.
6. Send Transitous the note its policy asks for (§6).

