/* The newsletter form posts to listmonk's public endpoint from JavaScript.
   Nothing here may reach the real service, and the two outcomes the form draws
   — done, and an inline error — both have to render. */

import { test, expect } from "../support/fixtures";
import { ALLOW_LISTMONK, mockListmonk } from "../support/network";

test.use({ net: { allow: ALLOW_LISTMONK } });

const PAGE = "/en/";

/* On the home page the form lives inside a <dialog>, opened from the header. */
async function openForm(page: import("@playwright/test").Page) {
  await page.goto(PAGE);
  await page.locator("[data-newsletter-open]").first().click();
  await expect(page.locator("dialog.newsletter-modal")).toBeVisible();
  return page.locator("dialog.newsletter-modal .newsletter-form").first();
}

async function fillAndSubmit(page: import("@playwright/test").Page) {
  const form = page.locator("dialog.newsletter-modal .newsletter-form").first();
  await form.locator('input[name="email"]').fill("someone@example.invalid");
  await form.locator(".newsletter-submit").click();
}

test("a successful subscription renders the done state", async ({ page, probe }) => {
  const listmonk = await mockListmonk(page);
  await openForm(page);

  await fillAndSubmit(page);

  await expect(page.locator("dialog.newsletter-modal .newsletter-done").first()).toBeVisible();
  expect(listmonk.posted.length, "the form did not post").toBe(1);
  expect(listmonk.posted[0]).toContain("example.invalid");

  /* And nothing else left the machine. */
  const stray = probe.network.blocked.filter((u) => !/muninn\.lna-dev\.net/.test(u));
  expect(stray, `blocked, but should not even have been attempted:\n${stray.join("\n")}`).toEqual([]);
});

test("a failing subscription renders the inline error", async ({ page, probe }) => {
  void probe;
  await mockListmonk(page, { fail: true });
  await openForm(page);
  await fillAndSubmit(page);

  await expect(page.locator("dialog.newsletter-modal .newsletter-status").first()).toBeVisible();
  await expect(page.locator("dialog.newsletter-modal .newsletter-done").first()).toBeHidden();
});

test("the form works without JavaScript too", async ({ browser }) => {
  /* It is a real <form method=post action=…>; the script only enhances it. */
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("http://localhost:1414/en/");
  const form = page.locator(".newsletter-form").first();
  await expect(form).toHaveAttribute("method", /post/i);
  await expect(form).toHaveAttribute("action", /listmonk\.lna-dev\.net/);
  await context.close();
});
