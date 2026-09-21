/* The per-photo page: its prev/next stay inside one band, and the copy-link
   button reports what it did. */

import { test, expect } from "../support/fixtures";
import { ALLOW_COMPANION, mockCompanion } from "../support/network";

test.use({ net: { allow: ALLOW_COMPANION } });

test.beforeEach(async ({ page, probe }) => {
  void probe;
  await mockCompanion(page);
});

async function firstPhotoPage(page: import("@playwright/test").Page): Promise<string> {
  await page.goto("/en/gallery/general/");
  const href = await page.locator(".gallery-item[href]").first().getAttribute("href");
  expect(href).toBeTruthy();
  return href!;
}

test("prev and next stay within the gallery", async ({ page }) => {
  await page.goto(await firstPhotoPage(page));
  const next = page.locator(".photo-nav-next");
  await expect(next).toHaveAttribute("href", /\/en\/gallery\/photo\//);

  await next.click();
  await expect(page).toHaveURL(/\/en\/gallery\/photo\/[^/]+\/$/);
  await expect(page.locator(".photo-nav-prev")).toHaveAttribute("href", /\/en\/gallery\/photo\//);
});

test("the copy-link button marks itself copied", async ({ page, browserName }) => {
  await page.goto(await firstPhotoPage(page));

  const button = page.locator(".photo-copy[data-copy]").first();
  /* The control is display:none until `has-clipboard` lands on <html>, so a
     visitor without the Clipboard API never sees something that would do
     nothing. */
  await expect(page.locator("html.has-clipboard")).toBeAttached();
  await expect(button).toBeVisible();

  const permalink = await button.getAttribute("data-copy");
  await button.click();
  await expect(button).toHaveClass(/is-copied/);

  /* Playwright can only grant clipboard permissions in Chromium; everywhere
     else the button's own state is the assertion. */
  test.skip(browserName !== "chromium", "clipboard read is Chromium-only in Playwright");
  const clipboard = await page.evaluate(() => navigator.clipboard.readText());
  expect(clipboard).toBe(permalink);
});

test("the page shows the photo's own metadata", async ({ page }) => {
  await page.goto(await firstPhotoPage(page));
  await expect(page.locator(".photo-hero img")).toBeVisible();
  await expect(page.locator(".photo-meta")).toBeVisible();
  /* The permalink is the permanent /gallery/photo/<uuid>/ alias, not the slug:
     a reworded title moves the slug, the uuid never moves. */
  await expect(page.locator(".photo-permalink")).toHaveAttribute(
    "href",
    /\/en\/gallery\/photo\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/$/,
  );
});
