/* Gallery projects that tell a story, in a browser (docs/concepts/gallery-project-stories.md §10).
 *
 * Story pages are found by their layout (projectPages() reads the content
 * files), not by name, so these keep working after the demo projects are
 * deleted — and skip when no project uses a story layout any more. */

import { test, expect } from "../support/fixtures";
import { ALLOW_COMPANION, mockCompanion, mockMapTiles } from "../support/network";
import { withoutWebGL2 } from "../support/webgl";
import { storyPages } from "../support/site";

test.use({ net: { allow: ALLOW_COMPANION } });

const ANALYTICS = /muninn\.lna-dev\.net/;
const english = () => storyPages().filter((p) => p.lang === "en");
const essay = () => english().find((p) => p.layout === "essay");
const withAreas = (layout: string) => english().find((p) => p.layout === layout && p.areas.length > 0);

test.beforeEach(async ({ page, probe }) => {
  void probe;
  await mockCompanion(page);
  await mockMapTiles(page);
});

for (const theme of ["light", "dark"]) {
  test(`no story page scrolls sideways, ${theme} @mobile`, async ({ page }) => {
    const pages = english();
    test.skip(pages.length === 0, "no project uses project_layout essay or journal");
    await page.addInitScript((t) => localStorage.setItem("pref-theme", t), theme);
    for (const p of pages) {
      await page.goto(p.url);
      await expect(page.locator(".story-page")).toHaveAttribute("data-view", "story");
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${p.url} scrolls sideways`).toBeLessThanOrEqual(1);

      /* On a phone a trio is a strip to swipe, scrolling inside itself. */
      const trio = page.locator(".story-trio").first();
      if ((await trio.count()) && (page.viewportSize()?.width ?? 1280) <= 768) {
        const strip = await trio.evaluate((el) => ({ sw: el.scrollWidth, cw: el.clientWidth, ox: getComputedStyle(el).overflowX }));
        expect(strip.ox, `${p.url}: the trio is not a strip`).toBe("auto");
        expect(strip.sw, `${p.url}: the trio does not scroll`).toBeGreaterThan(strip.cw);
      }
    }
  });
}

test("the toggle is reached with Tab and switched with Enter", async ({ page }) => {
  const p = essay() ?? english()[0];
  test.skip(!p, "no story page");
  await page.goto(p!.url);
  const grid = page.locator('.story-toggle button[data-view="grid"]');
  await expect(grid).toBeVisible();
  await expect(grid).toHaveAttribute("aria-pressed", "false");

  let focused = false;
  for (let i = 0; i < 60 && !focused; i++) {
    await page.keyboard.press("Tab");
    focused = await grid.evaluate((el) => el === document.activeElement);
  }
  expect(focused, "the Grid button cannot be reached with Tab").toBe(true);
  await page.keyboard.press("Enter");

  await expect(grid).toHaveAttribute("aria-pressed", "true");
  await expect(page).toHaveURL(/#grid$/);
  await expect(page.locator("#grid .gallery-item").first()).toBeVisible();
  await expect(page.locator(".story")).toBeHidden();

  /* And back. */
  await page.locator('.story-toggle button[data-view="story"]').press("Enter");
  await expect(page.locator(".story")).toBeVisible();
  await expect(page.locator("#grid")).toBeHidden();
});

test('"Show as grid" at the end of the story switches to the grid', async ({ page }) => {
  /* footer.html smooth-scrolls every #link with preventDefault + pushState,
     which fires no hashchange; the story script has to catch this one first. */
  const p = essay() ?? english()[0];
  test.skip(!p, "no story page");
  await page.goto(p!.url);
  const link = page.locator('.story-end a[href="#grid"]');
  await link.scrollIntoViewIfNeeded();
  await link.click();
  await expect(page.locator(".story-page")).toHaveAttribute("data-view", "grid");
  await expect(page).toHaveURL(/#grid$/);
  await expect(page.locator("#grid .gallery-item").first()).toBeInViewport();
  await expect(page.locator('.story-toggle button[data-view="grid"]')).toHaveAttribute("aria-pressed", "true");
});

test("a photo's id in the URL opens the grid and its lightbox, and closing keeps the grid", async ({ page }) => {
  const p = essay() ?? english()[0];
  test.skip(!p, "no story page");
  await page.goto(p!.url);
  const id = await page.locator("#grid .gallery-item[data-id]").first().getAttribute("data-id");
  await page.goto(`${p!.url}#${id}`);
  await expect(page.locator(".story-page")).toHaveAttribute("data-view", "grid");
  await expect(page.locator(".pswp--open")).toBeVisible();
  await expect(page.locator(".pswp__img:not(.pswp__img--placeholder)").first()).toBeAttached();
  await page.locator(".pswp__button--close").click();
  await expect(page.locator(".pswp--open")).toHaveCount(0);
  await expect(page.locator(".story-page")).toHaveAttribute("data-view", "grid");
});

test("the project map draws on the site's basemap and asks nobody else @mobile", async ({ page, probe }) => {
  const p = withAreas("essay") ?? withAreas("journal");
  test.skip(!p, "no story page with areas");
  await page.goto(p!.url);
  await page.locator("#map").scrollIntoViewIfNeeded();
  await expect(page.locator("#map .leaflet-gl-layer")).toHaveCount(1);
  await expect(page.locator("#map path.leaflet-interactive, #map path")).not.toHaveCount(0);
  await expect(page.locator("#map .story-area-list")).toBeVisible();

  /* Zoom stops at 13: past it a 1 km circle shows every path inside it. */
  const zoomIn = page.locator("#map .leaflet-control-zoom-in");
  for (let i = 0; i < 12; i++) {
    if (await zoomIn.evaluate((el) => el.classList.contains("leaflet-disabled"))) break;
    await zoomIn.click();
    await page.waitForTimeout(300);
  }
  await expect(zoomIn).toHaveClass(/leaflet-disabled/);

  await page.waitForTimeout(500);
  const offsite = probe.network.external.filter((u) => !/companion\.lna-dev\.net/.test(u) && !ANALYTICS.test(u));
  expect(offsite, `the project map reached a third party\n${offsite.join("\n")}`).toEqual([]);
});

test("without WebGL2 there is no map, and the list of areas stands in", async ({ page }) => {
  const p = withAreas("essay") ?? withAreas("journal");
  test.skip(!p, "no story page with areas");
  await withoutWebGL2(page);
  await page.goto(p!.url);
  await page.locator("#map").scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await expect(page.locator("#map .story-map-canvas")).toBeHidden();
  await expect(page.locator(".leaflet-container")).toHaveCount(0);
  await expect(page.locator("#map .story-area-list li").first()).toBeVisible();
});

test("scrolling a journal never keeps more than four mini maps alive", async ({ page }) => {
  const p = withAreas("journal");
  test.skip(!p, "no journal with areas");
  await page.goto(p!.url);
  const minis = await page.locator("[data-mini-map]").count();
  test.skip(minis === 0, "no outing with text and an area");

  let most = 0;
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y <= height; y += 300) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(150);
    most = Math.max(most, await page.locator(".journal-mini [data-flavor]").count());
  }
  for (let y = height; y >= 0; y -= 600) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(150);
    most = Math.max(most, await page.locator(".journal-mini [data-flavor]").count());
  }
  expect(most, "no mini map was ever built").toBeGreaterThan(0);
  expect(most, "more than four mini maps alive at once").toBeLessThanOrEqual(4);
});
