/* L2 — image URLs that only we can move (docs/concepts/stable-image-urls.md).
 *
 * Until 2026-10 every processed image was published under Hugo's cache key,
 * `<name>_hu_<hash>.<ext>`, and on 2026-09-10 a Hugo release moved all of them
 * with byte-identical files behind them. Nothing in the repo changed, so nothing
 * here could have caught it. Now every variant has a name of the site's own —
 * `<dir>/<spec>/<source name>.<ext>`, made by layouts/partials/image-variant.html
 * and nowhere else — and these checks hold that:
 *
 *   - no `_hu_` file anywhere in the build (the guard against a missed call
 *     site, theme templates included);
 *   - no template outside image-variant.html processes an image (the source:
 *     two chains under one name publish whichever rendered first, and the output
 *     cannot show that, because the second publishes nothing new);
 *   - every variant sits in a spec directory under its source's name;
 *   - the variant redirect map's invariants;
 *   - one contentUrl per photo, wherever it is described. */

import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import {
  REPO, LANGS, manifests, readSiteFile, servedPaths, sitePath, urlOf, jsonLdBlocks,
} from "../support/site";

const SPEC_DIR = /^(?:resize|fit|fill|crop)-[a-z0-9]+(?:-[a-z0-9]+)*$/;

/* ------------------------------------------------------------- the output */

test("no file anywhere in the build has a Hugo `_hu_` name", () => {
  const bad = [...servedPaths()].filter((u) => /_hu_[0-9a-f]+\.[^/]+$/.test(u)).sort();
  expect(bad.slice(0, 20), `${bad.length} file(s) published under Hugo's cache key — a template ` +
    `processed an image outside image-variant.html:\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
});

test("every variant sits in a spec directory under its source's name", () => {
  /* A variant is <dir>/<spec>/<sub-path/stem>.<ext>. Its source is:
       - under images/gallery/, a live photo — the manifest's `file`, by stem
         (the extension is the output format's);
       - a page resource, published next to the spec directory by its bundle;
       - a global asset under assets/, which is never published itself. */
  const photos = new Set(((manifests().en as any)?.photos ?? []).map((p: any) => String(p.file).replace(/\.[^.]+$/, "")));
  const served = servedPaths();
  const stems = new Map<string, Set<string>>();
  const stemsOf = (dir: string) => {
    if (!stems.has(dir)) {
      const set = new Set<string>();
      for (const base of [sitePath(dir), path.join(REPO, "assets", dir)]) {
        if (!fs.existsSync(base)) continue;
        for (const e of fs.readdirSync(base, { withFileTypes: true })) {
          if (e.isFile()) set.add(e.name.replace(/\.[^.]+$/, "").toLowerCase());
        }
      }
      stems.set(dir, set);
    }
    return stems.get(dir)!;
  };
  const bad: string[] = [];
  let variants = 0;
  for (const u of served) {
    const parts = u.split("/").filter(Boolean);
    const at = parts.findLastIndex((p, i) => i < parts.length - 1 && SPEC_DIR.test(p));
    if (at < 0) continue;
    variants++;
    const parent = parts.slice(0, at).join("/");
    const rest = parts.slice(at + 1);
    const stem = rest[rest.length - 1].replace(/\.[^.]+$/, "");
    if (parent === "images/gallery") {
      if (rest.length !== 1 || !photos.has(stem)) bad.push(`${u}: no live photo is called ${stem}`);
      continue;
    }
    const srcDir = [parent, ...rest.slice(0, -1)].join("/");
    /* A machine-specific mount (the game screenshots) is in neither place. */
    if (srcDir.startsWith("images/games/screenshots/")) continue;
    if (!stemsOf(srcDir).has(stem.toLowerCase())) bad.push(`${u}: no source ${srcDir}/${stem}.*`);
  }
  expect(variants, "no spec directory in the build at all").toBeGreaterThan(1000);
  expect(bad.slice(0, 20), `${bad.length} variant(s) without a source of that name\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
});

/* ------------------------------------------------------------- the source */

test("no template outside image-variant.html processes an image", () => {
  /* One chain per published name is what makes the bytes behind a name not
     depend on render order: `resources.Copy` to a taken path silently returns
     the first resource, and --printPathWarnings says nothing. The output cannot
     prove it — a second chain under a taken name publishes nothing — so the
     rule is held at the source. Comments are stripped first. */
  const PROCESSING = /\.(?:Resize|Fit|Fill|Crop|Process|Filter)\b|\bimages\.(?:Process|Filter|AutoOrient|Resize|Fit|Fill|Crop)\b|\bresources\.Copy\b/g;
  const ALLOW: { file: string; match: RegExp; why: string }[] = [
    { file: "layouts/partials/image-variant.html", match: /./, why: "the one producer" },
    { file: "layouts/partials/gallery-images.html", match: /^resources\.Copy$/,
      why: "copies each ORIGINAL to its slug name; processes nothing" },
    { file: "layouts/partials/image-variants.html", match: /^\.Filter$|^images\.AutoOrient$/,
      why: "reads the oriented width off an AutoOrient'ed copy; publishes nothing" },
  ];
  const files: string[] = [];
  const walk = (d: string) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, e.name);
      if (e.isDirectory()) walk(full);
      else files.push(path.relative(REPO, full));
    }
  };
  walk(path.join(REPO, "layouts"));
  const bad: string[] = [];
  const used = new Set<string>();
  for (const file of files) {
    const text = fs.readFileSync(path.join(REPO, file), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
    for (const m of text.matchAll(PROCESSING)) {
      const allow = ALLOW.find((a) => a.file === file && a.match.test(m[0]));
      if (allow) { used.add(allow.file); continue; }
      const line = text.slice(0, m.index).split("\n").length;
      bad.push(`${file}:${line}: ${m[0]}`);
    }
  }
  expect(bad, `image processing outside image-variant.html — route it through ` +
    `partial "image-variant.html" (dict "image" … "spec" …):\n${bad.join("\n")}`).toEqual([]);
  /* An allowance nothing needs any more is a hole waiting to be used. */
  const stale = ALLOW.filter((a) => a.file !== "layouts/partials/image-variant.html" && !used.has(a.file)).map((a) => a.file);
  expect(stale, "allowlist entries that match nothing").toEqual([]);
});

/* -------------------------------------------------------- the variant map */

test.describe("the variant redirect map", () => {
  /* Read by the `map "$legacy_dir$legacy_hu" …` block in both nginx.conf files of
     Web-Services. A wrong line there fails a request on the live server, not a
     build, so its invariants are held here. */
  function lines(): { key: string; value: string }[] {
    const text = readSiteFile(path.join("_nginx", "image-variant-redirects.map"));
    const out: { key: string; value: string }[] = [];
    for (const line of text.split("\n")) {
      if (!line.trim() || line.startsWith("#")) continue;
      const m = /^"((?:[^"\\]|\\.)*)" (\/\S+);$/.exec(line);
      expect(m, `not a map line nginx can read: ${line}`).toBeTruthy();
      out.push({ key: m![1].replace(/\\(["\\])/g, "$1"), value: m![2] });
    }
    return out;
  }

  test("every key is a directory plus _hu_<hex>, and no key is there twice", () => {
    const seen = new Set<string>();
    const bad: string[] = [];
    const all = lines();
    for (const { key } of all) {
      if (!/^\/(?:[^/]+\/)*_hu_[0-9a-f]+$/.test(key)) bad.push(`${key}: not <dir>/_hu_<hex>`);
      /* nginx compares map strings ignoring case. */
      if (seen.has(key.toLowerCase())) bad.push(`${key}: listed twice`);
      seen.add(key.toLowerCase());
    }
    expect(all.length, "the map is empty — is data/legacyImageVariants.yaml missing?").toBeGreaterThan(1000);
    expect(bad.slice(0, 20), bad.slice(0, 20).join("\n")).toEqual([]);
  });

  test("every target is a served file under a stable name", () => {
    /* Never a 301 → 404, and never a 301 to another `_hu_` name. */
    const served = servedPaths();
    const bad = lines()
      .filter(({ value }) => !served.has(decodeURIComponent(value)) || /_hu_/.test(value))
      .map(({ key, value }) => `${key} -> ${value}`);
    expect(bad.slice(0, 20), `${bad.length} target(s) not served\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
  });

  test("every key fits nginx's map_hash_bucket_size", () => {
    /* Same budget as the stem map: Web-Services sets map_hash_bucket_size 256. */
    const long = lines().filter(({ key }) => Buffer.byteLength(key, "utf8") > 200).map(({ key }) => key);
    expect(long, long.join("\n")).toEqual([]);
  });
});

/* ------------------------------------------------------- one contentUrl */

test.describe("one contentUrl per photo", () => {
  /* It used to be three: the original on the grids, the 1200px hero on the
     photo page's microdata, the 4000px variant in its JSON-LD and the image
     sitemap. Now it is the stable 4000px variant everywhere (§3). */
  for (const lang of LANGS) {
    test(`${lang}: photo page microdata = JSON-LD = image sitemap = grid`, () => {
      const photos = ((manifests()[lang] as any)?.photos ?? []) as any[];
      expect(photos.length, "no manifest").toBeGreaterThan(0);

      const sitemap = new Map<string, string>();
      for (const m of readSiteFile(path.join(lang, "sitemap.xml")).matchAll(/<url>([\s\S]*?)<\/url>/g)) {
        const loc = m[1].match(/<loc>([^<]+)<\/loc>/)?.[1];
        const img = m[1].match(/<image:loc>([^<]+)<\/image:loc>/)?.[1];
        if (loc && img) sitemap.set(decodeURIComponent(new URL(loc).pathname), img);
      }
      const grid = new Map<string, string>();
      for (const page of ["general", "archive"]) {
        const html = readSiteFile(path.join(lang, "gallery", page, "index.html"));
        for (const item of html.split('<a class="gallery-item"').slice(1)) {
          const id = item.match(/data-id="([^"]+)"/)?.[1];
          const url = item.match(/<meta itemprop="contentUrl" content="([^"]+)"/)?.[1];
          if (id && url) grid.set(id, url);
        }
      }

      const bad: string[] = [];
      for (const p of photos) {
        const rel = path.join(lang, "gallery", "photo", p.slug, "index.html");
        if (!fs.existsSync(sitePath(rel))) { bad.push(`${p.file}: no page`); continue; }
        const html = readSiteFile(rel);
        const micro = [...html.matchAll(/itemprop="contentUrl"[^>]*?(?:content|src)="([^"]+)"|(?:content|src)="([^"]+)"[^>]*?itemprop="contentUrl"/g)]
          .map((m) => m[1] ?? m[2]);
        const ld = jsonLdBlocks(html).map((b) => JSON.parse(b)).find((b) => b["@type"] === "ImageObject")?.contentUrl;
        const want = ld;
        const where = `${p.file} (/${lang}/gallery/photo/${p.slug}/)`;
        if (!want) { bad.push(`${where}: no JSON-LD contentUrl`); continue; }
        if (!/\/images\/gallery\/fit-4000x4000\//.test(want)) bad.push(`${where}: JSON-LD names ${want}, not the 4000px variant`);
        if (micro.length !== 1 || micro[0] !== want) bad.push(`${where}: microdata ${JSON.stringify(micro)} vs ${want}`);
        const sm = sitemap.get(urlOf(rel));
        if (sm !== want) bad.push(`${where}: sitemap ${sm} vs ${want}`);
        const g = grid.get(p.id);
        if (g !== undefined && g !== want) bad.push(`${where}: grid ${g} vs ${want}`);
      }
      expect(bad.slice(0, 20), `${bad.length} disagreement(s)\n${bad.slice(0, 20).join("\n")}`).toEqual([]);
    });
  }
});
