/* L2 — properties of the rendered HTML.
 *
 * Everything here reads the built site and nothing else. It is the layer that
 * would have refused the development build that sat in public/ on the day the
 * concept was written: 4,640 pages carrying http://localhost:1313, no opengraph,
 * no JSON-LD, and nothing in the pipeline that could tell. */

import { test, expect } from "@playwright/test";
import path from "node:path";
import {
  SITE_BASE, LANGS,
  htmlFiles, readSiteFile, eachHtml, servedPaths, urlOf, jsonLdBlocks, pageKind,
  hugoConfig, frontMatter, models, sitePath, gallery, dex,
} from "../support/site";
import fs from "node:fs";

const PRODUCTION = !SITE_BASE.includes("localhost");

/* One legitimate localhost sits in the nginx-proxy-manager post body — it is
   what the tutorial tells the reader to type. Allow-listed by path, so a
   localhost anywhere else is still a failure. */
const LOCALHOST_ALLOWED = /\/posts\/home-server\/nginx-proxy-manager\//;

/** Attribute values arrive HTML-escaped: Hugo writes `+` as `&#43;` and `&` as
 *  `&amp;` inside a URL. A link checker that skips this reports every game cover
 *  with a plus sign in its title as broken. */
function decodeEntities(s: string): string {
  return s
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

test.describe("no template leakage", () => {
  test("no unrendered Go template output anywhere", () => {
    const tokens = ["ZgotmplZ", "<no value>", "%!(", "map[interface"];
    const hits: string[] = [];
    for (const { file, html } of eachHtml()) {
      for (const t of tokens) if (html.includes(t)) hits.push(`${file}: ${t}`);
    }
    expect(hits.slice(0, 20), `${hits.length} page(s) leak template output\n${hits.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("no development base URL", () => {
    const hits: string[] = [];
    for (const { file, html } of eachHtml()) {
      if (html.includes("localhost:1313")) hits.push(file);
    }
    expect(hits.slice(0, 20), `${hits.length} page(s) were built by \`hugo server\`, which writes to public/ by default\n${hits.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("a production build mentions no localhost at all", () => {
    test.skip(!PRODUCTION, "only meaningful when SITE_BASE is the production URL");
    const hits: string[] = [];
    for (const { file, html } of eachHtml()) {
      if (LOCALHOST_ALLOWED.test("/" + file)) continue;
      if (/localhost/i.test(html)) hits.push(file);
    }
    expect(hits.slice(0, 20), `${hits.length} page(s)\n${hits.slice(0, 20).join("\n")}`).toEqual([]);
  });
});

test.describe("images", () => {
  test("every img has an alt attribute", () => {
    const hits: string[] = [];
    for (const { file, html } of eachHtml()) {
      for (const m of html.matchAll(/<img\b[^>]*>/gi)) {
        if (!/\balt\s*=/.test(m[0])) hits.push(`${file}: ${m[0].slice(0, 120)}`);
      }
    }
    expect(hits.slice(0, 20), `${hits.length} image(s) without alt\n${hits.slice(0, 20).join("\n")}`).toEqual([]);
  });
});

test.describe("internal links", () => {
  test("every internal href and src resolves to something served", () => {
    const served = servedPaths();
    const broken = new Map<string, string>();
    const base = SITE_BASE.replace(/\/$/, "");

    for (const { file, html } of eachHtml()) {
      const pageDir = path.posix.dirname(urlOf(file).replace(/\/$/, "/index.html")) + "/";
      const refs = [...html.matchAll(/\b(?:href|src)\s*=\s*"([^"]*)"/gi)].map((m) => m[1]);
      for (const raw of refs) {
        let u = decodeEntities(raw).trim();
        if (!u || u.startsWith("#") || u.startsWith("//")) continue;
        if (/^(mailto|tel|data|javascript|blob):/i.test(u)) continue;
        if (/^https?:\/\//i.test(u)) {
          if (!u.startsWith(base)) continue; // external: out of scope, by design
          u = u.slice(base.length) || "/";
        }
        if (!u.startsWith("/")) u = path.posix.normalize(pageDir + u);
        u = decodeURIComponent(u.split("#")[0].split("?")[0]);
        if (served.has(u) || served.has(u + "/") || served.has(u + "index.html")) continue;
        if (!broken.has(u)) broken.set(u, file);
      }
    }
    const lines = [...broken].map(([u, f]) => `${u}   (e.g. on ${f})`);
    expect(lines, `${lines.length} broken internal target(s)\n${lines.slice(0, 25).join("\n")}`).toEqual([]);
  });

  test("no relative link survives out of rendered Markdown", () => {
    /* `layouts/_markup/render-link.html` resolves a relative Markdown link
       against the page's own URL at build time, so `../x` and `/en/x` come out
       byte-identical. That is what lets a post body be reused away from its own
       URL — in a feed, in the search index — without the links pointing
       somewhere else.
     *
     * Scoped to `.post-content`, which is the Markdown-rendered region and
     * exactly what the hook governs. Chrome outside it (the RSS social icon's
     * `index.xml`, the search page's `../index.json`, the hand-written static
     * page under /tools/) is template and config, never travels, and is not this
     * hook's business. */
    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      for (const region of html.matchAll(/<div[^>]*class="[^"]*post-content[^"]*"[^>]*>([\s\S]*?)<\/div>\s*<footer/gi)) {
        for (const m of region[1].matchAll(/<a\b[^>]*?\bhref\s*=\s*"([^"]*)"/gi)) {
          const u = decodeEntities(m[1]).trim();
          if (!u || u.startsWith("/") || u.startsWith("#")) continue;
          if (/^[a-z][a-z0-9+.-]*:/i.test(u)) continue; // any scheme
          bad.push(`${file}: ${u}`);
        }
      }
    }
    expect(bad.slice(0, 20), `${bad.length} relative link(s) in rendered Markdown — the render hook should have resolved these\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("every gallery deep-link fragment matches a data-id on its target", () => {
    const cache = new Map<string, Set<string>>();
    const idsOn = (urlPath: string): Set<string> => {
      if (!cache.has(urlPath)) {
        const file = urlPath.replace(/^\//, "") + (urlPath.endsWith("/") ? "index.html" : "");
        let ids = new Set<string>();
        try {
          const html = readSiteFile(file);
          ids = new Set([...html.matchAll(/\bdata-id="([^"]*)"/g)].map((m) => m[1]));
        } catch {
          /* handled by the link test above */
        }
        cache.set(urlPath, ids);
      }
      return cache.get(urlPath)!;
    };

    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      for (const m of html.matchAll(/href="([^"]*\/gallery\/(?:general|archive)\/)#([0-9a-f-]{36})"/gi)) {
        const target = decodeEntities(m[1]).replace(SITE_BASE, "") || "/";
        if (!idsOn(target).has(m[2])) bad.push(`${file}: ${m[2]} is not on ${target}`);
      }
    }
    expect(bad.slice(0, 20), `${bad.length} deep link(s) point at a photo the target page does not show — lightbox.js matches window.location.hash against data-id\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });
});

test.describe("translations", () => {
  test("every page inside a language tree carries hreflang alternates", () => {
    const missing: string[] = [];
    for (const { file, html } of eachHtml()) {
      const u = urlOf(file);
      if (!LANGS.some((l) => u.startsWith(`/${l}/`))) continue;
      if (/http-equiv="refresh"/.test(html)) continue; // alias page, deliberately bare
      if (!/<link[^>]+rel="alternate"[^>]+hreflang=/.test(html)) missing.push(file);
    }
    expect(missing.slice(0, 20), `${missing.length} page(s)\n${missing.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("a page that exists in three languages declares all three alternates", () => {
    /* The weaker "has at least one alternate" check above passes on a page that
       names only itself — which is what 648 photo pages × 3 languages did, for
       as long as `translationKey` sat inside `params` instead of at the top
       level of .AddPage. Adapter pages are the ones at risk, so they are the
       ones checked: every photo, species and model page. */
    const kinds = ["gallery-photo", "dex-species", "model"];
    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      if (/http-equiv="refresh"/.test(html)) continue;
      if (!kinds.includes(pageKind(file))) continue;
      const langs = new Set(
        [...html.matchAll(/<link[^>]+rel="alternate"[^>]+hreflang="([a-z-]+)"/g)].map((m) => m[1]),
      );
      const missing = LANGS.filter((l) => !langs.has(l));
      if (missing.length) bad.push(`${file}: no ${missing.join(", ")} alternate`);
    }
    expect(bad.slice(0, 20), `${bad.length} adapter page(s) are not linked to their translations\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });
});

test.describe("structured data", () => {
  test("every JSON-LD block parses", () => {
    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      for (const block of jsonLdBlocks(html)) {
        try {
          JSON.parse(block);
        } catch (e: any) {
          bad.push(`${file}: ${e.message}`);
        }
      }
    }
    expect(bad.slice(0, 10), `${bad.length} unparseable block(s)\n${bad.slice(0, 10).join("\n")}`).toEqual([]);
  });

  test("each theme emits the @type it promises, and a dex page never emits BlogPosting", () => {
    /* The dex pages used to fall through to the BlogPosting branch, which
       asserted the site owner as author of Wikipedia's text and stamped
       datePublished: 0001-01-01 on 558 pages. */
    const want: Record<string, string> = {
      "gallery-photo": "ImageObject",
      "dex-species": "Taxon",
      model: "ProfilePage",
      profile: "ProfilePage",
      post: "BlogPosting",
    };
    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      if (/http-equiv="refresh"/.test(html)) continue;
      const kind = pageKind(file);
      const need = want[kind];
      if (!need) continue;
      const types = new Set(
        jsonLdBlocks(html).flatMap((b) => [...b.matchAll(/"@type":\s*"([^"]+)"/g)].map((m) => m[1])),
      );
      if (!types.has(need)) bad.push(`${file}: ${kind} has no ${need} (${[...types].join(", ") || "no JSON-LD"})`);
      if (kind === "dex-species" && types.has("BlogPosting")) bad.push(`${file}: dex page emits BlogPosting`);
      if (kind === "model" && types.has("BlogPosting")) bad.push(`${file}: model page emits BlogPosting`);
    }
    expect(bad.slice(0, 20), `${bad.length} page(s)\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("a production build emits the SEO partials", () => {
    /* head.html gates opengraph, twitter cards and JSON-LD on the production
       environment — the test build passes -e production for exactly this. */
    const home = readSiteFile(path.join("en", "index.html"));
    expect(home, "no opengraph — was this built without -e production?").toContain('property="og:title"');
    expect(home).toContain('name="twitter:card"');
    expect(jsonLdBlocks(home).length, "no JSON-LD on the home page").toBeGreaterThan(0);
  });
});

/* The site owner is ONE schema.org Person — docs/concepts/about-page-structured-data.md.
   Before, the About page and 24 other undated pages were BlogPostings published on
   0001-01-01, and the owner appeared as three unlinked Persons per page, one of
   them named after the site title and carrying a `logo`. */
test.describe("structured data — one person, no invented dates", () => {
  const cfg = () => hugoConfig().params;
  const personId = `${SITE_BASE}/#person`;
  const aboutSeg = () => String(cfg().author.page).replace(/^\/|\/$/g, "");

  /** Every object node inside one parsed JSON-LD value, depth first. */
  function nodes(v: any, out: any[] = []): any[] {
    if (Array.isArray(v)) v.forEach((x) => nodes(x, out));
    else if (v && typeof v === "object") {
      out.push(v);
      Object.values(v).forEach((x) => nodes(x, out));
    }
    return out;
  }
  function parsed(html: string): any[] {
    return jsonLdBlocks(html).map((b) => JSON.parse(b));
  }
  const isRedirect = (html: string) => /http-equiv="refresh"/.test(html);

  test("no invented dates, no logo on a Person, no empty keywords, wordCount is a number", () => {
    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      if (isRedirect(html)) continue;
      for (const n of parsed(html).flatMap((d) => nodes(d))) {
        for (const k of ["datePublished", "dateModified", "dateCreated"]) {
          if (String(n[k] ?? "").startsWith("0001")) bad.push(`${file}: ${k} ${n[k]}`);
        }
        if (n["@type"] === "Person" && "logo" in n) bad.push(`${file}: Person with a logo`);
        if (Array.isArray(n.keywords) && n.keywords.length === 0) bad.push(`${file}: empty keywords`);
        if ("wordCount" in n && typeof n.wordCount !== "number") bad.push(`${file}: wordCount ${JSON.stringify(n.wordCount)}`);
      }
    }
    expect(bad.slice(0, 20), `${bad.length} problem(s)\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("BlogPosting only on posts", () => {
    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      if (isRedirect(html) || pageKind(file) === "post") continue;
      if (parsed(html).flatMap((d) => nodes(d)).some((n) => n["@type"] === "BlogPosting")) bad.push(file);
    }
    expect(bad.slice(0, 20), `${bad.length} non-post page(s) claim to be a BlogPosting\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("every Person named after the owner carries the owner's @id", () => {
    /* The check that the graph is actually linked: author, publisher, a photo's
       creator and `about`, the owner's model page — all one person. */
    const name = cfg().author.name;
    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      if (isRedirect(html)) continue;
      for (const n of parsed(html).flatMap((d) => nodes(d))) {
        if (n["@type"] === "Person" && n.name === name && n["@id"] !== personId) bad.push(`${file}: ${JSON.stringify(n).slice(0, 120)}`);
      }
    }
    expect(bad.slice(0, 20), `${bad.length} unlinked owner Person(s)\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("the owner's @id is on no other model", () => {
    const owner = cfg().author.modelSlug;
    const bad: string[] = [];
    for (const m of models()) {
      for (const lang of LANGS) {
        const f = sitePath(lang, "gallery", "models", m.slug, "index.html");
        if (!fs.existsSync(f)) continue;
        const person = parsed(fs.readFileSync(f, "utf8")).find((d) => d["@type"] === "ProfilePage")?.mainEntity;
        const id = person?.["@id"];
        if (m.slug === owner && id !== personId) bad.push(`${lang}/${m.slug}: the owner's model page has @id ${id}`);
        if (m.slug !== owner && id !== undefined) bad.push(`${lang}/${m.slug}: somebody else's Person carries @id ${id}`);
      }
    }
    expect(bad).toEqual([]);
  });

  test("the About page is a ProfilePage of the owner, credited like its figure", () => {
    for (const lang of LANGS) {
      const html = readSiteFile(path.join(lang, aboutSeg(), "index.html"));
      const profile = parsed(html).find((d) => d["@type"] === "ProfilePage");
      expect(profile, `${lang}: no ProfilePage`).toBeTruthy();
      const person = profile.mainEntity;
      expect(person["@id"], lang).toBe(personId);
      expect(person.name, lang).toBe(cfg().author.name);
      expect(person.sameAs, `${lang}: sameAs must be params.schema.sameAs`).toEqual(cfg().schema.sameAs);

      /* One source for the credit: the portrait's resource metadata. The JSON-LD
         image and the figure's microdata must both say what it says. */
      const fm = frontMatter(`content/${aboutSeg()}/index.${lang}.md`);
      const portrait = (fm.resources ?? []).find((r: any) => r?.params?.portrait);
      expect(portrait, `${lang}: no portrait: true resource`).toBeTruthy();
      const credit = portrait.params.credit;
      expect(person.image?.creator?.name, `${lang}: JSON-LD image creator`).toBe(credit);
      const micro = html.match(/itemprop="creator"[^>]*>\s*<meta itemprop="name" content="([^"]*)"/);
      expect(micro?.[1], `${lang}: figure microdata creator`).toBe(credit);
      /* showCredit="false" on this page: named in the metadata, not under the photo. */
      expect(html, `${lang}: the credit line is switched off on the About page`).not.toContain('class="img-credit"');

      expect(html, lang).toContain('<meta property="og:type" content="profile" />');
    }
  });

  test("the home page is WebSite + Person, and every sameAs is a profile URL", () => {
    for (const lang of LANGS) {
      const html = readSiteFile(path.join(lang, "index.html"));
      const graph: any[] = parsed(html).find((d) => d["@graph"])?.["@graph"] ?? [];
      const site = graph.find((n) => n["@type"] === "WebSite");
      const person = graph.find((n) => n["@type"] === "Person");
      expect(site, `${lang}: no WebSite`).toBeTruthy();
      expect(person?.["@id"], `${lang}: Person @id`).toBe(personId);
      expect(site.publisher?.["@id"], `${lang}: WebSite publisher`).toBe(personId);
      expect(site.name, lang).toBe(cfg().ShortTitle);
      for (const u of person.sameAs ?? []) expect(u, `${lang}: sameAs`).toMatch(/^https:\/\//);
      expect(html, `${lang}: og:site_name`).toContain(`<meta property="og:site_name" content="${cfg().ShortTitle}" />`);
    }
  });

  test("every BreadcrumbList starts at the language home and counts 1…n", () => {
    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      if (isRedirect(html)) continue;
      for (const d of parsed(html)) {
        if (d["@type"] !== "BreadcrumbList") continue;
        const items: any[] = d.itemListElement;
        const pos = items.map((i) => i.position).join(",");
        if (pos !== items.map((_, i) => i + 1).join(",")) bad.push(`${file}: positions ${pos}`);
        const lang = urlOf(file).split("/")[1];
        if (items[0]?.item !== `${SITE_BASE}/${lang}/`) bad.push(`${file}: starts at ${items[0]?.item}`);
        /* A never-rendered section (/gallery/photo/) has no URL and must be skipped. */
        for (const i of items) if (!i.item) bad.push(`${file}: "${i.name}" has no URL`);
      }
    }
    expect(bad.slice(0, 20), `${bad.length} breadcrumb(s)\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("every URL in the JSON-LD is absolute", () => {
    /* Microdata resolves a relative href against the page; JSON-LD does not. The
       16 all-rights-reserved photos carried `"license": "/en/licensing/"`, which
       Google reported as an invalid URL — so exactly the photos whose licence
       says "ask me" were the ones not eligible for the Licensable badge. */
    const URL_KEYS = ["url", "contentUrl", "license", "acquireLicensePage", "item", "sameAs", "image", "@id"];
    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      if (isRedirect(html)) continue;
      for (const n of parsed(html).flatMap((d) => nodes(d))) {
        for (const k of URL_KEYS) {
          for (const v of [n[k]].flat()) {
            if (typeof v === "string" && !/^https?:\/\//.test(v)) bad.push(`${file}: ${k} = ${v}`);
          }
        }
      }
    }
    expect(bad.slice(0, 20), `${bad.length} relative URL(s) in JSON-LD\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("/about and the localised aliases reach the About page", () => {
    /* /about/ is a static file (a Hugo alias cannot write the domain root on a
       multilingual site) and goes to English; the rest are aliases. */
    const want: Record<string, string> = {
      "about": "en",
      "en/about": "en",
      "de/about": "de",
      "de/ueber-mich": "de",
      "sv/about": "sv",
      "sv/om-mig": "sv",
    };
    for (const [from, lang] of Object.entries(want)) {
      const html = readSiteFile(path.join(from, "index.html"));
      const target = html.match(/http-equiv="refresh" content="0; url=([^"]+)"/)?.[1] ?? "";
      expect(target.replace(SITE_BASE, ""), `/${from}/`).toBe(`/${lang}/${aboutSeg()}/`);
    }
  });
});

test.describe("robots", () => {
  test("a page marked robotsNoIndex says so in its meta robots", () => {
    const bad: string[] = [];
    for (const { file, html } of eachHtml()) {
      if (!/http-equiv="refresh"/.test(html)) continue;
      /* Alias pages are the one class that must always be noindex: they are a
         duplicate of the page they redirect to. */
      if (!/name="robots"[^>]*content="[^"]*noindex/i.test(html)) bad.push(file);
    }
    expect(bad.slice(0, 20), `${bad.length} redirect page(s) without noindex\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });
});

test("the build is not empty", () => {
  expect(htmlFiles().length, "no HTML under SITE_DIR — did the build run?").toBeGreaterThan(100);
});

/* Link previews (og:image) — a photography site whose shared links showed the
   site logo on 462 dex pages, the model page and five of the seven gallery
   sections, although every one of them has a photograph of its own. */
test.describe("link previews", () => {
  const LOGO = /Ping%C3%BCino|Pingüino/;
  const ogImage = (html: string) => html.match(/<meta property="og:image" content="([^"]+)"/)?.[1] ?? "";
  /** "…/Photo%20Name_hu_abc.jpg" → "Photo Name": the source photo behind a variant. */
  const stem = (u: string) => decodeURIComponent(u.split("/").pop() ?? "").split("_hu_")[0].replace(/\.[^.]+$/, "");

  test("the gallery sections, the models and every photographed species preview a photo", () => {
    const bad: string[] = [];
    const pages = ["gallery", "gallery/general", "gallery/dex", "gallery/projects", "gallery/portfolio", "gallery/archive"];
    const listed = models().filter((m) => m.visibility === "public");
    if (listed.length) pages.push("gallery/models");
    for (const m of models()) pages.push(`gallery/models/${m.slug}`);
    const caught = new Set(gallery().map((g) => String(g.species ?? "").toLowerCase()).filter(Boolean));
    for (const s of dex()) if (caught.has(String(s.scientific).toLowerCase())) pages.push(`gallery/dex/${s.slug}`);
    for (const lang of LANGS) {
      for (const p of pages) {
        const f = sitePath(lang, p, "index.html");
        if (!fs.existsSync(f)) continue;
        const img = ogImage(fs.readFileSync(f, "utf8"));
        if (!img || LOGO.test(img)) bad.push(`/${lang}/${p}/: og:image ${img || "(none)"}`);
      }
    }
    expect(bad.slice(0, 20), `${bad.length} page(s) preview the logo\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("a species nobody has photographed never previews its Commons stand-in", () => {
    /* The stand-in is mostly CC BY-SA; a link preview shows it with no
       attribution, which the licence does not allow. Those pages keep the logo. */
    const bad: string[] = [];
    for (const lang of LANGS) {
      for (const s of dex()) {
        const f = sitePath(lang, "gallery", "dex", s.slug, "index.html");
        if (!fs.existsSync(f)) continue;
        const img = ogImage(fs.readFileSync(f, "utf8"));
        if (/\/images\/dex\/reference\//.test(img)) bad.push(`/${lang}/gallery/dex/${s.slug}/: ${img}`);
      }
    }
    expect(bad).toEqual([]);
  });

  test("a section's preview is the photo on its gallery-home card, and the gallery previews its hero", () => {
    for (const lang of LANGS) {
      const home = readSiteFile(path.join(lang, "gallery", "index.html"));
      for (const section of ["projects", "general", "dex"]) {
        const card = home.match(new RegExp(`href="[^"]*/gallery/${section}/" class="gallery-nav-card" style="background-image: url\\('([^']+)'\\)"`))?.[1];
        expect(card, `${lang}: no ${section} card`).toBeTruthy();
        const preview = ogImage(readSiteFile(path.join(lang, "gallery", section, "index.html")));
        expect(stem(preview), `${lang}/gallery/${section}/: preview vs card`).toBe(stem(card!));
      }
      /* featured.html's hero on the gallery home = the portfolio's featured_image. */
      const hero = home.match(/class="featured-card"[^>]*style="background-image: url\('([^']+)'\)"/)?.[1];
      expect(stem(ogImage(home)), `${lang}/gallery/: preview vs hero`).toBe(stem(hero ?? ""));
      expect(stem(ogImage(readSiteFile(path.join(lang, "gallery", "portfolio", "index.html")))), `${lang}/gallery/portfolio/`).toBe(stem(hero ?? ""));
    }
  });
});
