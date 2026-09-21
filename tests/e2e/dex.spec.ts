/* The dex overview: search, group pills, the photographed-only toggle and the
   empty state. All client-side over data- attributes the build wrote. */

import { test, expect } from "../support/fixtures";

const DEX = "/en/gallery/dex/";

test.beforeEach(async ({ page, probe }) => {
  void probe;
  await page.goto(DEX);
});

test("search narrows the grid", async ({ page }) => {
  const all = await page.locator(".dex-card").count();
  expect(all).toBeGreaterThan(100);

  await page.locator("[data-dex-search]").fill("fox");
  const shown = page.locator(".dex-card:visible");
  const n = await shown.count();
  expect(n).toBeGreaterThan(0);
  expect(n).toBeLessThan(all);
  for (const s of await shown.evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.search!))) {
    expect(s).toContain("fox");
  }
});

test("a group pill narrows the grid to that group", async ({ page }) => {
  const pill = page.locator(".dex-pill[data-group]:not([data-group='all'])").first();
  const group = await pill.getAttribute("data-group");
  await pill.click();
  await expect(pill).toHaveClass(/is-active/);

  const groups = await page.locator(".dex-card:visible").evaluateAll((els) =>
    [...new Set(els.map((e) => (e as HTMLElement).dataset.group))],
  );
  expect(groups).toEqual([group]);

  await page.locator(".dex-pill[data-group='all']").click();
  expect(await page.locator(".dex-card:visible").count()).toBe(await page.locator(".dex-card").count());
});

test("\"only photographed\" leaves only caught species", async ({ page }) => {
  await page.locator("[data-dex-only-caught]").check();
  const caught = await page.locator(".dex-card:visible").evaluateAll((els) =>
    [...new Set(els.map((e) => (e as HTMLElement).dataset.caught))],
  );
  expect(caught).toEqual(["1"]);
  expect(await page.locator(".dex-card:visible").count()).toBeGreaterThan(0);
});

test("the empty state appears when nothing matches", async ({ page }) => {
  const empty = page.locator("[data-dex-empty]");
  await expect(empty).toBeHidden();
  await page.locator("[data-dex-search]").fill("zzzzzzzz-no-such-species");
  await expect(empty).toBeVisible();
  await expect(page.locator(".dex-card:visible")).toHaveCount(0);
});

test("a card links to its species page", async ({ page }) => {
  const card = page.locator(".dex-card").first();
  const href = await card.getAttribute("href");
  expect(href).toMatch(/^\/en\/gallery\/dex\/[a-z0-9-]+\/$/);
  await card.click();
  await expect(page).toHaveURL(new RegExp(`${href}$`));
  await expect(page.locator("h1")).toBeVisible();
});
