/* The published URL space of a build: every <loc> in the sitemaps, every item
 * <link> in every feed, every published original under /images/gallery/, and
 * every game page (noindex, so in no sitemap), path only.
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

  /* The game pages are noindex and so out of the sitemap on purpose — but their
     URLs are meant to stay put all the same; that is what the frozen slug is for
     (docs/concepts/gaming-game-pages.md §2). Every real page under
     /<lang>/gaming/<slug>/ counts. An alias (a renamed slug) is a refresh stub,
     not a page, and is covered by "still resolves" instead. */
  for (const lang of fs.readdirSync(siteDir)) {
    const dir = path.join(siteDir, lang, "gaming");
    if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) continue;
    for (const slug of fs.readdirSync(dir)) {
      const file = path.join(dir, slug, "index.html");
      if (!fs.existsSync(file)) continue;
      if (/http-equiv="?refresh/i.test(fs.readFileSync(file, "utf8"))) continue;
      out.add(`/${lang}/gaming/${slug}/`);
    }
  }
  return [...out].sort();
}
