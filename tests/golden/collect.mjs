/* The published URL space of a build: every <loc> in the sitemaps and every item
 * <link> in every feed, path only.
 *
 * Shared by the golden-list test and by `npm run golden:update`, so the two can
 * never disagree about what counts as published. */

import fs from "node:fs";
import path from "node:path";

export function collectPublishedPaths(siteDir, siteBase) {
  const out = new Set();
  const base = siteBase.replace(/\/$/, "");

  const add = (url) => {
    const u = url.trim();
    if (!u.startsWith(base)) return;
    let p = decodeURIComponent(new URL(u).pathname);
    if (!p.endsWith("/") && !path.basename(p).includes(".")) p += "/";
    out.add(p);
  };

  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (e.name === "images" || e.name === "packages") continue;
        walk(full);
      } else if (e.name === "sitemap.xml" || e.name === "index.xml") {
        const xml = fs.readFileSync(full, "utf8");
        for (const m of xml.matchAll(/<loc>([^<]+)<\/loc>/g)) add(m[1]);
        for (const m of xml.matchAll(/<link>([^<]+)<\/link>/g)) add(m[1]);
      }
    }
  };
  walk(siteDir);
  return [...out].sort();
}
