/* L2 — URL stability.
 *
 * CLAUDE.md states the rule twice — the gallery overhaul "preserves RSS URL
 * stability", a renamed photo keeps its id "because deep links use it" — and
 * nothing could check it. This is the check: a committed list of every URL the
 * site has ever published, and the assertion that each still resolves to a page
 * or to an alias. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { REPO, SITE_DIR, SITE_BASE, servedPaths } from "../support/site";
import { collectPublishedPaths } from "../golden/collect.mjs";

const LIST = path.join(REPO, "tests/golden/published-urls.txt");

function golden(): string[] {
  if (!fs.existsSync(LIST)) return [];
  return fs.readFileSync(LIST, "utf8")
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("#"));
}

test("the golden list exists and is not empty", () => {
  expect(fs.existsSync(LIST), "run `npm run golden:update` once to create it").toBe(true);
  expect(golden().length, "an empty list asserts nothing").toBeGreaterThan(100);
});

/* A retired gallery image URL resolves when the nginx redirect map sends it to a
   file that is served — Hugo cannot redirect an image, so nginx does it from
   /_nginx/gallery-image-redirects.map (docs/concepts/gallery-metadata-yaml-only.md
   §5). Same split as the server: stem, optional variant hash, extension. */
function redirectedImage(u: string, served: Set<string>): boolean {
  const m = /^\/images\/gallery\/(.+?)(_hu_[0-9a-f]+)?\.([A-Za-z]+)$/.exec(u);
  if (!m) return false;
  const file = path.join(SITE_DIR, "_nginx", "gallery-image-redirects.map");
  if (!fs.existsSync(file)) return false;
  const map = new Map<string, string>();
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const l = /^"((?:[^"\\]|\\.)*)" ([a-z0-9-]+);$/.exec(line);
    if (l) map.set(l[1].replace(/\\(["\\])/g, "$1").toLowerCase(), l[2]);
  }
  const target = map.get(m[1].toLowerCase());
  return Boolean(target) && served.has(`/images/gallery/${target}${m[2] ?? ""}.${m[3].toLowerCase()}`);
}

test("every URL ever published still resolves", () => {
  const served = servedPaths();
  const gone = golden().filter(
    (u) => !served.has(u) && !served.has(u + "/") && !served.has(u + "index.html") &&
      !redirectedImage(u, served),
  );
  expect(
    gone.slice(0, 40),
    `${gone.length} URL(s) no longer resolve. Each one needs a redirect — an alias on the page ` +
    `that replaced it, an entry in slugAliases: for a photo (which also redirects its old image ` +
    `files through the nginx map) — in the same commit that retires it. ` +
    `Only then may the line leave tests/golden/published-urls.txt.\n${gone.slice(0, 40).join("\n")}`,
  ).toEqual([]);
});

test("the list covers what this build publishes", () => {
  /* Not a failure in itself — new pages are normal. It fails so that adding a
     page is a conscious `npm run golden:update`, which is what puts the new URL
     under the protection of the test above. */
  const current = collectPublishedPaths(SITE_DIR, SITE_BASE);
  const known = new Set(golden());
  const missing = current.filter((u) => !known.has(u));
  expect(
    missing.slice(0, 40),
    `${missing.length} newly published URL(s) are not in the golden list yet — run \`npm run golden:update\`\n${missing.slice(0, 40).join("\n")}`,
  ).toEqual([]);
});
