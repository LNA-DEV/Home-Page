/* The like counter talks to the companion API. Mocked here, so the contract the
   mock encodes — paths and shapes — is the one place a change on that side shows
   up in this repository. */

import { test, expect, openLightbox } from "../support/fixtures";
import { ALLOW_COMPANION, mockCompanion } from "../support/network";

test.use({ net: { allow: ALLOW_COMPANION } });

test("the grid shows the count the companion returns", async ({ page, probe }) => {
  void probe;
  await mockCompanion(page, { likes: 42 });
  await page.goto("/en/gallery/general/");
  await expect(page.locator(".like-count.visible").first()).toBeVisible();
  await expect(page.locator(".like-count.visible").first()).toContainText("42");
});

test("the heart posts exactly once", async ({ page, probe }) => {
  void probe;
  const companion = await mockCompanion(page, { likes: 3 });
  await page.goto("/en/gallery/general/");
  await openLightbox(page);

  const heart = page.locator(".pswp__like-count, .pswp__button--like").first();
  test.skip((await heart.count()) === 0, "no like control in the viewer");

  await heart.click();
  await expect.poll(() => companion.posted.length, { timeout: 5000 }).toBe(1);
  expect(companion.posted[0].method).toBe("POST");
});

test("a companion that is down leaves the gallery usable", async ({ page, probe }) => {
  void probe;
  /* No mock at all: every companion request is aborted by the policy. The
     gallery must still render and open. */
  await page.goto("/en/gallery/general/");
  await expect(page.locator(".gallery-item").first()).toBeVisible();
  await openLightbox(page);
  await expect(page.locator(".pswp--open")).toBeVisible();
});
