/* PhotoSwipe, the deep link, and the hand-wired history.
 *
 * `lightbox.js` gives an open photo exactly one history entry: swiping through
 * thirty slides must still cost a single back press, and back must close the
 * viewer rather than leave the gallery. That is the bit with its own worktree in
 * the commit log, and the bit no build can check. */

import { test, expect, firstPhotoId, openLightbox, awaitLightboxReady } from "../support/fixtures";
import { ALLOW_COMPANION, mockCompanion } from "../support/network";

test.use({ net: { allow: ALLOW_COMPANION } });

const GRID = "/en/gallery/general/";

test.beforeEach(async ({ page, probe }) => {
  void probe; // installs the network policy before the first navigation
  await mockCompanion(page);
});

test("clicking a photo opens the viewer on that photo", async ({ page }) => {
  await page.goto(GRID);
  const id = await firstPhotoId(page);

  await openLightbox(page);
  await expect(page).toHaveURL(new RegExp(`#${id}$`));
});

test("the close button closes the viewer and stays on the gallery", async ({ page }) => {
  await page.goto(GRID);
  await openLightbox(page);

  await page.locator(".pswp__button--close").click();
  await expect(page.locator(".pswp--open")).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`${GRID}$`));
});

test("Escape closes the viewer and stays on the gallery", async ({ page }) => {
  await page.goto(GRID);
  await openLightbox(page);

  await page.keyboard.press("Escape");
  await expect(page.locator(".pswp--open")).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`${GRID}$`));
});

test("a deep link opens that slide", async ({ page }) => {
  await page.goto(GRID);
  const ids = await page.locator(".gallery-item[data-id]").evaluateAll((els) =>
    els.map((e) => (e as HTMLElement).dataset.id!),
  );
  const target = ids[3];

  await page.goto(`${GRID}#${target}`);
  await awaitLightboxReady(page);

  /* The counter is PhotoSwipe's own statement of which slide is current, and it
     is 1-based against the same order the grid is in. */
  await expect(page.locator(".pswp__counter")).toHaveText(new RegExp(`^${4} / ${ids.length}$`));
});

test("back closes the viewer instead of leaving the page", async ({ page }) => {
  await page.goto(GRID);
  await openLightbox(page);

  await page.goBack();
  await expect(page.locator(".pswp--open")).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`${GRID}$`));
  await expect(page.locator(".gallery-item").first()).toBeVisible();
});

test("swiping five slides still costs one back press", async ({ page }) => {
  /* One history entry per lightbox session, not per slide: slide changes use
     replaceState. Get this wrong and leaving the gallery takes six presses. */
  await page.goto(GRID);
  await openLightbox(page);

  for (let i = 0; i < 5; i++) {
    await page.keyboard.press("ArrowRight");
    await page.waitForTimeout(150);
  }
  await expect(page.locator(".pswp__counter")).toHaveText(/^6 \//);

  await page.goBack();
  await expect(page.locator(".pswp--open")).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`${GRID}$`));
});

test("the info panel shows the species link and the editing software", async ({ page }) => {
  await page.goto(GRID);
  /* Pick a photo that has both: a species (so the Species row links to the dex)
     and a Software value. */
  const idx = await page.locator(".gallery-item").evaluateAll((els) =>
    els.findIndex(
      (e) =>
        e.querySelector(".caption-species[data-dex-url]") && e.querySelector(".caption-software"),
    ),
  );
  test.skip(idx < 0, "no photo on this grid has both a species and a software value");

  await openLightbox(page, idx);
  await page.locator(".pswp__button--info").click();

  const popup = page.locator(".pswp-info-popup.visible");
  await expect(popup).toBeVisible();
  await expect(popup.locator('[data-field="species"] a, a[href*="/gallery/dex/"]').first()).toBeVisible();
  await expect(popup).toContainText(/darktable|Lightroom|GIMP|Capture One/i);
});
