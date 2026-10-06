/* The {{< map >}} shortcode. Its routes are fetched once by
 * scripts/map-route.py and inlined into the page, and the basemap is the
 * site's own — so a post with maps talks to the companion for tiles and to
 * nobody else. It used to ask OSRM's demo server for every route on every view
 * (docs/concepts/self-hosted-maps.md §7). */

import { test, expect } from "../support/fixtures";
import { ALLOW_COMPANION, mockCompanion, mockMapTiles } from "../support/network";
import { withoutWebGL2 } from "../support/webgl";

test.use({ net: { allow: ALLOW_COMPANION } });

const POST = "/sv/posts/resa/sverige/2024/";
const ANALYTICS = /muninn\.lna-dev\.net/;

test("every map draws its committed route over the site's basemap @mobile", async ({ page, probe }) => {
  await mockCompanion(page);
  const tiles = await mockMapTiles(page);

  await page.goto(POST);
  const maps = page.locator("[data-route-map]");
  await expect(maps).toHaveCount(6);
  await expect(page.locator("[data-route-map].leaflet-container")).toHaveCount(6);

  /* Two paths per map — the white casing and the line — and the line follows
     the road: a route has hundreds of points, a straight line two or three. */
  for (let i = 0; i < 6; i++) {
    const paths = maps.nth(i).locator("path.leaflet-interactive");
    await expect(paths).toHaveCount(2);
    const points = await paths.nth(1).evaluate((p) => (p.getAttribute("d") || "").split("L").length);
    expect(points, `map ${i} is not following its route`).toBeGreaterThan(20);
  }

  await expect(page.locator("[data-route-map] .leaflet-gl-layer")).toHaveCount(6);
  await expect(page.locator("[data-route-map] .basemap-notice")).toHaveCount(0);
  /* One TileJSON request for six maps: basemap.js shares it. */
  expect(tiles.hit.filter((u) => u.endsWith("/api/tiles/basemap.json"))).toHaveLength(1);

  await page.waitForTimeout(800);
  const offsite = probe.network.external.filter((u) => !/companion\.lna-dev\.net/.test(u) && !ANALYTICS.test(u));
  expect(offsite, `a route map reached a third party\n${offsite.join("\n")}`).toEqual([]);
});

test("without WebGL2 every map says why, and still draws its route", async ({ page, probe }) => {
  void probe;
  await withoutWebGL2(page);
  await mockCompanion(page);
  const tiles = await mockMapTiles(page);

  await page.goto(POST);
  const maps = page.locator("[data-route-map]");
  await expect(maps).toHaveCount(6);
  const notes = page.locator("[data-route-map] .basemap-notice");
  await expect(notes).toHaveCount(6);
  await expect(notes.first()).toContainText("WebGL");
  await expect(page.locator("[data-route-map] .leaflet-gl-layer")).toHaveCount(0);
  for (let i = 0; i < 6; i++) {
    await expect(maps.nth(i).locator("path.leaflet-interactive")).toHaveCount(2);
  }
  expect(tiles.hit.filter((u) => u.endsWith("/api/tiles/basemap.json"))).toEqual([]);
});
