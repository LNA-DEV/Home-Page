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
} from "../support/site";

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
