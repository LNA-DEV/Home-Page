/* L2 — the other languages on every home: docs/concepts/multilingual-home.md.
 *
 * Three things are held here against the content files and against each other:
 *
 *   §3  the "other languages" block on each home and on /posts/ — the newest
 *       posts that exist ONLY in another language, worked out again from
 *       content/posts/ independently of the template;
 *   §4  the "this page is also in …" bars — exactly one per translation, on
 *       every page, pointing where the hreflang alternate points;
 *   §5  the root page — noindex, canonical /en/, /en/ without JavaScript — and
 *       the /<lang>/page/1/ redirects it must not have swallowed;
 *   §6a the language switcher — the translation where there is one, else the
 *       other language's home.
 *
 * What the browser's language does to all of that (order, visibility, no layout
 * shift, no overlay) is in tests/e2e/multilingual-home.spec.ts. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { parse as parseYaml } from "yaml";
import {
  LANGS,
  REPO,
  SITE_BASE,
  eachHtml,
  frontMatter,
  jsonLdBlocks,
  readSiteFile,
  sitePath,
  urlOf,
  type Lang,
} from "../support/site";

/* ----------------------------------------------------------- the content */

type Post = { lang: Lang; bundle: string; title: string; date: Date; hidden: boolean };

/** Every post that a production build publishes, read from content/posts/ —
 *  not from the build — so the block is checked against the source. */
function contentPosts(): Post[] {
  const out: Post[] = [];
  const now = new Date();
  const walk = (dir: string) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) {
        walk(full);
        continue;
      }
      const m = e.name.match(/^index\.(en|de|sv)\.md$/);
      if (!m) continue;
      const fm = frontMatter(path.relative(REPO, full));
      const date = new Date(fm.date);
      if (fm.draft === true || date > now) continue;
      out.push({
        lang: m[1] as Lang,
        bundle: path.relative(REPO, dir),
        title: String(fm.title).trim(),
        date,
        hidden: String(fm.hiddenInHomeList) === "true",
      });
    }
  };
  walk(path.join(REPO, "content", "posts"));
  return out;
}

const posts = contentPosts();

/** The posts of `other` that have no translation in `lang`, newest first. */
function onlyIn(other: Lang, lang: Lang): Post[] {
  const bundlesIn = new Set(posts.filter((p) => p.lang === lang).map((p) => p.bundle));
  return posts
    .filter((p) => p.lang === other && !bundlesIn.has(p.bundle) && !p.hidden)
    .sort((a, b) => b.date.getTime() - a.date.getTime());
}

/* ------------------------------------------------------------ the markup */

const unescape = (s: string) =>
  s.replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">");

const blockOf = (html: string) => html.match(/<section class="lang-more"[\s\S]*?<\/section>/)?.[0] ?? null;

type Group = { lang: string; all: { href: string; text: string } | null; entries: { href: string; hreflang: string; lang: string; title: string; date: string }[] };

function groupsOf(block: string): Group[] {
  return block
    .split(/<div class="lang-more-group" /)
    .slice(1)
    .map((chunk) => {
      const lang = chunk.match(/^data-lang="([^"]+)"/)?.[1] ?? "";
      const all = chunk.match(/<a class="lang-more-all" href="([^"]+)"[^>]*>([^<]*)<\/a>/);
      const entries = [...chunk.matchAll(/<a class="lang-more-title" href="([^"]+)" hreflang="([^"]+)" lang="([^"]+)">([^<]*)<\/a>\s*<div class="lang-more-meta">(?:<time datetime="([^"]+)")?/g)].map(
        (m) => ({ href: m[1], hreflang: m[2], lang: m[3], title: unescape(m[4]), date: m[5] ?? "" }),
      );
      return { lang, all: all ? { href: all[1], text: unescape(all[2]) } : null, entries };
    });
}

/** The built file behind an absolute site URL. */
function fileOf(url: string): string {
  expect(url.startsWith(SITE_BASE + "/"), `${url} is not on this site`).toBe(true);
  return path.join(decodeURIComponent(url.slice(SITE_BASE.length + 1)), "index.html");
}

const htmlLang = (html: string) => html.match(/<html[^>]*\blang="([^"]+)"/)?.[1] ?? "";

/** hreflang → href of a page's <link rel="alternate">s, x-default left out. */
function alternates(html: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const m of html.matchAll(/<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"/g)) {
    if (m[1] !== "x-default") out.set(m[1], m[2]);
  }
  return out;
}

/** Every entry of a paginated post list, across all its pages. */
function listCount(lang: string): number {
  let n = 0;
  for (let page = 1; ; page++) {
    const rel = page === 1 ? path.join(lang, "posts", "index.html") : path.join(lang, "posts", "page", String(page), "index.html");
    if (!fs.existsSync(sitePath(rel))) break;
    const html = readSiteFile(rel);
    if (/http-equiv="refresh"/.test(html)) break;
    n += (html.match(/<article class="post-entry/g) ?? []).length;
  }
  return n;
}

/* ------------------------------------------------------------- the block */

test.describe("the other languages' posts (§3)", () => {
  for (const lang of LANGS) {
    for (const where of ["home", "posts"] as const) {
      const rel = where === "home" ? path.join(lang, "index.html") : path.join(lang, "posts", "index.html");

      test(`${lang} ${where}: one group per other language, the newest posts that exist only there`, () => {
        const block = blockOf(readSiteFile(rel));
        expect(block, `${rel} has no "other languages" block`).not.toBeNull();
        const groups = groupsOf(block!);

        const expected = LANGS.filter((o) => o !== lang && onlyIn(o, lang).length > 0);
        expect(groups.map((g) => g.lang), `${rel}: the groups`).toEqual(expected);

        for (const g of groups) {
          const want = onlyIn(g.lang as Lang, lang).slice(0, 3).map((p) => p.title);
          expect(g.entries.map((e) => e.title), `${rel}: the ${g.lang} group`).toEqual(want);
          expect(g.lang).not.toBe(lang);
        }
      });

      test(`${lang} ${where}: every entry is a post in its own language, with no translation in ${lang}`, () => {
        const groups = groupsOf(blockOf(readSiteFile(rel))!);
        for (const g of groups) {
          for (const e of g.entries) {
            expect(e.hreflang, e.href).toBe(g.lang);
            expect(e.lang, e.href).toBe(g.lang);
            expect(e.href, e.href).toContain(`/${g.lang}/posts/`);
            const target = readSiteFile(fileOf(e.href));
            expect(htmlLang(target), `${e.href} is not a ${g.lang} page`).toBe(g.lang);
            expect(alternates(target).has(lang), `${e.href} has a ${lang} translation, so it does not belong in the block`).toBe(false);
          }
        }
      });

      test(`${lang} ${where}: each count link names exactly the posts on the list it opens`, () => {
        const groups = groupsOf(blockOf(readSiteFile(rel))!);
        for (const g of groups) {
          expect(g.all, `${rel}: the ${g.lang} group has no count link`).not.toBeNull();
          expect(g.all!.href).toBe(`${SITE_BASE}/${g.lang}/posts/`);
          const n = listCount(g.lang);
          expect(n, `${g.lang}/posts/ lists no posts`).toBeGreaterThan(0);
          expect(g.all!.text, `${rel}: the ${g.lang} count`).toMatch(new RegExp(`(^|\\D)${n}(\\D|$)`));
        }
      });

      test(`${lang} ${where}: the block's links are plain, followed links`, () => {
        expect(blockOf(readSiteFile(rel))!).not.toMatch(/nofollow/);
      });
    }

    test(`${lang}: only the first page of each list carries the block`, () => {
      for (const rel of [path.join(lang, "page", "2", "index.html"), path.join(lang, "posts", "page", "2", "index.html")]) {
        if (!fs.existsSync(sitePath(rel))) continue;
        expect(blockOf(readSiteFile(rel)), rel).toBeNull();
      }
    });

    test(`${lang}: the block stays out of the home's feed and structured data`, () => {
      const html = readSiteFile(path.join(lang, "index.html"));
      const hrefs = groupsOf(blockOf(html)!).flatMap((g) => g.entries.map((e) => e.href));
      const ld = jsonLdBlocks(html).join("\n");
      const rss = readSiteFile(path.join(lang, "index.xml"));
      for (const href of hrefs) {
        expect(ld, `${lang} home JSON-LD names ${href}`).not.toContain(href);
        expect(rss, `${lang} feed carries ${href}`).not.toContain(href);
      }
    });

    test(`${lang}: "All posts" on the home is in the home's language`, () => {
      const html = readSiteFile(path.join(lang, "index.html"));
      const link = html.match(/<a class="next" href="[^"]*\/posts\/">\s*([^<]*?)\s*<\/a>/)?.[1];
      test.skip(link === undefined, `the ${lang} home has a single page of posts and no "All posts" link`);
      const want = (parseYaml(fs.readFileSync(path.join(REPO, "i18n", `${lang}.yaml`), "utf8")) as any[]).find((e) => e?.id === "all_posts")?.translation;
      expect(want, `i18n/${lang}.yaml has no all_posts`).toBeTruthy();
      expect(unescape(link!)).toBe(`${want} »`);
    });
  }
});

/* --------------------------------------------- the bars and the switcher */

test.describe("the hint bars and the language switcher (§4, §6a)", () => {
  test("every page has one bar per translation, linking where its hreflang alternate does", () => {
    const bad: string[] = [];
    let pages = 0;
    for (const { file, html } of eachHtml()) {
      if (/http-equiv="refresh"/.test(html) || !html.includes('class="header"')) continue;
      pages++;
      const own = htmlLang(html);
      const alt = alternates(html);
      alt.delete(own);
      const bars = new Map<string, string>();
      for (const m of html.matchAll(/<div class="lang-hint" data-lang="([^"]+)" lang="([^"]+)">\s*<span[^>]*>[^<]*<\/span>\s*<a class="lang-hint__link" href="([^"]+)" hreflang="([^"]+)"/g)) {
        if (m[1] !== m[2] || m[1] !== m[4]) bad.push(`${urlOf(file)}: a ${m[1]} bar is marked lang=${m[2]} hreflang=${m[4]}`);
        bars.set(m[1], m[3]);
      }
      if (bars.has(own)) bad.push(`${urlOf(file)}: a bar for the page's own language`);
      for (const [l, href] of alt) {
        if (bars.get(l) !== href) bad.push(`${urlOf(file)}: ${l} bar → ${bars.get(l) ?? "(none)"}, alternate → ${href}`);
      }
      for (const l of bars.keys()) if (!alt.has(l)) bad.push(`${urlOf(file)}: a ${l} bar but no ${l} alternate`);
    }
    expect(pages).toBeGreaterThan(100);
    expect(bad.slice(0, 20), `${bad.length} page(s) wrong`).toEqual([]);
  });

  test("every bar names its translation and has a labelled close button", () => {
    const html = readSiteFile(path.join("en", "posts", "media", "fediverse", "index.html"));
    const bar = html.match(/<div class="lang-hint" data-lang="de"[\s\S]*?<\/button>/)?.[0] ?? "";
    expect(bar, "the Fediverse post has no German bar").not.toBe("");
    expect(bar).toContain("<cite>Was ist das Fediverse?</cite>");
    expect(bar).toMatch(/<button type="button" class="lang-hint__close" aria-label="[^"]+"/);
    const home = readSiteFile(path.join("en", "index.html"));
    expect(home.match(/<div class="lang-hint" data-lang="de"[\s\S]*?<\/a>/)?.[0] ?? "", "a home bar names no title").not.toContain("<cite>");
  });

  test("the switcher goes to the translation, else to that language's home", () => {
    const bad: string[] = [];
    let links = 0;
    let toTranslation = 0;
    for (const { file, html } of eachHtml()) {
      const ul = html.match(/<ul class="lang-switch">([\s\S]*?)<\/ul>/)?.[1];
      if (!ul) continue;
      const alt = alternates(html);
      for (const m of ul.matchAll(/<a href="([^"]+)" hreflang="([^"]+)" data-lang-choice="([^"]+)"/g)) {
        const [, href, l, choice] = m;
        links++;
        if (alt.has(l)) toTranslation++;
        const want = alt.get(l) ?? `${SITE_BASE}/${l}/`;
        if (href !== want || choice !== l) bad.push(`${urlOf(file)}: ${l} → ${href}, expected ${want}`);
      }
    }
    expect(links, "no switcher link was checked").toBeGreaterThan(100);
    expect(toTranslation, "no switcher link leads to a translation").toBeGreaterThan(100);
    expect(bad.slice(0, 20), `${bad.length} link(s) wrong`).toEqual([]);
  });
});

/* -------------------------------------------------------- the root page */

test.describe("the root page (§5)", () => {
  test("/ is noindex, canonical /en/, and /en/ without JavaScript", () => {
    const html = readSiteFile("index.html");
    expect(html).toMatch(/<meta name="robots" content="noindex">/);
    expect(html).toContain(`<link rel="canonical" href="${SITE_BASE}/en/">`);
    expect(html).toContain(`<noscript><meta http-equiv="refresh" content="0; url=${SITE_BASE}/en/"></noscript>`);
    for (const l of LANGS) expect(html, `no link to the ${l} home`).toContain(`href="${SITE_BASE}/${l}/" hreflang="${l}"`);
    expect(html).toContain('location.replace("/"+l+"/"+location.search+location.hash)');
  });

  test("every /<lang>/page/1/ still redirects to its own home", () => {
    for (const l of LANGS) {
      const rel = path.join(l, "page", "1", "index.html");
      expect(fs.existsSync(sitePath(rel)), `${rel} is not built`).toBe(true);
      const html = readSiteFile(rel);
      expect(html, rel).toContain(`<meta http-equiv="refresh" content="0; url=${SITE_BASE}/${l}/">`);
      expect(html, rel).not.toContain("location.replace");
    }
  });
});
