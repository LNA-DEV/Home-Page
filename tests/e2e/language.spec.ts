/* The language switcher.
 *
 * NOTE, 2026-09-20: docs/concepts/testing.md §2 expects "from a translated page
 * it lands on the translation, from an untranslated page on the other
 * language's home". The shipped behaviour is the second half only — the
 * switcher points at the language home from EVERY page, including pages that
 * are fully translated: a post, a dex species, a model, and all 648 photo pages,
 * which carry a translationKey and a real translation with its own slug.
 *
 * These tests assert what the site does, not what the concept assumed, and say
 * so out loud. If the switcher is ever taught to follow .Translations, the last
 * test here is the one to turn around. */

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

test("a translated page's translation is reachable, even if the switcher does not go there", async ({ page, probe }) => {
  void probe;
  /* The link that does exist is the hreflang alternate in the head. A photo page
     is the sharpest case: the three languages have three different slugs, so
     nothing but the alternate can find the sibling. */
  await page.goto("/en/gallery/general/");
  const href = await page.locator(".gallery-item[href]").first().getAttribute("href");
  await page.goto(href!);

  const alternate = await page
    .locator('link[rel="alternate"][hreflang="de"]')
    .first()
    .getAttribute("href");
  expect(alternate, "no German alternate on a photo page").toBeTruthy();
  expect(alternate).toMatch(/\/de\/gallery\/photo\/[^/]+\/$/);

  await page.goto(alternate!);
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
  await expect(page.locator(".photo-hero img")).toBeVisible();

  /* The switcher, on that same page, points at the language home instead. */
  const switcher = await page.locator('.lang-switch a[href*="/en/"]').first().getAttribute("href");
  expect(switcher).toMatch(/\/en\/$/);
});
