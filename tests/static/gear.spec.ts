/* L2 — /gallery/gear/, cameras and lenses counted.
 *
 * docs/concepts/gallery-gear.md. The page aggregates what every photo page
 * already says: a photo page links its camera and its lens to their entry on
 * the gear page. So the check that needs no EXIF reader is that the two agree —
 * a lens card counts exactly the photo pages that link to it, and the cards plus
 * the "without camera data" footnote account for every photo in
 * data/gallery.yaml. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { parse as parseYaml } from "yaml";
import { REPO, LANGS, gallery, sitePath } from "../support/site";

const gear = (): any => parseYaml(fs.readFileSync(path.join(REPO, "data/gear.yaml"), "utf8"));

/** Every gear-page slug a real (non-redirect) photo page links to, per page. */
function photoPageLinks(lang: string): Set<string>[] {
  const dir = sitePath(lang, "gallery", "photo");
  const out: Set<string>[] = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (!e.isDirectory()) continue;
    const f = path.join(dir, e.name, "index.html");
    if (!fs.existsSync(f)) continue;
    const html = fs.readFileSync(f, "utf8");
    if (/http-equiv="refresh"/.test(html)) continue;
    out.push(new Set([...html.matchAll(/href="[^"]*\/gallery\/gear\/#([^"]+)"/g)].map((m) => m[1])));
  }
  return out;
}

/** The cards of one language's gear page: slug -> count. */
function cards(lang: string): Map<string, number> {
  const html = fs.readFileSync(sitePath(lang, "gallery", "gear", "index.html"), "utf8");
  return new Map(
    [...html.matchAll(/<article class="gear-card" id="([^"]+)" data-count="(\d+)">/g)].map((m) => [m[1], Number(m[2])]),
  );
}

function footnote(lang: string, attr: string): number {
  const html = fs.readFileSync(sitePath(lang, "gallery", "gear", "index.html"), "utf8");
  return Number(html.match(new RegExp(`class="gear-footnote"[^>]*${attr}="(\\d+)"`))?.[1] ?? 0);
}

test.describe("data/gear.yaml", () => {
  test("slugs are unique across bodies and lenses, and every match string belongs to one record", () => {
    const g = gear();
    const slugs = [...(g.bodies ?? []), ...(g.lenses ?? [])].map((r: any) => String(r.slug));
    expect(slugs.filter((s, i) => slugs.indexOf(s) !== i), "duplicate slugs").toEqual([]);
    for (const kind of ["bodies", "lenses"]) {
      const strings = (g[kind] ?? []).flatMap((r: any) =>
        (r.match ?? []).map((m: any) => String(typeof m === "object" ? m.text : m).trim().toLowerCase()),
      );
      expect(strings.filter((s: string, i: number) => strings.indexOf(s) !== i), `${kind}: duplicate match strings`).toEqual([]);
    }
  });

  test("every lens_default names a lens", () => {
    const g = gear();
    const lenses = new Set((g.lenses ?? []).map((r: any) => r.slug));
    const bad = (g.bodies ?? []).filter((b: any) => b.lens_default && !lenses.has(b.lens_default)).map((b: any) => b.slug);
    expect(bad).toEqual([]);
  });
});

test.describe("the gear page", () => {
  for (const lang of LANGS) {
    test(`${lang}: each card counts exactly the photo pages that link to it`, () => {
      const links = photoPageLinks(lang);
      const have = cards(lang);
      expect(have.size, `${lang}: no cards on the gear page`).toBeGreaterThan(0);
      for (const [slug, count] of have) {
        const linked = links.filter((s) => s.has(slug)).length;
        expect(linked, `${lang}: card ${slug} says ${count}, ${linked} photo pages link to it`).toBe(count);
      }
    });

    test(`${lang}: the cards and the footnote account for every photo`, () => {
      const sum = [...cards(lang).values()].reduce((a, b) => a + b, 0);
      expect(sum + footnote(lang, "data-no-data") + footnote(lang, "data-no-lens")).toBe(gallery().length);
    });

    test(`${lang}: a body with a lens_default never leaves a photo without a lens row`, () => {
      /* The Lumix G91 writes its lens only into the maker note, which Hugo does
         not read; before the gear register its 336 photo pages had no lens row. */
      const links = photoPageLinks(lang);
      for (const b of (gear().bodies ?? []).filter((b: any) => b.lens_default)) {
        const bodyPages = links.filter((s) => s.has(b.slug));
        expect(bodyPages.length, `${lang}: no photo page links ${b.slug}`).toBeGreaterThan(0);
        const without = bodyPages.filter((s) => !s.has(b.lens_default)).length;
        expect(without, `${lang}: ${without} ${b.slug} photo pages without ${b.lens_default}`).toBe(0);
      }
    });
  }
});
