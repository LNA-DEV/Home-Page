/* The download dialog.
 *
 * The module makes no filename — Hugo computes the `download` attribute and it
 * arrives finished in data-download-name — and it only ever ADDS the
 * all-rights-reserved gate, so the no-JavaScript path is the ungated one. Both
 * of those are properties a test can hold onto. */

import { test, expect, openLightbox } from "../support/fixtures";
import { ALLOW_COMPANION, mockCompanion } from "../support/network";
import { gallery } from "../support/site";

test.use({ net: { allow: ALLOW_COMPANION } });

const GRID = "/en/gallery/general/";

test.beforeEach(async ({ page, probe }) => {
  void probe;
  await mockCompanion(page);
});

test("the dialog opens over the viewer and lists the sizes", async ({ page }) => {
  await page.goto(GRID);
  await openLightbox(page);

  await page.locator(".pswp__button--download-button").click();
  const dialog = page.locator("dialog.gallery-download");
  await expect(dialog).toBeVisible();
  expect(await dialog.locator(".gallery-download__size, a[download]").count()).toBeGreaterThan(1);
});

test("the download attribute is Hugo's, not the script's", async ({ page }) => {
  await page.goto(GRID);
  const expected = await page.locator(".gallery-item").first().getAttribute("data-download-name");
  await openLightbox(page);
  await page.locator(".pswp__button--download-button").click();

  const dialog = page.locator("dialog.gallery-download");
  await expect(dialog).toBeVisible();
  const names = await dialog.locator("a[download]").evaluateAll((els) =>
    els.map((e) => (e as HTMLAnchorElement).getAttribute("download")),
  );
  expect(names.length).toBeGreaterThan(0);
  for (const n of names) expect(n).toBe(expected);
});

test("Escape closes the dialog and leaves the viewer open", async ({ page }) => {
  /* The first Escape closes the dialog (the browser does that for a modal
     <dialog>), the second closes the lightbox — which is why the site prevents
     PhotoSwipe's own Escape while the dialog is up. */
  await page.goto(GRID);
  await openLightbox(page);
  await page.locator(".pswp__button--download-button").click();
  await expect(page.locator("dialog.gallery-download")).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(page.locator("dialog.gallery-download")).toBeHidden();
  await expect(page.locator(".pswp--open")).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(page.locator(".pswp--open")).toHaveCount(0);
});

test("an all-rights-reserved photo is gated, and ticking the box releases it", async ({ page }) => {
  const restricted = gallery().find((e) => e.license === "all-rights-reserved" && e.section !== "archive");
  test.skip(!restricted, "no all-rights-reserved photo in the current gallery");

  await page.goto(GRID);
  const item = page.locator(`.gallery-item[data-id="${restricted!.id}"]`);
  await expect(item).toHaveAttribute("data-license", "all-rights-reserved");

  const index = await page.locator(".gallery-item").evaluateAll(
    (els, id) => els.findIndex((e) => (e as HTMLElement).dataset.id === id),
    restricted!.id,
  );
  await openLightbox(page, index);
  await page.locator(".pswp__button--download-button").click();

  const dialog = page.locator("dialog.gallery-download");
  await expect(dialog).toBeVisible();
  const box = dialog.locator('input[type="checkbox"]').first();
  await expect(box, "no gate on an all-rights-reserved photo").toBeVisible();

  const row = dialog.locator("a[download]").first();
  await expect(row).toHaveAttribute("aria-disabled", "true");
  await box.check();
  await expect(row).toHaveAttribute("aria-disabled", "false");
});

test("the static card on the photo page ships ungated", async ({ browser }) => {
  /* "It only ever adds the gate": with scripts off every link still works and
     the notice still sits above them. */
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("http://localhost:1414/en/gallery/general/");
  const href = await page.locator(".gallery-item[href]").first().getAttribute("href");
  await page.goto("http://localhost:1414" + href);

  const links = page.locator(".photo-download__size");
  expect(await links.count()).toBeGreaterThan(1);
  for (const a of await links.all()) {
    await expect(a).toHaveAttribute("download", /\S/);
    expect(await a.getAttribute("aria-disabled"), "gated without JavaScript").toBeNull();
  }
  expect(await page.locator(".photo-download__gate").count(), "a gate rendered with no JS to remove it").toBe(0);
  await context.close();
});
