/* The site search — including the two branch pages that are in the index only
   because someone put them there by hand. */

import { test, expect } from "../support/fixtures";

test("typing finds a known post", async ({ page, probe }) => {
  void probe;
  await page.goto("/en/search/");
  /* The search is wired to keyup, so the value has to be typed rather than set. */
  await page.locator("#searchInput").pressSequentially("hugo", { delay: 40 });
  await expect(page.locator("#searchResults li").first()).toBeVisible();
  await expect(page.locator("#searchResults")).toContainText(/hugo/i);
});

test("the index holds the branch pages that nothing links to", async ({ page, probe }) => {
  void probe;
  /* /gallery/models/ is reachable from the search and from a photo, and nowhere
     else — so if it fell out of index.json it would be unreachable. */
  const res = await page.request.get("/en/index.json");
  expect(res.ok()).toBe(true);
  const index = await res.json();
  const urls: string[] = (Array.isArray(index) ? index : index.items ?? []).map((e: any) => e.permalink ?? e.uri ?? "");
  expect(urls.some((u) => u.includes("/gallery/models/")), "/gallery/models/ is not in the search index").toBe(true);
  expect(urls.some((u) => u.includes("/travel")), "/travel is not in the search index").toBe(true);
});
