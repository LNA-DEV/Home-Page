/* The language switcher.
 *
 * docs/concepts/testing.md §2 expects "from a translated page it lands on the
 * translation, from an untranslated page on the other language's home". Until
 * 2026-11-18 the switcher pointed at the language home from every page; since
 * docs/concepts/multilingual-home.md §6a it follows .Translations — a post, a
 * dex species, a model, and every photo page, which carries a translationKey
 * and a real translation with its own slug. tests/static/multilingual-home.spec.ts
 * holds that for every page of the build; these scenarios walk it once in a
 * browser. */

import { test, expect } from "../support/fixtures";

const PAGES = [
  "/en/",
  "/en/gallery/general/",
  "/en/gallery/dex/red-fox/",
  "/en/posts/photography/wiki-loves-earth-2025/",
];

test("every page offers the other two languages", async ({ page, probe }) => {
  void probe;
  for (const url of PAGES) {
    await page.goto(url);
    const links = page.locator(".lang-switch a");
    await expect(links, url).toHaveCount(2);
  }
});

test("following the switcher lands in that language", async ({ page, probe }) => {
  void probe;
  await page.goto("/en/gallery/general/");
  await page.locator('.lang-switch a[href*="/de/"]').first().click();
  await expect(page).toHaveURL(/\/de\//);
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
});

test("the three language homes are each in their own language", async ({ page, probe }) => {
  void probe;
  for (const lang of ["en", "de", "sv"]) {
    await page.goto(`/${lang}/`);
    await expect(page.locator("html")).toHaveAttribute("lang", lang);
  }
});

test("on a translated page the switcher goes to the translation", async ({ page, probe }) => {
  void probe;
  /* A photo page is the sharpest case: the three languages have three different
     slugs, so the switcher has to follow the translation, not guess a path. */
  await page.goto("/en/gallery/general/");
  const href = await page.locator(".gallery-item[href]").first().getAttribute("href");
  await page.goto(href!);

  const alternate = await page
    .locator('link[rel="alternate"][hreflang="de"]')
    .first()
    .getAttribute("href");
  expect(alternate, "no German alternate on a photo page").toBeTruthy();
  expect(alternate).toMatch(/\/de\/gallery\/photo\/[^/]+\/$/);

  const switcher = await page.locator('.lang-switch a[hreflang="de"]').getAttribute("href");
  expect(switcher).toBe(alternate);

  await page.locator('.lang-switch a[hreflang="de"]').click();
  await expect(page).toHaveURL(alternate!);
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
  await expect(page.locator(".photo-hero img")).toBeVisible();
});

test("on a page with no translation the switcher goes to that language's home", async ({ page, probe }) => {
  void probe;
  await page.goto("/en/posts/photography/my-workflow/");
  const switcher = await page.locator('.lang-switch a[hreflang="de"]').getAttribute("href");
  expect(switcher).toMatch(/\/de\/$/);
});
