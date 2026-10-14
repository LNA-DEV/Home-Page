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

/* The two nginx maps, as nginx reads them: a quoted key (compared ignoring
   case) and a value. */
function nginxMap(name: string, value: RegExp): Map<string, string> {
  const map = new Map<string, string>();
  const file = path.join(SITE_DIR, "_nginx", name);
  if (!fs.existsSync(file)) return map;
  const re = new RegExp(`^"((?:[^"\\\\]|\\\\.)*)" (${value.source});$`);
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const l = re.exec(line);
    if (l) map.set(l[1].replace(/\\(["\\])/g, "$1").toLowerCase(), l[2]);
  }
  return map;
}
const stemMap = memoMap(() => nginxMap("gallery-image-redirects.map", /[a-z0-9-]+/));
const variantMap = memoMap(() => nginxMap("image-variant-redirects.map", /\/\S+/));
function memoMap(fn: () => Map<string, string>): () => Map<string, string> {
  let m: Map<string, string> | undefined;
  return () => (m ??= fn());
}

/* A retired image URL resolves when an nginx redirect map sends it to a file
   that is served — Hugo cannot redirect an image, so nginx does it. Same split
   as the server (../Web-Services/homepage/nginx.conf), same order:
     1. `<dir>/<anything>_hu_<hash>.<ext>` — an old Hugo cache-key name — goes
        through the variant map, keyed by directory and hash
        (docs/concepts/stable-image-urls.md §5);
     2. `/images/gallery/(<spec>/)?<stem>.<ext>` — a renamed photo — through the
        stem map, which carries the spec directory over
        (docs/concepts/gallery-metadata-yaml-only.md §5).
   A `_hu_` name the variant map does not know is a 404 on the server, so it does
   not resolve here either: the stem map never sees it. */
function redirectedImage(u: string, served: Set<string>): boolean {
  const hu = /^(\/(?:[^/]+\/)*)[^/]+?(_hu_[0-9a-f]+)\.[A-Za-z0-9]+$/.exec(u);
  if (hu) {
    const target = variantMap().get((hu[1] + hu[2]).toLowerCase());
    return Boolean(target) && served.has(decodeURIComponent(target!));
  }
  const m = /^\/images\/gallery\/([a-z0-9-]+\/)?([^/]+?)\.([A-Za-z]+)$/.exec(u);
  if (!m) return false;
  const target = stemMap().get(m[2].toLowerCase());
  return Boolean(target) && served.has(`/images/gallery/${m[1] ?? ""}${target}.${m[3].toLowerCase()}`);
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
