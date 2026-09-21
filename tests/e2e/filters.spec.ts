/* The category filter bubbles on /gallery/general/ — JS-only, client-side, on
   data-category. No navigation, no rebuild: get it wrong and the grid silently
   shows the wrong set. */

import { test, expect } from "../support/fixtures";

test("a category pill leaves only that category, and \"all\" restores", async ({ page, probe }) => {
  void probe;
  await page.goto("/en/gallery/general/");

  const total = await page.locator(".gallery-item").count();
  expect(total).toBeGreaterThan(50);

  const pill = page.locator(".filter-pill[data-category]:not([data-category='all'])").first();
  const category = await pill.getAttribute("data-category");
  await pill.click();

  await expect(pill).toHaveClass(/active/);
  const shown = page.locator(".gallery-item:visible");
  const shownCount = await shown.count();
  expect(shownCount).toBeGreaterThan(0);
  expect(shownCount).toBeLessThan(total);

  const categories = await shown.evaluateAll((els) =>
    [...new Set(els.map((e) => (e as HTMLElement).dataset.category))],
  );
  expect(categories).toEqual([category]);

  await page.locator(".filter-pill[data-category='all']").click();
  await expect(page.locator(".gallery-item:visible")).toHaveCount(total);
});

test("every pill names a category that exists on the grid", async ({ page, probe }) => {
  void probe;
  await page.goto("/en/gallery/general/");
  const pills = await page.locator(".filter-pill[data-category]").evaluateAll((els) =>
    els.map((e) => (e as HTMLElement).dataset.category!).filter((c) => c !== "all"),
  );
  const onGrid = await page.locator(".gallery-item[data-category]").evaluateAll((els) =>
    [...new Set(els.map((e) => (e as HTMLElement).dataset.category))],
  );
  expect(pills.filter((p) => !onGrid.includes(p)), "a pill that filters to nothing").toEqual([]);
});
