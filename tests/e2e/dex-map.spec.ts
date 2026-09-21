/* The species map. Its default view is entirely local — Natural Earth land and
   borders drawn as GeoJSON plus the iNaturalist range — and that is what makes
   a species page usable on the Tor onion build.
 *
 * The network policy is therefore the assertion: on load, nothing may leave
 * localhost. "Detailed map" is the explicit opt-in, and it may reach exactly two
 * hosts. */

import { test, expect } from "../support/fixtures";
import { ALLOW_MAP_TILES, ALLOW_COMPANION, mockDetailedMap, mockCompanion } from "../support/network";

/* Both are allowed through to a mock; the test asserts which were actually used. */
test.use({ net: { allow: [...ALLOW_MAP_TILES, ...ALLOW_COMPANION] } });

/* A species with a committed range file, so the map has something to draw. */
const SPECIES = "/en/gallery/dex/red-fox/";

test("a species page makes no third-party request on load", async ({ page, probe }) => {
  await mockCompanion(page);
  await mockDetailedMap(page);

  await page.goto(SPECIES);
  await expect(page.locator("[data-dex-map-canvas]")).toBeVisible();
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await page.waitForTimeout(1200);

  /* The one third party a species page does contact is the analytics script in
     extend_head.html, which is site-wide and on every page of every build. It is
     named here rather than filtered silently, so the exception stays visible:
     the claim the map rests on is that NO MAP DATA comes from a third party. */
  const ANALYTICS = /muninn\.lna-dev\.net/;
  const offsite = probe.network.external.filter(
    (u) => !/companion\.lna-dev\.net/.test(u) && !ANALYTICS.test(u),
  );
  expect(offsite, `the default map must draw locally — it is what makes this page work over Tor\n${offsite.join("\n")}`).toEqual([]);
  expect(
    probe.network.external.some((u) => /tile\.|gbif|inaturalist/i.test(u)),
    "the default view requested a tile or an occurrence overlay",
  ).toBe(false);
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

test("\"detailed map\" is the opt-in, and reaches exactly two hosts", async ({ page, probe }) => {
  await mockCompanion(page);
  const map = await mockDetailedMap(page);

  await page.goto(SPECIES);
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await page.waitForTimeout(600);

  await page.locator("[data-dex-map-detail]").click();
  await page.waitForTimeout(1500);

  expect(map.hit.some((u) => /tile\.openstreetmap\.org/.test(u)), "no OSM tiles requested").toBe(true);
  expect(map.hit.some((u) => /api\.gbif\.org/.test(u)), "no GBIF overlay requested").toBe(true);

  const unexpected = probe.network.external.filter(
    (u) => !/tile\.openstreetmap\.org|api\.gbif\.org|companion\.lna-dev\.net|muninn\.lna-dev\.net/.test(u),
  );
  expect(unexpected, `detailed mode reached a third host\n${unexpected.join("\n")}`).toEqual([]);

  /* The range polygon stays on top in both modes. */
  await expect(page.locator(".leaflet-pane.leaflet-dex-range-pane")).toBeAttached();
});
