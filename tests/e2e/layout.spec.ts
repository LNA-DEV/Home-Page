/* Page edges and widths — docs/concepts/design-system.md §5.

   The rule people perceive as "tidy", and the one screenshots catch worst:
     - a wide page's content edge is the logo's edge, at every width;
     - a text page is centred at --width-text;
     - nothing but an l-bleed block comes closer than the gutter to the edge;
     - nothing scrolls sideways.
   Measured, not screenshotted, so it holds on any machine. */

import { test, expect } from "../support/fixtures";
import { ALLOW_COMPANION, mockCompanion } from "../support/network";

test.use({ net: { allow: ALLOW_COMPANION } });
test.beforeEach(async ({ page, probe }) => {
  void probe;
  await mockCompanion(page);
});

const WIDE = [
  "/en/gallery/",
  "/en/gallery/general/",
  "/en/gallery/dex/",
  "/en/gallery/dex/white-tailed-eagle/",
  "/en/gallery/gear/",
  "/en/gallery/tags/bird/",
];
const TEXT = ["/en/lukas-nagel/", "/de/posts/photography/seeadler-fischadler-nicklheimer-filzen/", "/en/reading-list/"];
const WIDTHS = [375, 768, 1440, 1920];

async function measure(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const main = document.querySelector<HTMLElement>("main.main")!;
    const cs = getComputedStyle(main);
    const box = main.getBoundingClientRect();
    const gutter = parseFloat(cs.paddingLeft);
    const tooClose: string[] = [];
    /* The page's blocks, three levels down — deeper than that is a component's
       inside, and a scrolling row's items legitimately run past the edge. */
    const clipped = (el: Element) => {
      for (let p = el.parentElement; p && p !== main; p = p.parentElement) {
        if (getComputedStyle(p).overflowX !== "visible") return true;
      }
      return false;
    };
    main.querySelectorAll<HTMLElement>(":scope > *, :scope > * > *, :scope > * > * > *").forEach((el) => {
      if (el.closest(".l-bleed, .pswp, [hidden], dialog")) return;
      const r = el.getBoundingClientRect();
      const pos = getComputedStyle(el).position;
      if (r.width <= 2 || r.height <= 2 || pos === "fixed" || pos === "absolute" || clipped(el)) return;
      if (r.left < gutter - 1 || r.right > innerWidth - gutter + 1) {
        tooClose.push(`${el.tagName.toLowerCase()}.${[...el.classList].join(".")} ${Math.round(r.left)}–${Math.round(r.right)}`);
      }
    });
    return {
      layout: main.dataset.layout,
      logo: document.querySelector(".logo")!.getBoundingClientRect().left,
      contentLeft: box.left + gutter,
      contentRight: box.right - parseFloat(cs.paddingRight),
      gutter,
      viewport: innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      tooClose: tooClose.slice(0, 5),
    };
  });
}

for (const width of WIDTHS) {
  test.describe(`at ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    for (const url of WIDE) {
      test(`${url} lines up with the logo`, async ({ page }) => {
        await page.goto(url);
        const m = await measure(page);
        expect(m.layout).toBe("wide");
        expect(Math.abs(m.contentLeft - m.logo), `content ${m.contentLeft} vs logo ${m.logo}`).toBeLessThanOrEqual(1);
        expect(m.contentRight - m.contentLeft).toBeLessThanOrEqual(1060 + 1);
        expect(m.gutter).toBe(width <= 768 ? 16 : 24);
        expect(m.scrollWidth).toBeLessThanOrEqual(m.viewport);
        expect(m.tooClose).toEqual([]);
      });
    }

    for (const url of TEXT) {
      test(`${url} is a centred text column`, async ({ page }) => {
        await page.goto(url);
        const m = await measure(page);
        expect(m.layout).toBe("text");
        expect(m.contentRight - m.contentLeft).toBeLessThanOrEqual(720 + 1);
        expect(Math.abs(m.contentLeft - (m.viewport - m.contentRight))).toBeLessThanOrEqual(1);
        expect(m.scrollWidth).toBeLessThanOrEqual(m.viewport);
      });
    }
  });
}
