/* The newsletter form posts to listmonk's subscription form from JavaScript,
   with the solution to listmonk's ALTCHA proof of work once that is switched on.
   Nothing here may reach the real service, and the two outcomes the form draws
   — done, and an inline error — both have to render. */

import { test, expect } from "../support/fixtures";
import { ALLOW_LISTMONK, ALTCHA_NUMBER, mockListmonk } from "../support/network";

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
  /* ALTCHA is off (the challenge 404s), so there is nothing to send. */
  expect(new URLSearchParams(listmonk.posted[0]).has("altcha")).toBe(false);
  /* The honeypot goes along, empty: listmonk is the one that checks it. */
  expect(new URLSearchParams(listmonk.posted[0]).get("nonce")).toBe("");

  /* And nothing else left the machine. */
  const stray = probe.network.blocked.filter((u) => !/muninn\.lna-dev\.net/.test(u));
  expect(stray, `blocked, but should not even have been attempted:\n${stray.join("\n")}`).toEqual([]);
});

test("with ALTCHA on, the form posts the solved challenge", async ({ page, probe }) => {
  void probe;
  const listmonk = await mockListmonk(page, { captcha: true });
  await openForm(page);

  await fillAndSubmit(page);

  await expect(page.locator("dialog.newsletter-modal .newsletter-done").first()).toBeVisible();
  expect(listmonk.posted.length, "the form did not post").toBe(1);
  const altcha = new URLSearchParams(listmonk.posted[0]).get("altcha");
  expect(altcha, "the post carries no captcha solution").toBeTruthy();
  const solution = JSON.parse(Buffer.from(altcha!, "base64").toString("utf8"));
  expect(solution).toEqual({
    algorithm: listmonk.challenge.algorithm,
    challenge: listmonk.challenge.challenge,
    number: ALTCHA_NUMBER,
    salt: listmonk.challenge.salt,
    signature: listmonk.challenge.signature,
  });
});

test("a failing subscription renders the inline error", async ({ page, probe }) => {
  void probe;
  await mockListmonk(page, { fail: true });
  await openForm(page);
  await fillAndSubmit(page);

  await expect(page.locator("dialog.newsletter-modal .newsletter-status").first()).toBeVisible();
  await expect(page.locator("dialog.newsletter-modal .newsletter-done").first()).toBeHidden();
});

test("the honeypot is out of reach and a filled one reaches listmonk", async ({ page, probe }) => {
  void probe;
  const listmonk = await mockListmonk(page);
  const form = await openForm(page);
  const honeypot = form.locator('input[name="nonce"]');

  /* A text field a bot fills in, which no person sees, tabs into or gets
     autofilled. type="hidden", as listmonk ships it, is what bots skip. */
  await expect(honeypot).toHaveAttribute("type", "text");
  await expect(honeypot).toHaveAttribute("tabindex", "-1");
  await expect(honeypot).toHaveAttribute("autocomplete", "off");
  await expect(honeypot).not.toBeInViewport();

  /* A bot fills every field it finds. The script posts the honeypot as it is,
     listmonk answers 502, and the form shows its error, not the done state. */
  await honeypot.evaluate((el: HTMLInputElement) => (el.value = "https://spam.example"));
  await fillAndSubmit(page);

  await expect(page.locator("dialog.newsletter-modal .newsletter-status").first()).toBeVisible();
  await expect(page.locator("dialog.newsletter-modal .newsletter-done").first()).toBeHidden();
  expect(listmonk.posted.length, "the form did not post").toBe(1);
  expect(new URLSearchParams(listmonk.posted[0]).get("nonce")).toBe("https://spam.example");
});

test("without JavaScript the newsletter is not offered", async ({ browser }) => {
  /* Signing up needs the script (it solves the captcha), so no placement may
     show a form that can only fail: not the header CTA, not a post's footer. */
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("http://localhost:1414/en/");
  await expect(page.locator(".newsletter-cta")).toHaveCount(1);
  await expect(page.locator(".newsletter-cta")).toBeHidden();

  await page.goto("http://localhost:1414/en/posts/");
  const post = await page.locator(".entry-link").first().getAttribute("href");
  await page.goto(post!);
  const placements = page.locator(".newsletter");
  expect(await placements.count(), "the post has no newsletter placement to check").toBeGreaterThan(0);
  for (const placement of await placements.all()) await expect(placement).toBeHidden();
  await context.close();
});
