/* Everything the static layer reads, parsed once per worker.
 *
 * Two inputs, and they are deliberately separate: the *data files* in the repo
 * (the source of truth an editor types into) and the *built site* under
 * SITE_DIR (what the outside world gets). Almost every L2 check is an assertion
 * that those two agree, so nothing here may derive one from the other. */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parse as parseYaml } from "yaml";

export const REPO = path.resolve(fileURLToPath(new URL("../..", import.meta.url)));
export const SITE_DIR = path.resolve(REPO, process.env.SITE_DIR ?? ".test-site");
export const SITE_BASE = (process.env.SITE_BASE ?? "http://localhost:1414").replace(/\/$/, "");
export const LANGS = ["en", "de", "sv"] as const;
export type Lang = (typeof LANGS)[number];

/* The production base URL, whatever SITE_BASE happens to be — used by the leak
   checks, which have to know what "not localhost" looks like. */
export const PRODUCTION_BASE = "https://lna-dev.net";

function memo<T>(fn: () => T): () => T {
  let done = false;
  let value: T;
  return () => {
    if (!done) {
      value = fn();
      done = true;
    }
    return value;
  };
}

function readYaml(rel: string): any {
  return parseYaml(fs.readFileSync(path.join(REPO, rel), "utf8"));
}

/* ------------------------------------------------------------------ data */

export type GalleryEntry = {
  id?: string;
  src?: string;
  category?: string;
  section?: string;
  project?: string | string[];
  model?: string | string[];
  species?: string;
  portfolio?: boolean;
  license?: string;
  artist?: string;
  title?: string | Record<string, string>;
  alt?: string | Record<string, string>;
  description?: string | Record<string, string>;
  slug?: string;
  slugAliases?: string[];
  tags?: string[];
};

export const gallery = memo<GalleryEntry[]>(() => readYaml("data/gallery.yaml").images ?? []);
export const dex = memo<any[]>(() => readYaml("data/dex.yaml").species ?? []);
export const models = memo<any[]>(() => readYaml("data/models.yaml").models ?? []);
export const licenseMap = memo<Record<string, any>>(() => readYaml("data/licenseMap.yaml"));

/* The game library: one entry per COPY (data/gaming.yaml), the per-game editorial
   records (data/gamePages.yaml), and the titles hidden from every view. */
export const gaming = memo<any[]>(() => readYaml("data/gaming.yaml") ?? []);
export const gamePages = memo<any[]>(() => readYaml("data/gamePages.yaml")?.games ?? []);
export const gamingIgnore = memo<Set<string>>(
  () => new Set(((readYaml("data/gamingIgnore.yaml")?.titles ?? []) as any[]).map((t) => String(t).trim().toLowerCase())),
);

/** The slugs that get a page: every copy not hidden by gamingIgnore.yaml. */
export const shownGameSlugs = memo<string[]>(() => [
  ...new Set(gaming().filter((c) => !gamingIgnore().has(String(c.title).trim().toLowerCase())).map((c) => String(c.slug))),
]);

/* The site config. `params.author` and `params.schema.sameAs` define the owner as
   one schema.org Person; the structured-data tests assert the pages against it. */
export const hugoConfig = memo<any>(() => readYaml("hugo.yaml"));

/** The YAML front matter of a content file, parsed ("content/x/index.en.md"). */
export function frontMatter(rel: string): any {
  const text = fs.readFileSync(path.join(REPO, rel), "utf8");
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  return m ? parseYaml(m[1]) : {};
}

export const i18nIds = memo<Record<Lang, Set<string>>>(() => {
  const out = {} as Record<Lang, Set<string>>;
  for (const lang of LANGS) {
    const entries: any[] = readYaml(`i18n/${lang}.yaml`) ?? [];
    out[lang] = new Set(entries.map((e) => e?.id).filter(Boolean));
  }
  return out;
});

/* `project:` and `model:` are string-or-list in the YAML and normalised to a
   slice by gallery-meta.html. Every consumer here reads the normalised form, for
   the reason CLAUDE.md gives: `in` on the raw string matches substrings, so
   `eagles` would match `eagles-2026`. */
export function asList(v: string | string[] | undefined | null): string[] {
  if (!v) return [];
  const list = Array.isArray(v) ? v : [v];
  return list.map((s) => String(s).trim()).filter(Boolean);
}

export const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/* ------------------------------------------------------------ built site */

export function sitePath(...parts: string[]): string {
  return path.join(SITE_DIR, ...parts);
}

export const siteExists = memo(() => fs.existsSync(sitePath("index.html")) || fs.existsSync(sitePath("en", "index.html")));

/** Every file under SITE_DIR whose name ends in one of `exts`, as repo-relative
 *  site paths ("en/gallery/index.html"). Walked once per worker. */
function walk(
  dir: string,
  opts: { exts?: string[]; skipDirs?: Set<string> },
  acc: string[] = [],
  base = dir,
): string[] {
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return acc;
  }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (opts.skipDirs?.has(e.name)) continue;
      walk(full, opts, acc, base);
    } else if (!opts.exts || opts.exts.some((x) => e.name.endsWith(x))) {
      acc.push(path.relative(base, full));
    }
  }
  return acc;
}

/* The pages that get read. /images/ is 8 GB of the 8 GB and /packages/ is
   vendored Leaflet — no HTML of ours lives in either, and opening them would
   turn a two-second layer into a minute. */
const HEAVY = new Set(["images", "packages"]);

export const htmlFiles = memo<string[]>(() => walk(SITE_DIR, { exts: [".html"], skipDirs: HEAVY }).sort());
export const xmlFiles = memo<string[]>(() => walk(SITE_DIR, { exts: [".xml"], skipDirs: HEAVY }).sort());
/* Every text file a browser might run or read, /packages/ included — the
   vendored libraries are exactly where a third-party host would hide. */
export const textFiles = memo<string[]>(() =>
  walk(SITE_DIR, {
    exts: [".html", ".js", ".mjs", ".css", ".json", ".geojson", ".xml", ".txt", ".webmanifest", ".map"],
    skipDirs: new Set(["images"]),
  }).sort(),
);

export function readSiteFile(rel: string): string {
  return fs.readFileSync(sitePath(rel), "utf8");
}

/** Iterate every built HTML page without holding 96 MB in memory at once. */
export function* eachHtml(): Generator<{ file: string; html: string }> {
  for (const file of htmlFiles()) {
    yield { file, html: readSiteFile(file) };
  }
}

/** The URL path a built file is served at: "en/gallery/index.html" → "/en/gallery/". */
export function urlOf(file: string): string {
  const p = "/" + file.split(path.sep).join("/");
  return p.endsWith("/index.html") ? p.slice(0, -"index.html".length) : p;
}

/** Does a URL path exist in the built site, as a page or as a plain file? */
/* Every path the static server would answer — images and vendored packages
   included, since half the broken-link candidates are exactly those. This walk
   only reads directory entries, never file contents. */
export const servedPaths = memo<Set<string>>(() => {
  const set = new Set<string>();
  for (const f of walk(SITE_DIR, {})) {
    const u = urlOf(f);
    set.add(u);
    if (u.endsWith("/")) set.add(u.slice(0, -1));
  }
  return set;
});

/* The three per-language manifests Hugo resolves for the metadata embedding
   step. They are the one place the *build's* view of a photo's metadata is
   written down, which makes them the natural thing to assert the pages against. */
export type Manifest = { count?: number; images?: any[] };
export const manifests = memo<Record<Lang, Manifest | null>>(() => {
  const out = {} as Record<Lang, Manifest | null>;
  for (const lang of LANGS) {
    const p = sitePath(lang, "gallery-metadata.json");
    out[lang] = fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : null;
  }
  return out;
});

/* --------------------------------------------------------------- helpers */

/** Every value of an attribute across one HTML string. */
export function attrValues(html: string, attr: string): string[] {
  const re = new RegExp(`\\b${attr}\\s*=\\s*"([^"]*)"`, "gi");
  return [...html.matchAll(re)].map((m) => m[1]);
}

/** The contents of every <script type="application/ld+json"> block. */
export function jsonLdBlocks(html: string): string[] {
  const re = /<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  return [...html.matchAll(re)].map((m) => m[1]);
}

/** The URL prefix of every taxonomy's pages, language segment excluded: the
 *  plural name ("/tags/"), or its `permalinks.taxonomy` override
 *  ("/gallery/tags/"). Hugo's two defaults when hugo.yaml declares none. */
export const taxonomyPrefixes = memo<string[]>(() => {
  const cfg = hugoConfig() ?? {};
  const plurals = Object.values(cfg.taxonomies ?? { tag: "tags", category: "categories" }) as string[];
  return plurals.map((pl) => {
    const own = cfg.permalinks?.taxonomy?.[pl];
    return own ? `/${String(own).replace(/^\/|\/$/g, "")}/` : `/${pl}/`;
  });
});

/** Is this URL path ("/en/tags/privacy/") a taxonomy or term page? */
export function isTaxonomyUrl(u: string): boolean {
  const rest = u.replace(/^\/[a-z]{2}(?=\/)/, "");
  return taxonomyPrefixes().some((p) => rest.startsWith(p));
}

/** The content of the page's meta robots, whitespace removed ("noindex,follow"). */
export function metaRobots(html: string): string {
  return (html.match(/<meta name="robots" content="([^"]*)"/i)?.[1] ?? "").replace(/\s/g, "");
}

/** The page's theme param, as the body/article markup exposes it — falls back to
 *  a path heuristic, because not every theme writes a marker. */
export function pageKind(file: string): string {
  const u = urlOf(file);
  /* Before the /gallery/ rules: photo tags live at /gallery/tags/. */
  if (isTaxonomyUrl(u)) return "taxonomy";
  if (/\/gallery\/photo\//.test(u)) return "gallery-photo";
  if (/\/gallery\/dex\/[^/]+\//.test(u)) return "dex-species";
  if (/\/gallery\/models\/[^/]+\//.test(u)) return "model";
  if (/\/gallery\//.test(u)) return "gallery-list";
  /* The About page — params.author.page — renders as a ProfilePage. */
  const about = String(hugoConfig()?.params?.author?.page ?? "").replace(/^\/|\/$/g, "");
  if (about && u === `/${u.split("/")[1]}/${about}/`) return "profile";
  /* /posts/page/2/ and /posts/<section>/page/2/ are paginator pages of a list,
     not articles — they carry a breadcrumb and nothing else, correctly. */
  if (/\/page\/\d+\//.test(u)) return "other";
  if (/\/posts\/[^/]+\/[^/]+\//.test(u)) return "post";
  return "other";
}

/* ------------------------------------------------------- project stories */

/* Every gallery project page, from its content file (docs/concepts/
   gallery-project-stories.md): which layout it asked for, which project's photos
   it shows, and where it is built. A story page is found by its layout, never by
   name, so the tests keep working once the demo projects are deleted. */
export type ProjectPage = {
  dir: string;
  lang: Lang;
  /** "content/gallery/projects/<dir>/index.<lang>.md" */
  source: string;
  /** "/<lang>/gallery/projects/<dir>/" */
  url: string;
  /** "<lang>/gallery/projects/<dir>/index.html" */
  file: string;
  layout: string;
  slug: string;
  featured: string;
  areas: string[];
  weight: number;
  /** false for an album with build.list: never — reachable, but in no list. */
  listed: boolean;
};

export const projectPages = memo<ProjectPage[]>(() => {
  const root = path.join(REPO, "content", "gallery", "projects");
  const out: ProjectPage[] = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    for (const lang of LANGS) {
      const source = path.join("content", "gallery", "projects", entry.name, `index.${lang}.md`);
      if (!fs.existsSync(path.join(REPO, source))) continue;
      const fm = frontMatter(source);
      const params = fm.params ?? {};
      if (params.theme !== "gallery-project") continue;
      out.push({
        dir: entry.name,
        lang,
        source,
        url: `/${lang}/gallery/projects/${entry.name}/`,
        file: path.join(lang, "gallery", "projects", entry.name, "index.html"),
        layout: String(params.project_layout ?? "grid"),
        slug: String(params.project_slug ?? ""),
        featured: String(params.featured_image ?? ""),
        areas: asList(params.areas),
        weight: Number(fm.weight ?? 0),
        listed: fm.build?.list !== "never",
      });
    }
  }
  return out.sort((a, b) => a.url.localeCompare(b.url));
});

/** The project pages whose project_layout is essay or journal. */
export const storyPages = memo<ProjectPage[]>(() => projectPages().filter((p) => ["essay", "journal"].includes(p.layout)));

/** The photos a project page shows: the grid's, archive excluded. */
export function projectPhotoIds(slug: string): string[] {
  return gallery()
    .filter((e) => asList(e.project).includes(slug) && e.section !== "archive")
    .map((e) => String(e.id));
}

export const galleryAreas = memo<any[]>(() => readYaml("data/galleryAreas.yaml")?.areas ?? []);
