/* The trip map. The browser routes nothing any more: the companion computes
 * each leg's road or rail geometry when a trip is saved and delivers it as
 * `transportIn.geometry`, and the basemap is the site's own
 * (docs/concepts/self-hosted-maps.md). So a trip page may talk to the companion
 * and to nobody else — no OSRM, no Transitous, no CARTO. */

import { test, expect } from "../support/fixtures";
import { ALLOW_COMPANION, COMPANION, mockCompanion, mockMapTiles } from "../support/network";
import { withoutWebGL2 } from "../support/webgl";

test.use({ net: { allow: ALLOW_COMPANION } });

const ANALYTICS = /muninn\.lna-dev\.net/;

/* Three stops, two legs: a train leg with the companion's stored geometry
   (four points, so the drawn line must bend), and an upcoming car leg without
   one, which stays a straight line. */
const TRIP = {
  slug: "test-trip",
  title: "Test trip",
  updatedAt: "2026-10-01T10:00:00Z",
  stats: { cities: 3, countries: 2, distanceKm: 1100 },
  stops: [
    { id: "munich", name: "Munich", lat: 48.137, lng: 11.575, status: "visited", photos: [] },
    {
      id: "malmo", name: "Malmö", lat: 55.605, lng: 13.0, status: "current", photos: [],
      transportIn: {
        mode: "train", label: "ICE", duration: "10h", photos: [],
        geometry: [[48.137, 11.575], [50.11, 8.68], [53.55, 9.99], [55.605, 13.0]],
      },
    },
    {
      id: "kalmar", name: "Kalmar", lat: 56.66, lng: 16.36, status: "upcoming", photos: [],
      transportIn: { mode: "car", label: "car", duration: "3h", photos: [] },
    },
  ],
};

test("a trip draws the companion's geometry and asks no router @mobile", async ({ page, probe }) => {
  await mockCompanion(page);
  const tiles = await mockMapTiles(page);
  await page.route(`${COMPANION}/api/trips/test-trip`, (route) => route.fulfill({ json: TRIP }));

  await page.goto("/en/travel/#test-trip");
  await expect(page.locator(".trip-map.leaflet-container")).toBeVisible();

  /* Leaflet draws polylines as SVG paths: "M x y" then one "L x y" per further
     point. The stored train geometry has four points; the car leg has none and
     stays the two-point straight line. */
  const segments = page.locator(".trip-map path.leaflet-interactive");
  await expect(segments).toHaveCount(2);
  const lCounts = await segments.evaluateAll((paths) => paths.map((p) => (p.getAttribute("d") || "").split("L").length - 1));
  expect(lCounts.sort(), "the train leg should follow its stored geometry").toEqual([1, 3]);

  /* The basemap came from the companion, and the routes are credited with the
     link Transitous's policy asks for. */
  await expect(page.locator(".trip-map .leaflet-gl-layer")).toBeAttached();
  expect(tiles.hit.some((u) => u.endsWith("/api/tiles/basemap.json")), "no TileJSON requested").toBe(true);
  await expect(page.locator('.trip-map .leaflet-control-attribution a[href="https://transitous.org/sources/"]')).toBeAttached();

  await page.waitForTimeout(800);
  const offsite = probe.network.external.filter((u) => !/companion\.lna-dev\.net/.test(u) && !ANALYTICS.test(u));
  expect(offsite, `a trip page reached a third party\n${offsite.join("\n")}`).toEqual([]);
  expect(probe.pageErrors).toEqual([]);
  expect(probe.consoleErrors).toEqual([]);
});

test("the basemap switches flavor with the site theme", async ({ page, probe }) => {
  void probe;
  await mockCompanion(page);
  await mockMapTiles(page);
  await page.route(`${COMPANION}/api/trips/test-trip`, (route) => route.fulfill({ json: TRIP }));

  await page.goto("/en/travel/#test-trip");
  const gl = page.locator(".trip-map .leaflet-gl-layer");
  await expect(gl).toBeAttached();
  const start = await gl.getAttribute("data-flavor");
  const next = start === "dark" ? "light" : "dark";
  await page.evaluate((theme) => { document.documentElement.dataset.theme = theme; }, next);
  await expect(gl).toHaveAttribute("data-flavor", next);
});

test("without WebGL2 the trip map says why, and still draws its legs", async ({ page, probe }) => {
  void probe;
  await withoutWebGL2(page);
  await mockCompanion(page);
  await mockMapTiles(page);
  await page.route(`${COMPANION}/api/trips/test-trip`, (route) => route.fulfill({ json: TRIP }));

  await page.goto("/en/travel/#test-trip");
  await expect(page.locator(".trip-map.leaflet-container")).toBeVisible();
  const note = page.locator(".trip-map .basemap-notice");
  await expect(note).toBeVisible();
  await expect(note).toContainText("The background map needs WebGL");
  await expect(page.locator(".trip-map .leaflet-gl-layer")).toHaveCount(0);
  await expect(page.locator(".trip-map path.leaflet-interactive")).toHaveCount(2);
});
