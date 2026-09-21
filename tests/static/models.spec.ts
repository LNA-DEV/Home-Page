/* L2 — the models section.
 *
 * The one place in this repo where a silent failure costs somebody other than
 * the author. `visibility` is a decision a person made; the build enforces it
 * with allowlists (never `ne "hidden"`, because errorf marks a build failed
 * without stopping template execution), and this layer checks the result in the
 * files that would actually be published.
 *
 * The `hidden` test is vacuous while no record is hidden. That is the reason to
 * write it now rather than when it first matters. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import {
  REPO, LANGS, asList, gallery, models, sitePath, readSiteFile, eachHtml, jsonLdBlocks,
} from "../support/site";

const VISIBILITIES = ["public", "unlisted", "hidden"];

function byVisibility(v: string) {
  return (models() as any[]).filter((m) => m.visibility === v);
}

test.describe("data/models.yaml", () => {
  test("every record has a slug and an explicit visibility", () => {
    const bad: string[] = [];
    for (const m of models() as any[]) {
      if (!m.slug) bad.push(`record without slug: ${JSON.stringify(m).slice(0, 80)}`);
      if (!m.visibility) bad.push(`${m.slug}: no visibility — there is no default, on purpose`);
      else if (!VISIBILITIES.includes(m.visibility)) bad.push(`${m.slug}: visibility ${JSON.stringify(m.visibility)}`);
      /* name is required only on a record that renders: a tombstone may be
         slug + visibility and nothing else. */
      if (m.visibility !== "hidden" && !m.name) bad.push(`${m.slug}: no name`);
    }
    expect(bad, `valid values: ${VISIBILITIES.join(", ")}\n${bad.join("\n")}`).toEqual([]);
  });

  test("slugs are unique", () => {
    const seen = new Set<string>();
    const dupes = (models() as any[]).map((m) => m.slug).filter((s) => (seen.has(s) ? true : (seen.add(s), false)));
    expect(dupes, `a slug is reserved forever, tombstones included\n${dupes.join(", ")}`).toEqual([]);
  });

  test("no record carries contact details", () => {
    /* The repository is public, so every line of this file is page content
       whether it was meant that way or not. */
    const raw = fs.readFileSync(path.join(REPO, "data", "models.yaml"), "utf8");
    const hits = [...raw.matchAll(/[\w.+-]+@[\w-]+\.[a-z]{2,}|(?:\+\d[\d\s/-]{7,})/gi)].map((m) => m[0]);
    expect(hits, `looks like contact details in data/models.yaml: ${hits.join(", ")}`).toEqual([]);
  });
});

test.describe("the join", () => {
  test("every model: slug in gallery.yaml has a record", () => {
    /* A hard error in the build, unlike an unknown species: model slugs are a
       small closed set the author invented himself, so a miss is always a typo —
       and the cost is a person losing the credit or the visibility they agreed
       to. */
    const known = new Set((models() as any[]).map((m) => m.slug));
    const bad: string[] = [];
    for (const e of gallery()) {
      for (const slug of asList(e.model)) if (!known.has(slug)) bad.push(`${e.src}: model ${slug}`);
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("every cover names a gallery photo", () => {
    const ids = new Set(gallery().map((e) => e.id));
    const bad = (models() as any[])
      .filter((m) => m.cover && !ids.has(m.cover))
      .map((m) => `${m.slug}: cover ${m.cover}`);
    expect(bad, bad.join("\n")).toEqual([]);
  });
});

test.describe("visibility, in the built site", () => {
  test("a hidden record appears nowhere under SITE_DIR", () => {
    const hidden = byVisibility("hidden");
    test.skip(hidden.length === 0, "no record is hidden today — the check is written for when one is");

    const needles = hidden.flatMap((m) => [m.slug, m.name].filter(Boolean) as string[]);
    const hits: string[] = [];
    for (const { file, html } of eachHtml()) {
      for (const n of needles) {
        if (html.includes(n)) hits.push(`${file}: contains ${JSON.stringify(n)}`);
      }
      for (const n of needles) {
        if (file.includes(n)) hits.push(`${file}: the path itself contains ${JSON.stringify(n)}`);
      }
    }
    expect(hits.slice(0, 20), `${hits.length} occurrence(s) — hidden means the name appears in no page, caption, attribute, feed or path\n${hits.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("a hidden record renders no page", () => {
    const bad: string[] = [];
    for (const m of byVisibility("hidden")) {
      for (const lang of LANGS) {
        if (fs.existsSync(sitePath(lang, "gallery", "models", m.slug, "index.html"))) {
          bad.push(`${lang}/gallery/models/${m.slug}/`);
        }
      }
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("an unlisted record is reachable but in no listing", () => {
    const unlisted = byVisibility("unlisted");
    test.skip(unlisted.length === 0, "no record is unlisted today");

    const bad: string[] = [];
    for (const m of unlisted) {
      for (const lang of LANGS) {
        const page = sitePath(lang, "gallery", "models", m.slug, "index.html");
        if (!fs.existsSync(page)) {
          bad.push(`${lang}: ${m.slug} has no page — unlisted means "not in a listing", not "unreachable"`);
          continue;
        }
        const url = `/${lang}/gallery/models/${m.slug}/`;
        const sitemap = readSiteFile(path.join(lang, "sitemap.xml"));
        if (sitemap.includes(url)) bad.push(`${lang}: ${m.slug} is in sitemap.xml`);
        const grid = readSiteFile(path.join(lang, "gallery", "models", "index.html"));
        if (grid.includes(`/gallery/models/${m.slug}/`)) bad.push(`${lang}: ${m.slug} is linked from the grid`);
        const index = path.join(lang, "index.json");
        if (fs.existsSync(sitePath(index)) && readSiteFile(index).includes(url)) {
          bad.push(`${lang}: ${m.slug} is in the search index`);
        }
        if (!/name="robots"[^>]*content="[^"]*noindex/i.test(fs.readFileSync(page, "utf8"))) {
          bad.push(`${lang}: ${m.slug} has no noindex`);
        }
      }
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("a public record has a page in all three languages, listed in the grid", () => {
    const bad: string[] = [];
    for (const m of byVisibility("public")) {
      /* A record with no photo of its own renders no page at all — there is no
         "uncaught" state here, unlike a dex species — so only check the ones
         the gallery actually shows. Archive photos do not count. */
      const shown = gallery().some(
        (e) => asList(e.model).includes(m.slug) && e.section !== "archive",
      );
      if (!shown) continue;
      for (const lang of LANGS) {
        const page = sitePath(lang, "gallery", "models", m.slug, "index.html");
        if (!fs.existsSync(page)) {
          bad.push(`${lang}: ${m.slug} has no page`);
          continue;
        }
        const grid = readSiteFile(path.join(lang, "gallery", "models", "index.html"));
        if (!grid.includes(`/gallery/models/${m.slug}/`)) bad.push(`${lang}: ${m.slug} is not in the grid`);
      }
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("a record whose photos are all archived renders no page", () => {
    const bad: string[] = [];
    for (const m of models() as any[]) {
      if (m.visibility === "hidden") continue;
      const photos = gallery().filter((e) => asList(e.model).includes(m.slug));
      if (photos.length === 0 || photos.every((e) => e.section === "archive")) {
        for (const lang of LANGS) {
          if (fs.existsSync(sitePath(lang, "gallery", "models", m.slug, "index.html"))) {
            bad.push(`${lang}: ${m.slug} has a page but nothing current to show`);
          }
        }
      }
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });
});

test.describe("the model page itself", () => {
  test("a ProfilePage names the person and nothing the page does not", () => {
    const bad: string[] = [];
    for (const m of byVisibility("public")) {
      const page = sitePath("en", "gallery", "models", m.slug, "index.html");
      if (!fs.existsSync(page)) continue;
      const html = fs.readFileSync(page, "utf8");

      const profile = jsonLdBlocks(html)
        .map((b) => {
          try { return JSON.parse(b); } catch { return null; }
        })
        .find((j) => j?.["@type"] === "ProfilePage");
      if (!profile) {
        bad.push(`${m.slug}: no ProfilePage JSON-LD — without it the page falls through to BlogPosting, claiming the site owner as author of somebody else's bio`);
        continue;
      }
      expect(profile.mainEntity?.name, `${m.slug}: mainEntity.name`).toBe(m.name);

      const sameAs: string[] = profile.mainEntity?.sameAs ?? [];
      const links: string[] = (m.links ?? []).map((l: any) => l.url);
      const extra = sameAs.filter((u) => !links.includes(u));
      const missing = links.filter((u) => !sameAs.includes(u));
      if (extra.length) bad.push(`${m.slug}: sameAs holds URLs the record does not: ${extra.join(", ")}`);
      if (missing.length) bad.push(`${m.slug}: sameAs is missing ${missing.join(", ")}`);
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("the links carry rel=noopener and never rel=me", () => {
    /* rel=me is an identity claim about the site's author. A model page links to
       somebody else, so making that claim would be false; the honest place for
       those URLs is sameAs. */
    const bad: string[] = [];
    for (const m of byVisibility("public")) {
      const page = sitePath("en", "gallery", "models", m.slug, "index.html");
      if (!fs.existsSync(page)) continue;
      const html = fs.readFileSync(page, "utf8");
      const section = html.match(/<(?:ul|div)[^>]*class="[^"]*model-links[^"]*"[\s\S]*?<\/(?:ul|div)>/i)?.[0] ?? "";
      const anchors = [...section.matchAll(/<a\b[^>]*>/gi)];
      /* Guard against the test quietly passing because the block moved and the
         selector stopped matching. */
      if ((m.links ?? []).length && anchors.length !== m.links.length) {
        bad.push(`${m.slug}: found ${anchors.length} link anchor(s) for ${m.links.length} record link(s) — has .model-links moved?`);
      }
      for (const a of anchors) {
        if (/rel="[^"]*\bme\b/i.test(a[0])) bad.push(`${m.slug}: rel=me on ${a[0].slice(0, 90)}`);
        if (!/rel="[^"]*noopener/i.test(a[0])) bad.push(`${m.slug}: no rel=noopener on ${a[0].slice(0, 90)}`);
      }
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("the section emits HTML only — no per-section gallery feed", () => {
    /* rss.xml branches on `eq .Section "gallery"`, so a section below /gallery/
       otherwise emits the same 572-photo feed per language, with links to
       anchors that do not exist on that page. */
    for (const lang of LANGS) {
      const feed = sitePath(lang, "gallery", "models", "index.xml");
      expect(fs.existsSync(feed), `${lang}/gallery/models/index.xml should not exist — the stub sets outputs: [HTML]`).toBe(false);
    }
  });
});
