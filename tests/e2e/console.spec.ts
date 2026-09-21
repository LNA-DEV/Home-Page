/* One page per theme, and nothing may report an error.
 *
 * `fix console error` is in the commit log; this is the layer that would have
 * found it. Aborted third-party requests are the network policy working, not a
 * failure, and the fixture already excludes them. */

import { test, expect } from "../support/fixtures";
import { ALLOW_COMPANION, ALLOW_MAP_TILES, mockCompanion, mockDetailedMap } from "../support/network";

test.use({ net: { allow: [...ALLOW_COMPANION, ...ALLOW_MAP_TILES] } });

const PAGES: Record<string, string> = {
  home: "/en/",
  "gallery-home": "/en/gallery/",
  "gallery-general": "/en/gallery/general/",
  "gallery-archive": "/en/gallery/archive/",
  "gallery-projects": "/en/gallery/projects/",
  "dex-home": "/en/gallery/dex/",
  "dex-species": "/en/gallery/dex/red-fox/",
  "models-home": "/en/gallery/models/",
  feed: "/en/feed/",
  gaming: "/en/gaming/",
  search: "/en/search/",
  about: "/en/lukas-nagel/",
};

for (const [theme, url] of Object.entries(PAGES)) {
  test(`${theme} reports no console error and no failed request`, async ({ page, probe }) => {
    await mockCompanion(page);
    await mockDetailedMap(page);

    const res = await page.goto(url);
    expect(res?.status(), url).toBeLessThan(400);
    await page.waitForLoadState("networkidle").catch(() => {});
    await page.waitForTimeout(400);

    expect(probe.pageErrors, `${url}\n${probe.pageErrors.join("\n")}`).toEqual([]);
    expect(probe.consoleErrors, `${url}\n${probe.consoleErrors.join("\n")}`).toEqual([]);
    expect(probe.failedRequests, `${url}\n${probe.failedRequests.join("\n")}`).toEqual([]);
  });
}
