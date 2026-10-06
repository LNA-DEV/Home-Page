/* L0 — the {{< map >}} shortcode's one hard rule: a `route` that names no
 * committed file stops the build (docs/concepts/self-hosted-maps.md §7).
 *
 * Checked on a throwaway site in a temp dir, not on the real one: breaking a
 * real post to prove the build breaks would make the main build test red. The
 * fixture carries the real shortcode file and nothing else, so it tests exactly
 * what the site ships. */

import { test, expect } from "@playwright/test";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { REPO } from "../support/site";

const run = promisify(execFile);

function fixture(routeName: string, withFile: boolean): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "map-route-"));
  const write = (rel: string, body: string) => {
    fs.mkdirSync(path.dirname(path.join(dir, rel)), { recursive: true });
    fs.writeFileSync(path.join(dir, rel), body);
  };
  write("hugo.toml", 'baseURL = "http://example.org/"\ndisableKinds = ["taxonomy", "term", "RSS", "sitemap"]\n');
  write("layouts/shortcodes/map.html", fs.readFileSync(path.join(REPO, "layouts/shortcodes/map.html"), "utf8"));
  write("layouts/page.html", "{{ .Content }}");
  write("layouts/home.html", "home");
  write(
    "content/trip.md",
    `---\ntitle: trip\n---\n{{< map coordinates="[{\\"x\\": 55.6, \\"y\\": 13.0}, {\\"x\\": 56.7, \\"y\\": 16.4}]" route="${routeName}" >}}\n`,
  );
  if (withFile) {
    write(
      `assets/data/maps/routes/${routeName}.geojson`,
      JSON.stringify({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[13.0, 55.6], [14.5, 56.0], [16.4, 56.7]] } }),
    );
  }
  return dir;
}

async function hugo(dir: string) {
  try {
    const r = await run("hugo", ["-d", "public"], { cwd: dir });
    return { code: 0, out: r.stdout + r.stderr };
  } catch (e: any) {
    return { code: e.code ?? 1, out: (e.stdout ?? "") + (e.stderr ?? "") };
  }
}

test("a route that names no file stops the build, naming the page and the route", async () => {
  const dir = fixture("nowhere", false);
  try {
    const { code, out } = await hugo(dir);
    expect(code, out).not.toBe(0);
    expect(out).toContain('map route "nowhere" has no file assets/data/maps/routes/nowhere.geojson');
    expect(out).toContain("trip.md");
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("a committed route is inlined as [lng, lat] pairs", async () => {
  const dir = fixture("there", true);
  try {
    const { code, out } = await hugo(dir);
    expect(code, out).toBe(0);
    const html = fs.readFileSync(path.join(dir, "public", "trip", "index.html"), "utf8");
    expect(html).toContain('data-route="[[13,55.6],[14.5,56],[16.4,56.7]]"');
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
