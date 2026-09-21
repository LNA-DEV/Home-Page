/* The model pages, in a browser: the page a `public` record renders, and the
   Model row the lightbox draws from the caption spans. */

import { test, expect, openLightbox } from "../support/fixtures";
import { ALLOW_COMPANION, mockCompanion } from "../support/network";
import { models, gallery, asList } from "../support/site";

test.use({ net: { allow: ALLOW_COMPANION } });

function firstPublic() {
  return (models() as any[]).find(
    (m) =>
      m.visibility === "public" &&
      gallery().some((e) => asList(e.model).includes(m.slug) && e.section !== "archive"),
  );
}

test.beforeEach(async ({ page, probe }) => {
  void probe;
  await mockCompanion(page);
});

test("a public model has a page with a name, a strip and its links", async ({ page }) => {
  const m = firstPublic();
  test.skip(!m, "no public model with current photos");

  await page.goto(`/en/gallery/models/${m.slug}/`);
  await expect(page.locator("h1")).toHaveText(m.name);
  await expect(page.locator(".gallery-item").first()).toBeVisible();

  for (const link of m.links ?? []) {
    await expect(page.locator(`.model-links a[href="${link.url}"]`)).toHaveAttribute("rel", /noopener/);
    await expect(page.locator(`.model-links a[href="${link.url}"]`)).not.toHaveAttribute("rel", /\bme\b/);
  }
});

test("the grid lists the public models", async ({ page }) => {
  const m = firstPublic();
  test.skip(!m, "no public model with current photos");
  await page.goto("/en/gallery/models/");
  await expect(page.locator(`a[href="/en/gallery/models/${m.slug}/"]`).first()).toBeVisible();
});

test("the lightbox shows a Model row that links to the page", async ({ page }) => {
  const m = firstPublic();
  test.skip(!m, "no public model with current photos");

  const photo = gallery().find((e) => asList(e.model).includes(m.slug) && e.section !== "archive")!;
  await page.goto("/en/gallery/general/");
  const index = await page.locator(".gallery-item").evaluateAll(
    (els, id) => els.findIndex((e) => (e as HTMLElement).dataset.id === id),
    photo.id,
  );
  test.skip(index < 0, "that photo is not on the general grid");

  await openLightbox(page, index);
  await page.locator(".pswp__button--info").click();
  const popup = page.locator(".pswp-info-popup.visible");
  await expect(popup).toBeVisible();
  await expect(popup.locator(`a[href*="/gallery/models/${m.slug}/"]`)).toBeVisible();
});

test("a hidden model's name is on no page", async ({ page }) => {
  const hidden = (models() as any[]).filter((m) => m.visibility === "hidden");
  test.skip(hidden.length === 0, "no record is hidden today");

  for (const m of hidden) {
    const res = await page.request.get(`/en/gallery/models/${m.slug}/`);
    expect(res.status(), `${m.slug} still has a page`).toBe(404);
  }
  await page.goto("/en/gallery/models/");
  const body = (await page.locator("body").textContent()) ?? "";
  for (const m of hidden) {
    if (m.name) expect(body).not.toContain(m.name);
    expect(body).not.toContain(m.slug);
  }
});
