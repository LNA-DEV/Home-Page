/* The species map. Its default view is entirely local — Natural Earth land and
 * borders drawn as GeoJSON plus the iNaturalist range — and that is what makes
 * a species page usable on the Tor onion build.
 *
 * The network policy is therefore the assertion: on load, nothing may leave
 * localhost. "Detailed map" is the explicit opt-in, and even it may reach only
 * the companion, which serves the site's own basemap and proxies GBIF
 * (docs/concepts/self-hosted-maps.md). */

import { test, expect } from "../support/fixtures";
import { ALLOW_COMPANION, mockMapTiles, mockCompanion } from "../support/network";
import { withoutWebGL2 } from "../support/webgl";

/* The companion is allowed through to a mock; the test asserts which of its
   endpoints were actually used. */
test.use({ net: { allow: ALLOW_COMPANION } });

/* A species with a committed range file, so the map has something to draw. */
const SPECIES = "/en/gallery/dex/red-fox/";

/* The analytics script in extend_head.html is site-wide and on every page of
   every build. It is named here rather than filtered silently, so the exception
   stays visible: the claim the map rests on is that NO MAP DATA comes from a
   third party. */
const ANALYTICS = /muninn\.lna-dev\.net/;

/** How many pixels of the ocean mask's canvas are this colour, give or take a
 *  rounding step. The mask is painted opaque at the zooms these tests use. */
async function maskPixels(page: import("@playwright/test").Page, hex: string) {
  return page.evaluate((color) => {
    const canvas = document.querySelector(".leaflet-dex-ocean-pane canvas") as HTMLCanvasElement | null;
    if (!canvas) return -1;
    const ctx = canvas.getContext("2d");
    if (!ctx || !canvas.width || !canvas.height) return -1;
    const want = [1, 3, 5].map((i) => parseInt(color.slice(i, i + 2), 16));
    const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);
    let n = 0;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i + 3] > 250 && Math.abs(data[i] - want[0]) <= 2 && Math.abs(data[i + 1] - want[1]) <= 2 && Math.abs(data[i + 2] - want[2]) <= 2) n++;
    }
    return n;
  }, hex);
}

test("a species page makes no third-party request on load, and loads no MapLibre", async ({ page, probe }) => {
  await mockCompanion(page);
  const tiles = await mockMapTiles(page);
  const local: string[] = [];
  page.on("request", (r) => local.push(r.url()));

  await page.goto(SPECIES);
  await expect(page.locator("[data-dex-map-canvas]")).toBeVisible();
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await page.waitForTimeout(1200);

  const offsite = probe.network.external.filter(
    (u) => !/companion\.lna-dev\.net/.test(u) && !ANALYTICS.test(u),
  );
  expect(offsite, `the default map must draw locally — it is what makes this page work over Tor\n${offsite.join("\n")}`).toEqual([]);
  expect(tiles.hit, "the default view asked the companion for map tiles").toEqual([]);
  expect(
    local.filter((u) => /\/packages\/(maplibre-gl|protomaps)/.test(u)),
    "MapLibre is ~300 KB and loads only after the click",
  ).toEqual([]);
});

test("the land, the range and the sea are all drawn", async ({ page, probe }) => {
  void probe;
  await mockCompanion(page);
  await page.goto(SPECIES);
  await expect(page.locator(".leaflet-container")).toBeVisible();

  /* Stacking is pinned by panes, not by load order: land 410 → range 420 →
     ocean 430 → lines 440. These are independent fetches that finish in any
     order, and a shared renderer paints as they arrive. */
  for (const pane of ["dex-land", "dex-range", "dex-ocean", "dex-lines"]) {
    /* Leaflet names a custom pane's element `leaflet-<name>-pane`. */
    await expect(page.locator(`.leaflet-pane.leaflet-${pane}-pane`), `pane ${pane}`).toBeAttached();
  }

  /* Each pane is painted by its own canvas renderer, not by SVG paths, so
     "did it draw anything" is a pixel question. */
  for (const pane of ["dex-land", "dex-range"]) {
    const painted = await page.evaluate((name) => {
      const canvas = document.querySelector(`.leaflet-${name}-pane canvas`) as HTMLCanvasElement | null;
      if (!canvas) return null;
      const ctx = canvas.getContext("2d");
      if (!ctx || !canvas.width || !canvas.height) return 0;
      const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);
      let opaque = 0;
      for (let i = 3; i < data.length; i += 4) if (data[i] > 0) opaque++;
      return opaque;
    }, pane);
    expect(painted, `${pane} has no canvas`).not.toBeNull();
    expect(painted, `${pane} drew nothing`).toBeGreaterThan(0);
  }
});

test("\"detailed map\" is the opt-in, and reaches only the companion @mobile", async ({ page, probe }) => {
  await mockCompanion(page);
  const tiles = await mockMapTiles(page);

  await page.goto(SPECIES);
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await page.waitForTimeout(600);

  await page.locator("[data-dex-map-detail]").click();
  /* The basemap is MapLibre inside Leaflet; its container appears once the
     scripts loaded and WebGL2 gave it a context. */
  const gl = page.locator(".leaflet-dex-basemap-pane .leaflet-gl-layer");
  await expect(gl).toBeAttached();
  await expect(gl).toHaveAttribute("data-flavor", "light");
  await page.waitForTimeout(1200);

  expect(tiles.hit.some((u) => u.endsWith("/api/tiles/basemap.json")), "no TileJSON requested").toBe(true);
  expect(tiles.hit.some((u) => /\/api\/tiles\/basemap\/\d{8}\/\d+\/\d+\/\d+\.mvt$/.test(u)), "no basemap tiles requested").toBe(true);
  expect(tiles.hit.some((u) => /\/api\/tiles\/gbif\/\d+\/\d+\/\d+\/\d+\.png$/.test(u)), "no GBIF overlay requested").toBe(true);

  const unexpected = probe.network.external.filter((u) => !/companion\.lna-dev\.net/.test(u) && !ANALYTICS.test(u));
  expect(unexpected, `detailed mode reached a third party\n${unexpected.join("\n")}`).toEqual([]);

  await expect(page.locator(".basemap-notice"), "a note although WebGL2 is there").toHaveCount(0);

  /* The drawn world is swapped out; the range and its ocean mask stay. */
  await expect(page.locator(".leaflet-pane.leaflet-dex-range-pane")).toBeAttached();
  /* The mask repaints the sea in the basemap's own water colour, so the range
     still means "on land" over the basemap. */
  const light = await page.evaluate(() => (window as any).basemaps.namedFlavor("light").water as string);
  expect(await maskPixels(page, light), `mask not in the light flavor's water ${light}`).toBeGreaterThan(1000);
});

test("the detailed map follows the site theme, mask included, and switches back", async ({ page, probe }) => {
  void probe;
  await mockCompanion(page);
  await mockMapTiles(page);

  await page.goto(SPECIES);
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await page.locator("[data-dex-map-detail]").click();
  const gl = page.locator(".leaflet-gl-layer");
  await expect(gl).toHaveAttribute("data-flavor", "light");

  /* PaperMod's toggle sets data-theme on <html>; that is all the map watches. */
  await page.evaluate(() => { document.documentElement.dataset.theme = "dark"; });
  await expect(gl).toHaveAttribute("data-flavor", "dark");
  const dark = await page.evaluate(() => (window as any).basemaps.namedFlavor("dark").water as string);
  await expect.poll(() => maskPixels(page, dark), { message: `mask not in the dark flavor's water ${dark}` }).toBeGreaterThan(1000);

  /* A second click restores the drawn world and drops the basemap. */
  await page.locator("[data-dex-map-detail]").click();
  await expect(page.locator(".leaflet-gl-layer")).toHaveCount(0);
  await expect(page.locator("[data-dex-map-detail]")).not.toHaveClass(/is-active/);
});

test("without WebGL2, \"detailed map\" says why inside the map and keeps the drawn world", async ({ page, probe }) => {
  void probe;
  await withoutWebGL2(page);
  await mockCompanion(page);
  const tiles = await mockMapTiles(page);
  const local: string[] = [];
  page.on("request", (r) => local.push(r.url()));

  await page.goto(SPECIES);
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await page.locator("[data-dex-map-detail]").click();

  const note = page.locator("[data-dex-map] .basemap-notice");
  await expect(note).toBeVisible();
  await expect(note).toContainText("WebGL");
  await expect(page.locator(".leaflet-gl-layer")).toHaveCount(0);
  /* The drawn world stays under the GBIF overlay, which needs no WebGL. */
  await expect(page.locator(".leaflet-dex-land-pane canvas")).toBeAttached();
  await expect.poll(() => tiles.hit.some((u) => /\/api\/tiles\/gbif\//.test(u)), { message: "no GBIF overlay" }).toBe(true);
  expect(tiles.hit.filter((u) => u.endsWith("/api/tiles/basemap.json")), "TileJSON fetched although nothing can draw it").toEqual([]);
  expect(local.filter((u) => /\/packages\/maplibre-gl/.test(u)), "MapLibre loaded although it cannot run").toEqual([]);

  /* Switching back takes the note away again. */
  await page.locator("[data-dex-map-detail]").click();
  await expect(note).toHaveCount(0);
});
