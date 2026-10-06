/* L2 — no map on this site sends a visitor to a third party.
 *
 * The basemap is the site's own (the Protomaps build of OpenStreetMap, served
 * by the companion), GBIF's density tiles go through the companion, and routes
 * are computed once — by the companion for trips, by scripts/map-route.py for
 * the {{< map >}} shortcode — instead of in the browser
 * (docs/concepts/self-hosted-maps.md). The guard is plain text: if any built
 * file names one of the hosts the maps used to call, a page can call it again.
 * Attribution links (openstreetmap.org/copyright, transitous.org/sources/,
 * gbif.org/species/…) are not request hosts and stay allowed. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { REPO, textFiles, readSiteFile, sitePath } from "../support/site";

const BANNED = [
  "tile.openstreetmap.org",
  "basemaps.cartocdn.com",
  "router.project-osrm.org",
  "api.transitous.org",
  "api.gbif.org",
];

test("no built file names a third-party map host", () => {
  const hits: string[] = [];
  for (const file of textFiles()) {
    const text = readSiteFile(file);
    for (const host of BANNED) if (text.includes(host)) hits.push(`${file}: ${host}`);
  }
  expect(hits.slice(0, 20), `${hits.length} hit(s)\n${hits.slice(0, 20).join("\n")}`).toEqual([]);
});

/* Every route= in a post names a committed route file that is a usable line. */
const ROUTE_DIR = path.join(REPO, "assets", "data", "maps", "routes");

function contentFiles(dir: string, acc: string[] = []): string[] {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) contentFiles(full, acc);
    else if (e.name.endsWith(".md")) acc.push(full);
  }
  return acc;
}

test("every {{< map route=… >}} names a committed route in [lng, lat] order", () => {
  const problems: string[] = [];
  let used = 0;
  for (const file of contentFiles(path.join(REPO, "content"))) {
    const md = fs.readFileSync(file, "utf8");
    for (const m of md.matchAll(/\{\{<\s*map\b[^>]*?\broute="([^"]+)"/g)) {
      used++;
      const name = m[1];
      const target = path.join(ROUTE_DIR, `${name}.geojson`);
      if (!fs.existsSync(target)) {
        problems.push(`${path.relative(REPO, file)}: route "${name}" has no file`);
        continue;
      }
      const feature = JSON.parse(fs.readFileSync(target, "utf8"));
      const coords = feature?.geometry?.coordinates;
      if (feature?.geometry?.type !== "LineString" || !Array.isArray(coords) || coords.length < 2) {
        problems.push(`${name}: not a LineString with two or more points`);
        continue;
      }
      const bad = coords.filter((c: number[]) => !(Math.abs(c[0]) <= 180 && Math.abs(c[1]) <= 90));
      if (bad.length) problems.push(`${name}: ${bad.length} point(s) out of range`);
    }
  }
  expect(used, "no {{< map >}} uses a route — did the Swedish post lose them?").toBeGreaterThan(0);
  expect(problems).toEqual([]);
});

test("a route map carries its route inline, and nothing to fetch", () => {
  const html = fs.readFileSync(sitePath("sv", "posts", "resa", "sverige", "2024", "index.html"), "utf8");
  const routes = [...html.matchAll(/data-route-map[^>]*?data-route="([^"]*)"/g)].map((m) => m[1]);
  expect(routes).toHaveLength(6);
  for (const r of routes) {
    const coords = JSON.parse(r.replace(/&#34;|&quot;/g, '"'));
    expect(Array.isArray(coords) && coords.length > 20, "route inlined as [lng, lat] pairs").toBe(true);
  }
  /* The routing plugin is gone, with its stylesheet. */
  expect(html).not.toContain("leaflet-routing-machine");
});
