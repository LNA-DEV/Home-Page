/* The activity feed: client-side filters, and the photo-item contract with the
   gallery — a photo item's link jumps to the gallery and opens the lightbox on
   the right photo. */

import { test, expect } from "../support/fixtures";
import { ALLOW_COMPANION, mockCompanion } from "../support/network";
import { awaitLightboxReady } from "../support/fixtures";

test.use({ net: { allow: ALLOW_COMPANION } });

test.beforeEach(async ({ page, probe }) => {
  void probe;
  await mockCompanion(page);
});

test("a filter button hides the other kinds", async ({ page }) => {
  await page.goto("/en/feed/");
  /* The feed groups items per month into one container per kind
     (.activity-photos, .activity-posts, …); filtering hides the containers. */
  const months = page.locator(".activity-month");
  expect(await months.count()).toBeGreaterThan(0);

  const kinds = ["posts", "photos", "talks", "awards", "publications"];
  const before: Record<string, number> = {};
  for (const k of kinds) before[k] = await page.locator(`.activity-${k}:visible`).count();

  const kind = kinds.find((k) => before[k] > 0)!;
  await page.locator(`.activity-filter[data-filter="${kind}"]`).click();
  await expect(page.locator(`.activity-filter[data-filter="${kind}"]`)).toHaveClass(/active/);

  expect(await page.locator(`.activity-${kind}:visible`).count(), kind).toBeGreaterThan(0);
  for (const other of kinds.filter((k) => k !== kind)) {
    expect(await page.locator(`.activity-${other}:visible`).count(), `${other} should be hidden`).toBe(0);
  }

  await page.locator('.activity-filter[data-filter="all"]').click();
  for (const k of kinds) {
    expect(await page.locator(`.activity-${k}:visible`).count(), k).toBe(before[k]);
  }
});

test("a photo item lands on the gallery and opens that photo", async ({ page }) => {
  await page.goto("/en/feed/");
  const link = page.locator('a[href*="/gallery/"][href*="#"]').first();
  test.skip((await link.count()) === 0, "no photo item in the feed");

  const href = await link.getAttribute("href");
  const hash = href!.split("#")[1];
  await link.click();
  await expect(page).toHaveURL(new RegExp(`#${hash}$`));
  await awaitLightboxReady(page);
});
