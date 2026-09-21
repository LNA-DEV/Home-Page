/* The page fixture every L3 scenario uses.
 *
 * It installs the network policy before the first navigation, grants clipboard
 * permissions where the engine has them, and collects console errors and failed
 * requests so the "no console error" scenario is a property of every page visit
 * rather than a separate crawl. */

import { test as base, expect } from "@playwright/test";
import { installNetworkPolicy, type NetworkLog } from "./network";

export type Probe = {
  network: NetworkLog;
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
};

/* The allow-list is wrapped in an object rather than passed as a bare array:
   Playwright's option fixtures use a [value, options] tuple, and an array value
   is ambiguous with it — a bare RegExp[] arrives as its first element. */
export const test = base.extend<{ probe: Probe; net: { allow: RegExp[] } }>({
  /* Overridden per file with test.use({ net: { allow: [...] } }). */
  net: [{ allow: [] as RegExp[] }, { option: true }],

  probe: async ({ page, net, browserName, context }, use) => {
    const allow = net?.allow ?? [];
    if (browserName === "chromium") {
      /* Playwright can only grant these in Chromium; the copy-link scenario
         asserts the button state everywhere and reads the clipboard only here. */
      await context.grantPermissions(["clipboard-read", "clipboard-write"]).catch(() => {});
    }

    const probe: Probe = {
      network: await installNetworkPolicy(page, { allow }),
      consoleErrors: [],
      pageErrors: [],
      failedRequests: [],
    };

    page.on("console", (msg) => {
      if (msg.type() === "error") probe.consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => probe.pageErrors.push(String(err)));
    page.on("requestfailed", (req) => {
      /* An aborted third-party request is the policy working, not a failure. */
      const url = req.url();
      if (!probe.network.blocked.includes(url)) probe.failedRequests.push(url);
    });

    await use(probe);
  },
});

export { expect };

/** The first gallery photo's UUID on a built grid page. */
export async function firstPhotoId(page: import("@playwright/test").Page): Promise<string> {
  const id = await page.locator(".gallery-item[data-id]").first().getAttribute("data-id");
  expect(id, "no gallery item on this page").toBeTruthy();
  return id!;
}

/** Open the lightbox on the nth gallery item and wait until it is ready for input.
 *
 * PhotoSwipe does most of its wiring — the keyboard listener, the heavy image,
 * the close path — in `openingAnimationEnd`, not in `open`. Both `.pswp--open`
 * and `.pswp--ui-visible` appear well before that, so a test that acts as soon
 * as the viewer looks open acts on a viewer that is still opening, and the
 * click or key press is swallowed.
 *
 * The honest signal is the moment `appendHeavy()` swaps the placeholder for the
 * real image, which is the first thing that same handler does.
 */
export async function openLightbox(page: import("@playwright/test").Page, nth = 0) {
  await page.locator(".gallery-item").nth(nth).click();
  await expect(page.locator(".pswp--open")).toBeVisible();
  await expect(page.locator(".pswp--ui-visible")).toBeVisible();
  await expect(page.locator(".pswp__img:not(.pswp__img--placeholder)").first()).toBeAttached();
  return page.locator(".pswp");
}

/** The same wait, for a viewer that was opened by a deep link rather than a click. */
export async function awaitLightboxReady(page: import("@playwright/test").Page) {
  await expect(page.locator(".pswp--open")).toBeVisible();
  await expect(page.locator(".pswp--ui-visible")).toBeVisible();
  await expect(page.locator(".pswp__img:not(.pswp__img--placeholder)").first()).toBeAttached();
}
