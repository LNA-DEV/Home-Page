/* L2 — the game pages (docs/concepts/gaming-game-pages.md).
 *
 * One page per game at /<lang>/gaming/<slug>/, built from four files with one
 * owner each: data/gaming.yaml (the copies), data/gamePages.yaml (what a person
 * writes), data/gameFacts/ and data/gameAchievements/ (what the scripts fetch).
 * These tests hold the data and the built pages against each other. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import {
  REPO, LANGS, SITE_BASE, gaming, gamePages, shownGameSlugs, sitePath, readSiteFile,
  jsonLdBlocks, xmlFiles, attrValues,
} from "../support/site";

const SLUG_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const ACH_DIR = path.join(REPO, "data", "gameAchievements");
const STATIC = path.join(REPO, "static");
const ICON_DIR = path.join(STATIC, "images", "games", "achievements");

function achievementFile(key: string): any | null {
  const p = path.join(ACH_DIR, `${key}.json`);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : null;
}

function copyKey(c: any): string {
  if (c.platform === "steam" && c.appid) return `steam-${c.appid}`;
  if (c.platform === "gog" && c.appName) return `gog-${c.appName}`;
  return "";
}

function gamePage(lang: string, slug: string): string {
  return readSiteFile(path.join(lang, "gaming", slug, "index.html"));
}

test.describe("the data", () => {
  test("every copy has a well-formed slug", () => {
    const bad = gaming()
      .filter((c) => !SLUG_RE.test(String(c.slug ?? "")))
      .map((c) => `${c.title} (${c.platform}): ${JSON.stringify(c.slug)}`);
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("no two copies on one platform share a slug", () => {
    /* A game is not owned twice on one store, so this is two different games
       merged by accident — the build refuses it, and so does this. */
    const seen = new Map<string, string>();
    const bad: string[] = [];
    for (const c of gaming()) {
      const k = `${c.slug}|${c.platform ?? "other"}`;
      if (seen.has(k)) bad.push(`${c.slug} (${c.platform}): ${seen.get(k)} / ${c.title}`);
      seen.set(k, c.title);
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("per-game fields are not on a copy", () => {
    const bad = gaming()
      .filter((c) => ["rating", "notes", "genres", "tags"].some((f) => f in c))
      .map((c) => `${c.title} (${c.platform}) — move it to data/gamePages.yaml`);
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("every gamePages.yaml record names a game", () => {
    const slugs = new Set(gaming().map((c) => String(c.slug)));
    const bad = gamePages().filter((p) => !slugs.has(String(p.slug))).map((p) => String(p.slug));
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("every achievement file belongs to a copy, and counts agree with the card", () => {
    const byKey = new Map(gaming().map((c) => [copyKey(c), c]));
    const bad: string[] = [];
    for (const f of fs.existsSync(ACH_DIR) ? fs.readdirSync(ACH_DIR) : []) {
      const key = f.replace(/\.json$/, "");
      const copy = byKey.get(key);
      if (!copy) { bad.push(`${f}: no copy in data/gaming.yaml`); continue; }
      const doc = achievementFile(key);
      const total = doc.achievements.length;
      const unlocked = doc.achievements.filter((a: any) => a.achieved).length;
      if (total !== copy.achievementsTotal) bad.push(`${f}: ${total} rows, the card says ${copy.achievementsTotal}`);
      if (unlocked !== copy.achievementsUnlocked) bad.push(`${f}: ${unlocked} unlocked, the card says ${copy.achievementsUnlocked}`);
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("every committed icon is referenced by an achievement", () => {
    /* The syncs delete what no achievement points at; a stray icon is dead
       weight in a repository that commits them. */
    const refs = new Set<string>();
    for (const f of fs.existsSync(ACH_DIR) ? fs.readdirSync(ACH_DIR) : []) {
      for (const a of achievementFile(f.replace(/\.json$/, "")).achievements) if (a.icon) refs.add(a.icon);
    }
    const stray: string[] = [];
    const walk = (dir: string) => {
      for (const e of fs.existsSync(dir) ? fs.readdirSync(dir, { withFileTypes: true }) : []) {
        const full = path.join(dir, e.name);
        if (e.isDirectory()) walk(full);
        else {
          const ref = path.relative(STATIC, full).split(path.sep).join("/");
          if (!refs.has(ref)) stray.push(ref);
        }
      }
    };
    walk(ICON_DIR);
    expect(stray.slice(0, 20), `${stray.length} unreferenced icon(s)`).toEqual([]);
  });
});

test.describe("the pages", () => {
  test("every shown game has a page in all three languages, and its card links to it", () => {
    const bad: string[] = [];
    for (const lang of LANGS) {
      const grid = readSiteFile(path.join(lang, "gaming", "index.html"));
      for (const slug of shownGameSlugs()) {
        if (!fs.existsSync(sitePath(lang, "gaming", slug, "index.html"))) bad.push(`${lang}/${slug}: no page`);
        else if (!grid.includes(`href="/${lang}/gaming/${slug}/"`)) bad.push(`${lang}/${slug}: no card links it`);
      }
    }
    expect(bad.slice(0, 20), `${bad.length} problem(s)\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("the grid lists no game pages as post entries", () => {
    /* The gaming-home branch in list.html renders the body only; PaperMod's list
       would otherwise append every game page underneath the grid. */
    for (const lang of LANGS) {
      expect(readSiteFile(path.join(lang, "gaming", "index.html"))).not.toContain('class="post-entry');
    }
  });

  test("every achievement is a row, and the unlocked ones are marked", () => {
    const bad: string[] = [];
    for (const slug of shownGameSlugs()) {
      const docs = gaming()
        .filter((c) => String(c.slug) === slug)
        .map((c) => achievementFile(copyKey(c)))
        .filter(Boolean);
      const total = docs.reduce((n, d) => n + d.achievements.length, 0);
      const unlocked = docs.reduce((n, d) => n + d.achievements.filter((a: any) => a.achieved).length, 0);
      const html = gamePage("en", slug);
      const rows = (html.match(/<li class="game-achv[" ]/g) ?? []).length;
      const open = (html.match(/data-state="unlocked"/g) ?? []).length;
      if (rows !== total || open !== unlocked) bad.push(`${slug}: ${rows}/${open} rows, data says ${total}/${unlocked}`);
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("noindex, follow on every game page, and none in a sitemap", () => {
    const bad: string[] = [];
    for (const lang of LANGS) {
      for (const slug of shownGameSlugs()) {
        if (!gamePage(lang, slug).includes('<meta name="robots" content="noindex, follow">')) bad.push(`${lang}/${slug}`);
      }
    }
    expect(bad.slice(0, 10), `${bad.length} page(s) without noindex, follow`).toEqual([]);
    const listed = xmlFiles()
      .filter((f) => f.endsWith("sitemap.xml"))
      .flatMap((f) => [...readSiteFile(f).matchAll(/<loc>([^<]*\/gaming\/[^<]+\/)<\/loc>/g)].map((m) => m[1]));
    expect(listed, "game pages are noindex — a sitemap entry would contradict that").toEqual([]);
  });

  test("the three languages of a game are one hreflang cluster", () => {
    const bad: string[] = [];
    for (const slug of shownGameSlugs()) {
      const html = gamePage("de", slug);
      for (const lang of LANGS) {
        if (!html.includes(`hreflang="${lang}" href="${SITE_BASE}/${lang}/gaming/${slug}/"`)) bad.push(`${slug}: no ${lang}`);
      }
    }
    expect(bad.slice(0, 10), bad.slice(0, 10).join("\n")).toEqual([]);
  });

  test("a game page's body loads nothing from another host", () => {
    /* Store and Wikipedia LINKS are fine; a resource off the site (an icon
       hotlinked from Steam's CDN, say) would break the Tor build and tell a
       third party who is reading. The <main> element only: the site-wide head
       (the analytics script on the site's own subdomain) is not this page's. */
    const bad: string[] = [];
    for (const slug of shownGameSlugs()) {
      const html = gamePage("en", slug);
      const main = html.slice(html.indexOf("<main"), html.indexOf("</main>"));
      for (const src of attrValues(main, "src")) {
        if (/^(https?:)?\/\//.test(src) && !src.startsWith(SITE_BASE)) bad.push(`${slug}: ${src}`);
      }
    }
    expect(bad.slice(0, 10), bad.slice(0, 10).join("\n")).toEqual([]);
  });

  test("the JSON-LD is a WebPage about a VideoGame, with no author", () => {
    const bad: string[] = [];
    for (const slug of shownGameSlugs()) {
      const blocks = jsonLdBlocks(gamePage("en", slug)).map((b) => JSON.parse(b));
      const page = blocks.find((b) => b["@type"] === "WebPage");
      if (!page) { bad.push(`${slug}: no WebPage`); continue; }
      if (page.about?.["@type"] !== "VideoGame") bad.push(`${slug}: about is ${JSON.stringify(page.about)}`);
      if ("author" in page || "datePublished" in page) bad.push(`${slug}: claims an author or a date`);
    }
    test.skip(bad.length === shownGameSlugs().length && bad.every((b) => b.endsWith("no WebPage")),
      "JSON-LD is rendered in production builds only");
    expect(bad.slice(0, 10), bad.slice(0, 10).join("\n")).toEqual([]);
  });

  test("no screenshot original is published", () => {
    /* Only processed variants (_hu_) — the original is never referenced, so
       Hugo never writes it. Vacuous until the first screenshot exists. */
    const dir = sitePath("images", "games", "screenshots");
    const originals: string[] = [];
    const walk = (d: string) => {
      for (const e of fs.existsSync(d) ? fs.readdirSync(d, { withFileTypes: true }) : []) {
        const full = path.join(d, e.name);
        if (e.isDirectory()) walk(full);
        else if (!e.name.includes("_hu_")) originals.push(path.relative(dir, full));
      }
    };
    walk(dir);
    expect(originals, originals.join("\n")).toEqual([]);
  });
});
