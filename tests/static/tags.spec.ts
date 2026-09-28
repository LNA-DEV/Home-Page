/* L2 — photo tags as a Hugo taxonomy: /<lang>/gallery/tags/<tag>/.
 *
 * docs/concepts/tag-pages.md. The photo content adapter hands every
 * non-archive photo's lowercased tags to the `phototags` taxonomy; Hugo makes a
 * page per tag, and the photo page links each tag through `.GetTerms`. The
 * build's own view of a photo's tags is the per-language manifest
 * (gallery-metadata.json), so that is what the pages are held against.
 *
 * The robots and sitemap side — every tag page noindex, follow and in no
 * sitemap — is in html.spec.ts and feeds.spec.ts, with the post tags. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { LANGS, manifests, sitePath, readSiteFile } from "../support/site";

type Photo = { id: string; slug: string; section: string; tags?: string[] };

const photos = (lang: string): Photo[] => ((manifests() as any)[lang]?.photos ?? []) as Photo[];
const tagDir = (lang: string) => sitePath(lang, "gallery", "tags");

/** Every term page of one language: dir name → its HTML. */
function termPages(lang: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const e of fs.readdirSync(tagDir(lang), { withFileTypes: true })) {
    if (!e.isDirectory()) continue;
    const f = path.join(tagDir(lang), e.name, "index.html");
    if (fs.existsSync(f)) out.set(e.name, fs.readFileSync(f, "utf8"));
  }
  return out;
}

/** The tag a term page is for, as its H1 prints it ("#fall colors" → "fall colors"). */
const headingTag = (html: string) =>
  (html.match(/<h1>#([^<]*)<\/h1>/)?.[1] ?? "").replace(/&amp;/g, "&").replace(/&#39;/g, "'");

/** The photo-tags block of a photo page: every <li>, and how many are links. */
function tagList(html: string): { items: number; links: number } {
  const block = html.match(/<div class="photo-tags">[\s\S]*?<\/ul>/)?.[0] ?? "";
  return {
    items: (block.match(/<li>/g) ?? []).length,
    links: (block.match(/<a [^>]*rel="tag"/g) ?? []).length,
  };
}

test.describe("photo tags", () => {
  test("one page per tag of a non-archive photo, and no other", () => {
    /* Also catches the adapter and Hugo disagreeing about a term — two tags
       Hugo merges, or one it drops, show up as a difference here. */
    for (const lang of LANGS) {
      const want = new Set(
        photos(lang).filter((p) => p.section !== "archive").flatMap((p) => p.tags ?? []),
      );
      expect(want.size, `${lang}: no tags in the manifest`).toBeGreaterThan(0);
      const have = new Set([...termPages(lang).values()].map(headingTag));
      const missing = [...want].filter((t) => !have.has(t));
      const extra = [...have].filter((t) => !want.has(t));
      expect(missing.slice(0, 20), `${lang}: ${missing.length} tag(s) without a page`).toEqual([]);
      expect(extra.slice(0, 20), `${lang}: ${extra.length} page(s) for no tag`).toEqual([]);
    }
  });

  test("every tag page lists at least one photo, none of them archived", () => {
    const bad: string[] = [];
    for (const lang of LANGS) {
      const section = new Map(photos(lang).map((p) => [`/${lang}/gallery/photo/${p.slug}/`, p.section]));
      for (const [dir, html] of termPages(lang)) {
        const grid = html.match(/<section class="photo-related photo-tag-grid">[\s\S]*?<\/section>/)?.[0] ?? "";
        const hrefs = [...grid.matchAll(/<a href="([^"]+)"/g)].map((m) => m[1]);
        if (!hrefs.length) bad.push(`${lang}/${dir}: no photos`);
        for (const h of hrefs) {
          const s = section.get(decodeURIComponent(h));
          if (s === undefined) bad.push(`${lang}/${dir}: ${h} is not a photo page`);
          else if (s === "archive") bad.push(`${lang}/${dir}: ${h} is archived`);
        }
      }
    }
    expect(bad.slice(0, 20), `${bad.length} problem(s)\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("a photo page links every tag, and an archive photo none", () => {
    /* The photo page matches a tag to its term through the term's .Title,
       lowered — this is the test that the round trip holds for every tag. */
    const bad: string[] = [];
    for (const lang of LANGS) {
      for (const p of photos(lang)) {
        if (!p.tags?.length) continue;
        const f = sitePath(lang, "gallery", "photo", p.slug, "index.html");
        if (!fs.existsSync(f)) continue;
        const { items, links } = tagList(fs.readFileSync(f, "utf8"));
        const want = p.section === "archive" ? 0 : items;
        if (links !== want) bad.push(`${lang}/${p.slug}: ${links} of ${items} tags linked, want ${want}`);
      }
    }
    expect(bad.slice(0, 20), `${bad.length} photo page(s)\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("photo tags have no feeds", () => {
    /* content/phototags/_index.<lang>.md cascades `outputs: [HTML]`, one file
       per language — a missing one brings ~600 feeds back in that language. */
    const bad: string[] = [];
    for (const lang of LANGS) {
      if (fs.existsSync(path.join(tagDir(lang), "index.xml"))) bad.push(`${lang}/gallery/tags/index.xml`);
      for (const dir of termPages(lang).keys()) {
        if (fs.existsSync(path.join(tagDir(lang), dir, "index.xml"))) bad.push(`${lang}/gallery/tags/${dir}/index.xml`);
      }
    }
    expect(bad.slice(0, 10), `${bad.length} feed(s)`).toEqual([]);
  });

  test("the index lists every tag page", () => {
    for (const lang of LANGS) {
      const index = readSiteFile(path.join(lang, "gallery", "tags", "index.html"));
      const linked = new Set(
        [...index.matchAll(/<a href="([^"]+)" rel="tag">/g)].map((m) => decodeURIComponent(m[1])),
      );
      const pages = [...termPages(lang).keys()].map((d) => `/${lang}/gallery/tags/${d}/`);
      const missing = pages.filter((u) => !linked.has(decodeURIComponent(u)));
      expect(missing.slice(0, 20), `${lang}: ${missing.length} tag page(s) not on the index`).toEqual([]);
    }
  });
});
