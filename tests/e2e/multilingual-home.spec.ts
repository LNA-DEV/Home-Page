/* What the visitor's browser language does: docs/concepts/multilingual-home.md
 * §4, §5, §6a, and the two SEO conditions of §8.
 *
 * Playwright's `locale` sets both navigator.languages and Accept-Language, which
 * is exactly what a real browser with that language sends. The HTML under test
 * is identical in every scenario (tests/static/multilingual-home.spec.ts holds
 * it); only the attributes the inline script in head.html sets on <html>, and
 * the CSS keyed on them, differ.
 *
 * The no-shift scenario blocks the web fonts. The header shifts by a fraction of
 * a pixel while Cantarell swaps in on every page, bar or no bar; that shift is
 * the font's, not this feature's, and it would drown the one thing measured
 * here — that the bar and the reordered block are in place from the first
 * frame. Without fonts, a page must not shift at all. */

import { test, expect } from "../support/fixtures";
import type { Page } from "@playwright/test";

const POST = "/en/posts/media/fediverse/"; // translated: has /de/posts/media/fediverse/

const visibleBar = (page: Page) => page.locator(".lang-hint:visible");

async function groupOrder(page: Page): Promise<string[]> {
  const groups = page.locator(".lang-more-group");
  const out: { lang: string; y: number }[] = [];
  for (let i = 0; i < (await groups.count()); i++) {
    const g = groups.nth(i);
    out.push({ lang: (await g.getAttribute("data-lang"))!, y: (await g.boundingBox())!.y });
  }
  return out.sort((a, b) => a.y - b.y).map((g) => g.lang);
}

test.describe("an English browser", () => {
  test.use({ locale: "en-US" });

  test("sees no bar on an English page, and the groups in their own order", async ({ page, probe }) => {
    void probe;
    await page.goto("/en/");
    await expect(page.locator("html")).toHaveAttribute("data-top", "en");
    await expect(visibleBar(page)).toHaveCount(0);
    expect(await groupOrder(page)).toEqual(["de", "sv"]);
  });

  test("is offered English on a German page that has it", async ({ page, probe }) => {
    void probe;
    await page.goto("/de/posts/media/fediverse/");
    await expect(visibleBar(page)).toHaveCount(1);
    await expect(visibleBar(page)).toHaveAttribute("data-lang", "en");
    await expect(visibleBar(page).locator("a")).toHaveAttribute("href", /\/en\/posts\/media\/fediverse\/$/);
  });
});

test.describe("a German browser", () => {
  test.use({ locale: "de-DE" });

  test("on /en/: the German bar, in German, and the German group first and marked", async ({ page, probe }) => {
    void probe;
    await page.goto("/en/");
    await expect(visibleBar(page)).toHaveCount(1);
    await expect(visibleBar(page)).toHaveAttribute("lang", "de");
    await expect(visibleBar(page).locator("a")).toHaveAttribute("href", /\/de\/$/);
    expect(await groupOrder(page)).toEqual(["de", "sv"]);
    const de = page.locator('.lang-more-group[data-lang="de"]');
    const sv = page.locator('.lang-more-group[data-lang="sv"]');
    expect(await de.evaluate((e) => getComputedStyle(e).borderTopWidth)).toBe("2px");
    expect(await sv.evaluate((e) => getComputedStyle(e).borderTopWidth)).toBe("1px");
  });

  test("on a translated post: the bar names the German post", async ({ page, probe }) => {
    void probe;
    await page.goto(POST);
    await expect(visibleBar(page)).toHaveCount(1);
    await expect(visibleBar(page).locator("cite")).toHaveText("Was ist das Fediverse?");
  });

  test("on an untranslated post: no bar", async ({ page, probe }) => {
    void probe;
    await page.goto("/en/posts/photography/my-workflow/");
    await expect(page.locator(".lang-hint")).toHaveCount(0);
  });

  test("✕ hides the bar, and it stays hidden after a reload and on the next page", async ({ page, probe }) => {
    void probe;
    await page.goto(POST);
    await visibleBar(page).locator(".lang-hint__close").click();
    await expect(visibleBar(page)).toHaveCount(0);
    await page.reload();
    await expect(visibleBar(page)).toHaveCount(0);
    await page.goto("/en/");
    await expect(visibleBar(page)).toHaveCount(0);
  });

  test("picking English in the switcher wins over the browser language", async ({ page, probe }) => {
    void probe;
    await page.goto("/de/posts/media/fediverse/");
    await page.locator('.lang-switch a[hreflang="en"]').click();
    await expect(page).toHaveURL(/\/en\/posts\/media\/fediverse\/$/);
    await expect(page.locator("html")).toHaveAttribute("data-top", "en");
    await expect(visibleBar(page)).toHaveCount(0);
    await page.goto("/");
    await expect(page).toHaveURL(/\/en\/$/);
  });
});

test.describe("a Swedish browser", () => {
  test.use({ locale: "sv-SE" });

  test("on /en/: the Swedish group moves above the German one", async ({ page, probe }) => {
    void probe;
    await page.goto("/en/");
    expect(await groupOrder(page)).toEqual(["sv", "de"]);
    await expect(visibleBar(page)).toHaveAttribute("data-lang", "sv");
  });
});

test.describe("the root page", () => {
  for (const [locale, home] of [
    ["de-DE", "/de/"],
    ["sv-SE", "/sv/"],
    ["en-GB", "/en/"],
    ["fr-FR", "/en/"],
  ] as const) {
    test.describe(locale, () => {
      test.use({ locale });
      test(`sends ${locale} to ${home}`, async ({ page, probe }) => {
        void probe;
        await page.goto("/");
        await expect(page).toHaveURL(new RegExp(`${home}$`));
      });
    });
  }

  test.describe("without JavaScript", () => {
    test.use({ locale: "de-DE", javaScriptEnabled: false });
    test("goes to /en/, and no bar shows anywhere", async ({ page, probe }) => {
      void probe;
      await page.goto("/");
      await expect(page).toHaveURL(/\/en\/$/);
      await expect(visibleBar(page)).toHaveCount(0);
      expect(await groupOrder(page)).toEqual(["de", "sv"]);
    });
  });
});

test.describe("the SEO conditions (§8)", () => {
  test.use({ locale: "de-DE" });

  for (const url of ["/en/", POST]) {
    test(`no layout shift on ${url} with the bar showing`, async ({ page, probe, browserName }) => {
      void probe;
      /* Only Chromium reports layout-shift entries; elsewhere the observer would
         see nothing and the test would pass without measuring anything. */
      test.skip(browserName !== "chromium", "layout-shift entries are Chromium-only");
      /* Cantarell's swap shifts the header a little on every page, bar or no
         bar, so the font's @font-face is served empty. Blocking only the font
         file is not enough where Cantarell is installed system-wide
         (Fedora/GNOME): Chrome then swaps to the local font once the web font
         fails. */
      await page.route(/\/css\/cantarell\.css$/, (route) => route.fulfill({ contentType: "text/css", body: "" }));
      await page.addInitScript(() => {
        (window as any).__shifts = [];
        new PerformanceObserver((list) => {
          for (const e of list.getEntries() as any[]) (window as any).__shifts.push(e.value);
        }).observe({ type: "layout-shift", buffered: true });
      });
      await page.goto(url);
      await expect(visibleBar(page)).toHaveCount(1);
      await page.waitForLoadState("load");
      await page.waitForTimeout(500);
      const shifts = await page.evaluate(() => (window as any).__shifts as number[]);
      expect(shifts, "the page shifted after first paint").toEqual([]);
    });
  }

  test("the bar is in the page, not over it, and small enough to leave the heading in view @mobile", async ({ page, probe }) => {
    void probe;
    await page.goto(POST);
    const bar = visibleBar(page);
    await expect(bar).toHaveCount(1);
    expect(await bar.evaluate((e) => getComputedStyle(e).position)).toMatch(/^(static|relative)$/);
    expect(await page.locator(".lang-hints").evaluate((e) => getComputedStyle(e).position)).toMatch(/^(static|relative)$/);
    const box = (await bar.boundingBox())!;
    expect(box.height, "the bar is too tall").toBeLessThanOrEqual(120);
    const h1 = (await page.locator("h1").first().boundingBox())!;
    const viewport = page.viewportSize()!;
    expect(h1.y + h1.height, "the heading is pushed out of the first screen").toBeLessThanOrEqual(viewport.height);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, "the bar makes the page scroll sideways").toBeLessThanOrEqual(1);
  });
});
