/* L2 — data ↔ output.
 *
 * The build output is the contract with the outside world, and every check here
 * is the same shape: a fact stated in a data file has to be visible, once and
 * correctly, in the site Hugo produced from it. Invariants that make a single
 * page *wrong* stay errorf in the templates — this layer is for what a build
 * cannot see, which is cross-file consistency and rendered output. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import {
  REPO, LANGS, UUID_RE, asList,
  gallery, dex, licenseMap, i18nIds, manifests,
  sitePath, readSiteFile, htmlFiles, attrValues,
} from "../support/site";

test.describe("gallery.yaml", () => {
  test("every id is a UUID and unique", () => {
    const seen = new Map<string, string>();
    const problems: string[] = [];
    for (const e of gallery()) {
      if (!e.id || !UUID_RE.test(e.id)) problems.push(`${e.src}: id ${JSON.stringify(e.id)} is not a UUID`);
      else if (seen.has(e.id)) problems.push(`${e.src}: id ${e.id} already used by ${seen.get(e.id)}`);
      else seen.set(e.id, e.src ?? "?");
    }
    expect(problems, problems.join("\n")).toEqual([]);
  });

  test("every src is present and unique", () => {
    const seen = new Set<string>();
    const problems: string[] = [];
    for (const e of gallery()) {
      if (!e.src) problems.push(`${e.id}: no src`);
      else if (seen.has(e.src)) problems.push(`${e.id}: src ${e.src} is used twice`);
      else seen.add(e.src);
    }
    expect(problems, problems.join("\n")).toEqual([]);
  });

  test("every license is a key in licenseMap.yaml", () => {
    const keys = new Set(Object.keys(licenseMap()));
    const bad = gallery()
      .filter((e) => !e.license || !keys.has(e.license))
      .map((e) => `${e.src}: license ${JSON.stringify(e.license)}`);
    expect(bad, `licenses must be keys, not display strings — known keys: ${[...keys].join(", ")}\n${bad.join("\n")}`).toEqual([]);
  });

  test("every species names a scientific name in dex.yaml", () => {
    /* A warning in the build, on purpose: species names are an open external
       vocabulary. Here it is an assertion, because L0 fails on any WARN anyway
       and this says which photo. */
    const sci = new Set(dex().map((d: any) => String(d.scientific ?? "").trim().toLowerCase()));
    const bad = gallery()
      .filter((e) => e.species && !sci.has(String(e.species).trim().toLowerCase()))
      .map((e) => `${e.src}: species ${JSON.stringify(e.species)}`);
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("every project slug is an album under content/gallery/projects/", () => {
    const albums = new Set(
      fs.readdirSync(path.join(REPO, "content/gallery/projects"), { withFileTypes: true })
        .filter((d) => d.isDirectory())
        .map((d) => d.name),
    );
    const bad: string[] = [];
    for (const e of gallery()) {
      for (const slug of asList(e.project)) {
        if (!albums.has(slug)) bad.push(`${e.src}: project ${slug}`);
      }
    }
    expect(bad, `known albums: ${[...albums].join(", ")}\n${bad.join("\n")}`).toEqual([]);
  });
});

test.describe("UUID references", () => {
  /* featured_image:, dex_cover:, photo_id: and the models' cover: all name a
     photo by its id. A typo is a blank where a photo should be, which no
     template can tell from "deliberately absent". */
  test("every UUID referenced from content or data names a gallery entry", () => {
    const ids = new Set(gallery().map((e) => e.id));
    const bad: string[] = [];
    const fields = /^\s*(featured_image|dex_cover|photo_id|cover)\s*:\s*["']?([0-9a-f-]{36})["']?\s*$/gim;

    const scan = (dir: string, exts: string[]) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) scan(full, exts);
        else if (exts.some((x) => entry.name.endsWith(x))) {
          const text = fs.readFileSync(full, "utf8");
          for (const m of text.matchAll(fields)) {
            if (!ids.has(m[2])) bad.push(`${path.relative(REPO, full)}: ${m[1]} ${m[2]}`);
          }
        }
      }
    };
    scan(path.join(REPO, "content"), [".md", ".gotmpl"]);
    scan(path.join(REPO, "data"), [".yaml"]);
    expect(bad, bad.join("\n")).toEqual([]);
  });
});

test.describe("dex.yaml", () => {
  test("every record with a height has a height_measure", () => {
    const bad = dex()
      .filter((d: any) => d.height && !d.height_measure)
      .map((d: any) => `${d.slug}: height ${JSON.stringify(d.height)} with no height_measure`);
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("every height_measure is one of the five known dimensions", () => {
    const known = new Set(["shoulder", "standing", "length", "wingspan", "shell"]);
    const bad = dex()
      .filter((d: any) => d.height_measure && !known.has(String(d.height_measure)))
      .map((d: any) => `${d.slug}: height_measure ${JSON.stringify(d.height_measure)}`);
    expect(bad, `known: ${[...known].join(", ")}\n${bad.join("\n")}`).toEqual([]);
  });

  test("every sighting has numeric lat and lng", () => {
    const bad: string[] = [];
    for (const d of dex() as any[]) {
      for (const s of d.sightings ?? []) {
        if (typeof s?.lat !== "number" || typeof s?.lng !== "number") {
          bad.push(`${d.slug}: sighting ${JSON.stringify(s)}`);
        }
      }
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  test("slug and number are unique", () => {
    const problems: string[] = [];
    for (const key of ["slug", "number"] as const) {
      const seen = new Set<string>();
      for (const d of dex() as any[]) {
        const v = String(d[key]);
        if (seen.has(v)) problems.push(`duplicate ${key}: ${v}`);
        seen.add(v);
      }
    }
    expect(problems, problems.join("\n")).toEqual([]);
  });
});

test.describe("i18n", () => {
  test("the three files define the same keys", () => {
    const ids = i18nIds();
    const problems: string[] = [];
    const all = new Set<string>([...ids.en, ...ids.de, ...ids.sv]);
    for (const key of [...all].sort()) {
      const missing = LANGS.filter((l) => !ids[l].has(key));
      if (missing.length) problems.push(`${key}: missing in ${missing.join(", ")}`);
    }
    expect(problems, `a missing key falls back to English on a page in another language\n${problems.join("\n")}`).toEqual([]);
  });
});

test.describe("the gallery manifests", () => {
  test("each language writes one, and its count matches the YAML", () => {
    const m = manifests();
    for (const lang of LANGS) {
      expect(m[lang], `${lang}/gallery-metadata.json is missing — the gallerymeta output format has to be restated in languages.${lang}.outputs.home`).toBeTruthy();
      expect(m[lang]!.count, `${lang}: manifest count`).toBe(gallery().length);
      expect((m[lang] as any).photos.length, `${lang}: manifest photo records`).toBe(gallery().length);
    }
  });

  test("the three manifests agree on ids, and the ids are the YAML's", () => {
    const yamlIds = new Set(gallery().map((e) => e.id));
    for (const lang of LANGS) {
      const ids = new Set((manifests()[lang] as any).photos.map((p: any) => p.id));
      const missing = [...yamlIds].filter((id) => !ids.has(id));
      const extra = [...ids].filter((id) => !yamlIds.has(id as string));
      expect(missing, `${lang}: in the YAML, not in the manifest: ${missing.join(", ")}`).toEqual([]);
      expect(extra, `${lang}: in the manifest, not in the YAML: ${extra.join(", ")}`).toEqual([]);
    }
  });

  test("every manifest record carries a resolved licence", () => {
    const keys = new Set(Object.keys(licenseMap()));
    const bad: string[] = [];
    for (const p of (manifests().en as any).photos) {
      if (!p.license?.key || !keys.has(p.license.key)) bad.push(`${p.src}: ${JSON.stringify(p.license)}`);
      if (!p.license?.terms) bad.push(`${p.src}: no licence terms to embed`);
      if (!p.artist) bad.push(`${p.src}: no artist`);
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });
});

test.describe("the gallery pages", () => {
  test("general + archive show exactly the photos in the YAML", () => {
    for (const lang of LANGS) {
      const ids = new Set<string>();
      for (const page of ["general", "archive"]) {
        const html = readSiteFile(path.join(lang, "gallery", page, "index.html"));
        for (const id of attrValues(html, "data-id")) ids.add(id);
      }
      const yamlIds = new Set(gallery().map((e) => e.id!));
      const missing = [...yamlIds].filter((id) => !ids.has(id));
      const extra = [...ids].filter((id) => !yamlIds.has(id));
      expect(missing, `${lang}: in the YAML but on neither grid: ${missing.slice(0, 10).join(", ")}`).toEqual([]);
      expect(extra, `${lang}: on a grid but not in the YAML: ${extra.slice(0, 10).join(", ")}`).toEqual([]);
    }
  });

  test("the archive grid holds exactly the archived photos", () => {
    const archived = new Set(gallery().filter((e) => e.section === "archive").map((e) => e.id!));
    for (const lang of LANGS) {
      const html = readSiteFile(path.join(lang, "gallery", "archive", "index.html"));
      const shown = new Set(attrValues(html, "data-id"));
      expect([...archived].filter((id) => !shown.has(id)), `${lang}: archived but not on the archive grid`).toEqual([]);
      expect([...shown].filter((id) => !archived.has(id)), `${lang}: on the archive grid but not archived`).toEqual([]);
    }
  });
});

test.describe("photo pages", () => {
  /* Every photo gets its own page per language, plus a permanent /photo/<uuid>/
     alias and one redirect per slugAlias. The real pages are the ones that are
     not a redirect. */
  function realPhotoPages(lang: string): Map<string, string> {
    const dir = sitePath(lang, "gallery", "photo");
    const out = new Map<string, string>();
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const file = path.join(dir, entry.name, "index.html");
      if (!fs.existsSync(file)) continue;
      const html = fs.readFileSync(file, "utf8");
      if (/http-equiv="refresh"/.test(html)) continue;
      const id = attrValues(html, "data-id")[0];
      out.set(entry.name, id);
    }
    return out;
  }

  for (const lang of LANGS) {
    test(`${lang}: one page per entry, and every page maps back to an entry`, () => {
      const pages = realPhotoPages(lang);
      const ids = new Set(pages.values());
      const yamlIds = new Set(gallery().map((e) => e.id!));
      expect(pages.size, `${lang}: real photo pages`).toBe(gallery().length);
      expect([...yamlIds].filter((id) => !ids.has(id)), `${lang}: entries with no page`).toEqual([]);
      expect([...ids].filter((id) => !yamlIds.has(id as string)), `${lang}: pages with no entry`).toEqual([]);
    });

    test(`${lang}: every photo keeps its permanent /photo/<uuid>/ alias`, () => {
      const missing = gallery()
        .map((e) => e.id!)
        .filter((id) => !fs.existsSync(sitePath(lang, "gallery", "photo", id, "index.html")));
      expect(missing, `${lang}: uuid alias missing for ${missing.slice(0, 10).join(", ")}`).toEqual([]);
    });
  }

  test("the three languages are linked by translationKey, not by URL", () => {
    /* The slug is per language on purpose, so the three segments differ; what
       has to hold is that each language has a page for the same id. */
    const byLang = LANGS.map((l) => new Set(realPhotoPages(l).values()));
    for (let i = 1; i < byLang.length; i++) {
      const diff = [...byLang[0]].filter((id) => !byLang[i].has(id));
      expect(diff, `${LANGS[i]} has no page for ${diff.slice(0, 5).join(", ")}`).toEqual([]);
    }
  });
});
