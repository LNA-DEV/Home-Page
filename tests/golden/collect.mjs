/* The published URL space of a build: every <loc> in the sitemaps, every item
 * <link> in every feed, and every published original under /images/gallery/,
 * path only.
 *
 * The originals are the one image URL meant to stay put — a variant's `_hu_<hash>`
 * changes on every re-export by design — and since the build names them after
 * the photo's English slug, a reworded title moves them. Listing them here makes
 * that a conscious `npm run golden:update`, and urls.spec.ts accepts a retired
 * one only when the nginx redirect map sends it somewhere live
 * (docs/concepts/gallery-metadata-yaml-only.md §5).
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

  const gallery = path.join(siteDir, "images", "gallery");
  if (fs.existsSync(gallery)) {
    for (const f of fs.readdirSync(gallery)) {
      if (!/_hu_[0-9a-f]+\./.test(f)) out.add(`/images/gallery/${f}`);
    }
  }
  return [...out].sort();
}
