/* L2 — gallery projects that tell a story (docs/concepts/gallery-project-stories.md §10).
 *
 * Every project page whose project_layout is essay or journal, in every
 * language, is held against data/gallery.yaml: each of the project's photos
 * exactly once in the story, every story image sized and described, one h1, a
 * toggle that renders hidden, and a map that can only ever draw coarse circles.
 *
 * Story pages are found by their layout, not by name. Until the owner switches a
 * real project they are the unlisted demos (§3.1); once those are deleted and
 * no story is left, the page tests skip instead of failing. */

import { test, expect } from "@playwright/test";
import {
  projectPages, storyPages, projectPhotoIds, galleryAreas, readSiteFile,
} from "../support/site";

/* Enough of HTML's entities for an attribute Hugo wrote: data-areas is JSON
   inside double quotes, so its quotes arrive as &#34;. */
function decodeEntities(s: string): string {
  return s
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&quot;/g, '"')
    .replace(/&#x27;|&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

/* The story part of a page: from the story wrapper to the grid that follows it. */
function storyPart(html: string): string {
  const start = html.indexOf('class="story-page');
  const end = html.indexOf('id="grid"', start);
  return start < 0 ? "" : html.slice(start, end < 0 ? undefined : end);
}

/* At most two decimals, the rule of data/galleryAreas.yaml (§8). */
const COARSE = /^-?\d{1,3}(\.\d{1,2})?$/;

test.describe("data/galleryAreas.yaml", () => {
  test("every area is coarse: 2 decimals at most, a radius of 1,000 m at least", () => {
    const bad: string[] = [];
    for (const a of galleryAreas()) {
      for (const k of ["lat", "lng"]) {
        if (!COARSE.test(String(a[k]))) bad.push(`${a.slug}: ${k} ${a[k]}`);
      }
      if (!(Number(a.radius) >= 1000)) bad.push(`${a.slug}: radius ${a.radius}`);
    }
    expect(bad, `a precise area could point at a nest\n${bad.join("\n")}`).toEqual([]);
  });

  test("every area a project names is in the file", () => {
    const known = new Set(galleryAreas().map((a) => a.slug));
    const bad = projectPages().flatMap((p) => p.areas.filter((s) => !known.has(s)).map((s) => `${p.source}: ${s}`));
    expect(bad, bad.join("\n")).toEqual([]);
  });
});

test.describe("project pages", () => {
  test("a grid project is today's page: no story markup", () => {
    const bad: string[] = [];
    for (const p of projectPages().filter((p) => p.layout === "grid")) {
      const html = readSiteFile(p.file);
      if (html.includes('class="story-page')) bad.push(p.url);
      if (!html.includes('id="gallery"')) bad.push(`${p.url}: no grid`);
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("every project page, whatever its layout, links its listed neighbours", () => {
    /* gallery-project-nav.html: previous and next among the LISTED projects by
       weight, no wrapping; a page outside the list offers the first listed one. */
    const bad: string[] = [];
    for (const p of projectPages()) {
      const listed = projectPages()
        .filter((q) => q.lang === p.lang && q.listed)
        .sort((a, b) => a.weight - b.weight || a.url.localeCompare(b.url));
      const i = listed.findIndex((q) => q.url === p.url);
      const want = {
        prev: i > 0 ? listed[i - 1].url : "",
        next: i < 0 ? listed[0]?.url ?? "" : listed[i + 1]?.url ?? "",
      };
      const html = readSiteFile(p.file);
      const nav = html.match(/<nav class="project-nav"[\s\S]*?<\/nav>/)?.[0] ?? "";
      for (const dir of ["prev", "next"] as const) {
        const got = nav.match(new RegExp(`class="project-nav-card project-nav-${dir}" href="([^"]*)"`))?.[1] ?? "";
        if (got !== want[dir]) bad.push(`${p.url}: ${dir} is ${got || "none"}, expected ${want[dir] || "none"}`);
      }
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("every story page still carries the whole grid", () => {
    const stories = storyPages();
    test.skip(stories.length === 0, "no project uses project_layout essay or journal");
    const bad: string[] = [];
    for (const p of stories) {
      const html = readSiteFile(p.file);
      const grid = html.slice(html.indexOf('id="grid"'));
      const ids = new Set([...grid.matchAll(/class="gallery-item"[^>]*?data-id="([^"]+)"/g)].map((m) => m[1]));
      for (const id of projectPhotoIds(p.slug)) if (!ids.has(id)) bad.push(`${p.url}: ${id} missing from #grid`);
    }
    expect(bad.slice(0, 20), bad.join("\n")).toEqual([]);
  });
});

for (const p of storyPages()) {
  test.describe(`${p.layout} ${p.url}`, () => {
    test("shows every photo of the project exactly once, the hero included", () => {
      const story = storyPart(readSiteFile(p.file));
      const placed = [...story.matchAll(/\bdata-id="([^"]+)"/g)].map((m) => m[1]);
      const expected = projectPhotoIds(p.slug).sort();
      const twice = placed.filter((id, i) => placed.indexOf(id) !== i);
      expect(twice, `shown more than once: ${twice.join(", ")}`).toEqual([]);
      expect([...placed].sort()).toEqual(expected);
      if (p.featured) expect(story, "the hero is the featured_image").toContain(`data-id="${p.featured}"`);
    });

    test("every story image has a size and a description, and only the hero loads eagerly", () => {
      /* The next-project card's thumbnail sits beside the project's name and is
         decorative (alt=""), so it is left out. */
      const story = storyPart(readSiteFile(p.file)).replace(/<a class="story-next"[\s\S]*?<\/a>/, "");
      const bad: string[] = [];
      let eager = 0;
      for (const m of story.matchAll(/<img\b[^>]*>/g)) {
        const tag = m[0];
        const alt = tag.match(/\balt="([^"]*)"/)?.[1] ?? "";
        if (!/\bwidth="\d+"/.test(tag) || !/\bheight="\d+"/.test(tag)) bad.push(`no width/height: ${tag.slice(0, 100)}`);
        if (!decodeEntities(alt).trim()) bad.push(`empty alt: ${tag.slice(0, 100)}`);
        if (/loading="eager"/.test(tag)) eager++;
        else if (!/loading="lazy"/.test(tag)) bad.push(`neither lazy nor the hero: ${tag.slice(0, 100)}`);
      }
      expect(bad.slice(0, 10), bad.join("\n")).toEqual([]);
      expect(eager, "only the hero loads eagerly").toBeLessThanOrEqual(1);
    });

    test("has one h1", () => {
      const html = readSiteFile(p.file);
      expect([...html.matchAll(/<h1\b/g)].length).toBe(1);
    });

    test("renders the toggle hidden, with aria-pressed buttons", () => {
      const story = storyPart(readSiteFile(p.file));
      const toggle = story.match(/<div class="story-toggle"[^>]*>([\s\S]*?)<\/div>/);
      expect(toggle, "no toggle").not.toBeNull();
      expect(toggle![0], "a visitor without JavaScript must not meet a dead control").toMatch(/<div class="story-toggle"[^>]*\bhidden\b/);
      const buttons = [...toggle![1].matchAll(/<button\b[^>]*>/g)].map((m) => m[0]);
      expect(buttons).toHaveLength(2);
      for (const b of buttons) expect(b).toMatch(/aria-pressed="(true|false)"/);
      expect(story, '"Show as grid" works without JavaScript').toContain('href="#grid"');
    });

    test("draws nothing on a map but coarse areas", () => {
      const story = storyPart(readSiteFile(p.file));
      const bad: string[] = [];
      for (const m of story.matchAll(/data-areas="([^"]*)"/g)) {
        for (const a of JSON.parse(decodeEntities(m[1])) as any[]) {
          if (!COARSE.test(String(a.lat)) || !COARSE.test(String(a.lng))) bad.push(`${a.slug}: ${a.lat}, ${a.lng}`);
          if (!(a.radius >= 1000)) bad.push(`${a.slug}: radius ${a.radius}`);
        }
      }
      for (const m of story.matchAll(/data-lat="([^"]*)" data-lng="([^"]*)" data-radius="([^"]*)"/g)) {
        if (!COARSE.test(m[1]) || !COARSE.test(m[2])) bad.push(`mini map: ${m[1]}, ${m[2]}`);
        if (!(Number(m[3]) >= 1000)) bad.push(`mini map: radius ${m[3]}`);
      }
      expect(bad, bad.join("\n")).toEqual([]);
      if (p.areas.length) expect(story, "a project with areas lists them for a browser without a map").toContain('class="story-area-list"');
    });
  });
}
