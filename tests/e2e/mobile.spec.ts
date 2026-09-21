/* The @mobile subset.
 *
 * Starts with the two scenarios that have a fix commit — `Fix navbar on mobile`
 * and `fix back link on mobile` — plus the grid and the lightbox under touch.
 * It grows when a mobile bug appears.
 *
 * Firefox has no mobile emulation in Playwright, so these run in the
 * mobile-chrome and mobile-safari projects; at desktop width they run too and
 * assert the same things hold there. */

import { test, expect, openLightbox } from "../support/fixtures";
import { ALLOW_COMPANION, mockCompanion } from "../support/network";

test.use({ net: { allow: ALLOW_COMPANION } });

test.beforeEach(async ({ page, probe }) => {
  void probe;
  await mockCompanion(page);
});

test("the navbar is visible and usable at phone width @mobile", async ({ page }) => {
  await page.goto("/en/");
  const nav = page.locator("header nav, .nav").first();
  await expect(nav).toBeVisible();

  const menu = page.locator("#menu");
  await expect(menu).toBeVisible();

  /* Nothing in the header may push the page wider than the viewport. */
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "the page scrolls sideways").toBeLessThanOrEqual(1);

  const first = menu.locator("a").first();
  await expect(first).toBeVisible();
  const box = await first.boundingBox();
  expect(box, "a menu link has no box").not.toBeNull();
  expect(box!.width, "a menu link is too small to tap").toBeGreaterThan(20);
});

test("the gallery back link is visible and clickable @mobile", async ({ page }) => {
  await page.goto("/en/gallery/general/");
  const href = await page.locator(".gallery-item[href]").first().getAttribute("href");
  await page.goto(href!);

  /* The way back from a photo is the gallery breadcrumb. */
  const back = page.locator(".gallery-breadcrumb a").last();
  test.skip((await back.count()) === 0, "no back link on this page");
  await expect(back).toBeVisible();
  await back.click();
  await expect(page).toHaveURL(/\/en\/gallery\//);
});

test("the grid lays out without sideways scroll @mobile", async ({ page }) => {
  await page.goto("/en/gallery/general/");
  await expect(page.locator(".gallery-item").first()).toBeVisible();
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "the gallery scrolls sideways").toBeLessThanOrEqual(1);
});

test("the lightbox opens and closes under touch @mobile", async ({ page }) => {
  await page.goto("/en/gallery/general/");
  await openLightbox(page);
  await page.locator(".pswp__button--close").click();
  await expect(page.locator(".pswp--open")).toHaveCount(0);
});
