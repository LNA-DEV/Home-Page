/* Design system — docs/concepts/design-system.md §9 (contrast) and §5
   (page edges). The styleguide shows every colour token in a light and a dark
   panel side by side (each panel sets `color-scheme`, and every token is
   light-dark()), so one page load checks both themes. */

import { test, expect } from "@playwright/test";

const STYLEGUIDE = "/en/styleguide/";

test("every text and UI sample on the styleguide meets its contrast", async ({ page }) => {
  await page.goto(STYLEGUIDE);
  const failures = await page.evaluate(() => {
    function parse(c: string): [number, number, number, number] {
      const n = c.match(/[\d.]+/g)!.map(Number);
      // "rgb(r, g, b)", "rgba(r, g, b, a)" or "color(srgb r g b / a)" (0–1)
      if (c.startsWith("color(")) return [n[0] * 255, n[1] * 255, n[2] * 255, n[3] ?? 1];
      return [n[0], n[1], n[2], n[3] ?? 1];
    }
    function lum([r, g, b]: number[]) {
      const f = (v: number) => {
        v /= 255;
        return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    }
    function background(el: Element) {
      for (let e: Element | null = el; e; e = e.parentElement) {
        const c = parse(getComputedStyle(e).backgroundColor);
        if (c[3] >= 1) return c;
      }
      return [255, 255, 255, 1];
    }
    const out: string[] = [];
    document.querySelectorAll<HTMLElement>("[data-contrast]").forEach((el) => {
      const min = Number(el.dataset.contrast);
      const cs = getComputedStyle(el);
      const fg = parse(el.dataset.contrastOf === "border" ? cs.borderTopColor : cs.color);
      const bg = el.dataset.contrastOf === "border" && el.parentElement ? background(el.parentElement) : background(el);
      const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
      const ratio = (a + 0.05) / (b + 0.05);
      if (ratio < min) {
        const scheme = el.closest<HTMLElement>("[data-scheme]")?.dataset.scheme ?? "?";
        out.push(`${scheme}: "${el.textContent?.trim()}" ${ratio.toFixed(2)}:1 < ${min}:1`);
      }
    });
    return out;
  });
  expect(failures).toEqual([]);
  expect(await page.locator("[data-contrast]").count()).toBeGreaterThan(40);
});

test("the styleguide lists every colour token in both themes", async ({ page }) => {
  await page.goto(STYLEGUIDE);
  const panels = page.locator(".sg-theme");
  await expect(panels).toHaveCount(2);
  const light = await panels.nth(0).locator(".sg-swatch").count();
  const dark = await panels.nth(1).locator(".sg-swatch").count();
  expect(light).toBeGreaterThan(50);
  expect(dark).toBe(light);
  /* light-dark() resolved per panel: the accent differs between the two. */
  const values = await panels.locator(".sg-swatch").evaluateAll((items) =>
    items.filter((i) => i.querySelector("code")?.textContent === "--accent").map((i) => i.querySelector("span")?.textContent),
  );
  expect(values).toHaveLength(2);
  expect(values[0]).not.toBe(values[1]);
});
