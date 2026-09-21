/* The gaming grid: client-side sort, and a platform row that appears only when
   there is something to choose between. */

import { test, expect } from "../support/fixtures";

test.beforeEach(async ({ page, probe }) => {
  void probe;
  await page.goto("/en/gaming/");
});

async function titles(page: import("@playwright/test").Page): Promise<string[]> {
  return page.locator("[data-title]").evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.title!));
}

test("sorting reorders the tiles", async ({ page }) => {
  const byPlaytime = await titles(page);
  expect(byPlaytime.length).toBeGreaterThan(3);

  await page.locator('.gaming-btn[data-sort="alpha"], .gaming-btn[data-sort="title"]').first().click();
  const alpha = await titles(page);
  expect(alpha).toHaveLength(byPlaytime.length);
  expect([...alpha].sort((a, b) => a.localeCompare(b))).toEqual(alpha);

  await page.locator('.gaming-btn[data-sort="recent"]').click();
  const recent = await titles(page);
  expect(recent).toHaveLength(byPlaytime.length);
  expect(recent).not.toEqual(alpha);

  await page.locator('.gaming-btn[data-sort="playtime"]').click();
  expect(await titles(page)).toEqual(byPlaytime);
});

test("the platform row appears only with two or more platforms", async ({ page }) => {
  const platforms = await page.locator("[data-platform]").evaluateAll((els) =>
    [...new Set(els.map((e) => (e as HTMLElement).dataset.platform))],
  );
  const row = page.locator(".gaming-filter").first();
  if (platforms.length >= 2) {
    await expect(row).toBeVisible();
  } else {
    expect(await row.count()).toBe(0);
  }
});

test("the stats header counts what the grid shows", async ({ page }) => {
  const tiles = await page.locator("[data-title]").count();
  await expect(page.locator(".gaming-stats")).toContainText(String(tiles));
});

test("a hidden game is nowhere on the page", async ({ page }) => {
  /* data/gamingIgnore.yaml drops a title at the shared choke point, so it must
     be gone from the grid, the stats and the About preview alike. */
  const fs = await import("node:fs");
  const path = await import("node:path");
  const { REPO } = await import("../support/site");
  const file = path.join(REPO, "data", "gamingIgnore.yaml");
  test.skip(!fs.existsSync(file), "no ignore list");

  /* Only the entries under `titles:` — the header comment carries examples in
     the same shape, and matching those would make the test lie. */
  const lines = fs.readFileSync(file, "utf8").split("\n");
  const start = lines.findIndex((l) => /^titles:/.test(l.trim()) && !l.trim().startsWith("#"));
  const ignored: string[] = [];
  for (const line of lines.slice(start + 1)) {
    const t = line.trim();
    if (t.startsWith("#") || t === "") continue;
    if (!t.startsWith("- ")) break;
    ignored.push(t.slice(2).trim().replace(/^["']|["']$/g, ""));
  }
  test.skip(ignored.length === 0, "the ignore list is empty");

  /* Compared against the tiles' own titles rather than the page text: an
     ignored title like "The Way" is three ordinary words that occur in prose. */
  const shown = (await titles(page)).map((t) => t.trim().toLowerCase());
  const leaked = ignored.filter((t) => shown.includes(t.trim().toLowerCase()));
  expect(leaked, `hidden in data/gamingIgnore.yaml but still a tile: ${leaked.join(", ")}`).toEqual([]);
});
