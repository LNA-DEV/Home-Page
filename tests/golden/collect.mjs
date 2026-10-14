/* The published URL space of a build: every <loc> in the sitemaps, every item
 * <link> in every feed, every published gallery file under /images/gallery/ —
 * the originals and every variant — and every game page (noindex, so in no
 * sitemap), path only.
 *
 * Gallery files are named after the photo's English slug, so a reworded title
 * moves them, and a variant sits under the same name one spec directory down
 * (`fit-600x600/<slug>.jpg`, layouts/partials/image-variant.html). That name
 * belongs to the site, not to Hugo: it no longer moves with a Hugo release or
 * an `imaging:` edit (docs/concepts/stable-image-urls.md). Listing every one of
 * them here makes any move a conscious `npm run golden:update`, and urls.spec.ts
 * accepts a retired one only when an nginx redirect map sends it somewhere live.
 * Variants elsewhere (posts, covers) stay out: their set follows each source's
 * width, and replacing a post image may legitimately change it.
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
    for (const e of fs.readdirSync(gallery, { withFileTypes: true })) {
      if (e.isFile()) out.add(`/images/gallery/${e.name}`);
      else if (e.isDirectory()) {
        for (const f of fs.readdirSync(path.join(gallery, e.name))) out.add(`/images/gallery/${e.name}/${f}`);
      }
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
