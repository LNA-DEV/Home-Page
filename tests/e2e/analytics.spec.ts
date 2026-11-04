/* The pageview waits for a sign of life (extend_head.html): input the browser
   raised itself, or leaving the page. A crawler that renders the page and kills
   it once the network is idle shows neither and is never counted.

   The network policy answers the tracker with an empty script, so what is
   asserted is what the page hands it: the calls in the stub's queue
   (plausible.q) and the options in plausible.o. That the real tracker (v33)
   honours autoCapturePageviews and transformRequest, and that Chrome's own
   pointermove after an anchor scroll has no movement, was tried by hand against
   the served script. */

import { test, expect } from "../support/fixtures";
import type { Page } from "@playwright/test";

const PAGE = "/en/";

/** The calls the page made to plausible(), in order, as [name, options?]. */
function calls(page: Page) {
  return page.evaluate(() =>
    ((window as any).plausible.q ?? []).map((args: IArguments) => Array.from(args)),
  ) as Promise<[string, Record<string, unknown>?][]>;
}

async function names(page: Page) {
  return (await calls(page)).map((c) => c[0]);
}

test("a page nobody touches is not counted", async ({ page, probe }) => {
  void probe;
  await page.goto(PAGE);
  await page.waitForTimeout(1500);
  expect(await names(page)).toEqual([]);
  expect(await page.evaluate(() => (window as any).plausible.o.autoCapturePageviews)).toBe(false);
});

test("events the page dispatches itself are no sign of life", async ({ page, probe }) => {
  void probe;
  await page.goto(PAGE);
  await page.evaluate(() => {
    for (const type of ["pointermove", "pointerdown", "wheel", "touchstart"])
      window.dispatchEvent(new PointerEvent(type, { movementX: 5, movementY: 5 }));
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
  });
  expect(await names(page)).toEqual([]);
});

test("real input counts the page, once", async ({ page, probe }) => {
  void probe;
  await page.goto(PAGE);
  await page.mouse.move(40, 40, { steps: 5 });
  await page.mouse.move(200, 160, { steps: 5 });
  await page.keyboard.press("Shift");
  expect(await names(page)).toEqual(["pageview"]);
});

/* A tap on a phone; at desktop width, where there is no touchscreen, a click. */
test("a tap counts the page, once @mobile", async ({ page, probe, hasTouch }) => {
  void probe;
  await page.goto(PAGE);
  /* Wherever the tap lands, it must not follow a link off the page. */
  await page.evaluate(() => document.addEventListener("click", (e) => e.preventDefault(), true));
  for (const [x, y] of [[20, 300], [40, 320]]) {
    if (hasTouch) await page.touchscreen.tap(x, y);
    else await page.mouse.click(x, y);
  }
  expect(await names(page)).toEqual(["pageview"]);
});

test("leaving the page counts it", async ({ page, probe }) => {
  void probe;
  await page.goto(PAGE);
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "hidden" });
    document.dispatchEvent(new Event("visibilitychange"));
    window.dispatchEvent(new PageTransitionEvent("pagehide"));
  });
  expect(await names(page)).toEqual(["pageview"]);
});

test("an event before the pageview waits for it", async ({ page, probe }) => {
  void probe;
  await page.goto(PAGE);
  /* What the tracker does with "Image View" when a deep link opens the
     lightbox on load: it asks transformRequest, which holds the event back. */
  const held = await page.evaluate(() =>
    (window as any).plausible.o.transformRequest({
      n: "Image View",
      u: location.href,
      p: { gallery_image_id: "id" },
    }),
  );
  expect(held).toBeNull();
  expect(await names(page)).toEqual([]);

  await page.keyboard.press("Shift");
  const after = await calls(page);
  expect(after.map((c) => c[0])).toEqual(["pageview", "Image View"]);
  expect(after[1][1]).toMatchObject({ props: { gallery_image_id: "id" } });

  /* Counted: later events go straight through. */
  const passed = await page.evaluate(() =>
    (window as any).plausible.o.transformRequest({ n: "Image View", u: location.href }),
  );
  expect(passed).toMatchObject({ n: "Image View" });
});
