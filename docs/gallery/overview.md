# Gallery system (the load-bearing part of the site)

The gallery was recently restructured. The model is **one flat image folder + central YAML metadata + theme dispatch**. Understanding this is essential before touching any gallery template.

- **Image source of truth**: the local photo store, mounted to the `assets/images/gallery/` virtual path (via `module.mounts` in `config/_default/module.yaml` — see Build / Deploy). All photos sit flat there as global resources regardless of which view they appear in; templates address them as `images/gallery/*`, unaffected by where the files physically live.
- **Metadata source of truth**: `data/gallery.yaml` — one entry per image with `id` (UUID, stable across renames), `src` (current filename), `category`, `section` (`general` | `archive`), `project` (slug, list of slugs, or empty — a photo may sit in several albums, e.g. a thematic one and a single-session one), `portfolio` (bool), `species`, `tags`, `alt`, `title`, `description`, `license`, `artist`. The `src` field must exactly match the image filename. The `id` is the **stable identifier** used by deep links, the likes API, and `featured_image:` references — when a filename changes, only `src` is updated; `id` stays. Three of those fields have a shape worth knowing:
  - **`title`, `alt`, `description` are per-language.** Each is either a bare string (which means English) or an `{en, de, sv}` map, and every read falls back to `en` — the same rule the dex applies to species prose. `gallery-meta.html` normalises the string form into a map so a template only ever meets one shape; `collect-images.html` does the language pick. **`alt` and `description` are different things**: `alt` is the short account of what is visible that goes on the `<img>`, `description` is the prose the photo page prints, and `description` falls back to `alt` when absent.
  - **`license` is a key into `data/licenseMap.yaml`** (`cc-by-sa-4.0`, `all-rights-reserved`), not a display string. The English display strings the entries used to hold were rewritten to keys by the one-time import (`docs/concepts/gallery-metadata-import.md`, **done**), and the `aliases` lists that resolved them went with it — a `license:` that is not a key is now a build error. The map holds `url`, optional per-language `url_by_lang` (CC's translated deeds), a `label` and the `terms` sentence embedded into the served files.
  - **`tags` lives here and nowhere else.** Until 2026-09-26 the build also read the file's `dc:subject` and showed the union; the one-time import (`scripts/gallery-import-tags.py`, **done**, `docs/concepts/gallery-metadata-yaml-only.md` §3) copied those 4,422 tags in, keeping darktable's camelCase spelling (`bavarianAlps`), and the file read and `data/galleryTagIgnore.yaml` went. `gallery-meta.html` normalises `tags` to `.tags` (stored spelling, de-duplicated ignoring case) and `.tagsLower`. **The build now reads nothing editorial out of a file at all** — only the technical EXIF — so a darktable re-export or re-tag cannot change what the site says about a photo. The filename is only a pointer (`src`); nothing a reader sees is derived from it. Every tag of a non-archive photo also gets a page — see `docs/gallery/tags.md`.
- **Two cached partials underpin everything else**:
  - `layouts/partials/gallery-images.html` — returns all gallery image resources via `resources.Match "images/gallery/*"`, **each copied with `resources.Copy` to `images/gallery/<file>`**, the name the site publishes it under (see *Served image names* in `docs/gallery/images.md`); a file with no entry in `data/gallery.yaml` is left out. Global resources are inherently language-independent. Always call via `partialCached`. Note: `.Name` on these resources returns a full path with a **leading slash** (`/images/gallery/photo.jpg`) — use `path.Base` when looking up by bare filename — and after the copy it **still returns the store filename**, not the published one, so every `bySrc` lookup and every `GetMatch "images/gallery/<src>"` works unchanged; only `.RelPermalink` / `.Permalink` carry the new name. Match patterns are matched with or without the leading slash, so `resources.Match "images/gallery/*"` is unaffected.
  - `layouts/partials/gallery-meta.html` — returns `{ bySrc, byId }`, two dicts sharing the same metadata entries. `bySrc` is keyed by bare filename (use `path.Base` on resource `.Name` to match); `byId` is for UUID lookups (`featured_image`, etc.). Each entry gains a derived **`.projects`** key — `project:` normalised to a slice — and that is the only field any template should read for album membership (`in $meta.projects $slug`); comparing `.project` directly breaks the list form, and `in` on the raw string would match a substring (`eagles` against `eagles-2026`). It also normalises `title`, `alt` and `description` **in place** from string-or-map to an `{en, de, sv}` map — never print one of those three straight off an entry, you would get a Go map literal; the prose itself stays unresolved because `head.html`, `resolve-featured-image.html` and `feed/list.html` all want the raw maps. **`.slug` and `.slugAliases`, by contrast, ARE language-dependent** — see `docs/gallery/photo-pages.md`. That is safe even though every caller passes `partialCached` with no variant key: **Hugo scopes the partial cache per language Site**, so the partial runs once per language and each build sees its own value (verified on 0.166; the context argument contributes nothing to the key, only variants do). An earlier version of `CLAUDE.md` claimed the opposite and used it to argue the return value had to stay language-neutral — it does not. It also derives the language-neutral **`.fileSlug` / `.file`** (the served file name, *Served image names* in `docs/gallery/images.md`) and **`.tags` / `.tagsLower`**. Hard-fails the build if any entry lacks an `id` — run `scripts/add-gallery-ids.py` to populate one — or lacks a title in both the current language and English (a pinned `slug:` does not excuse it any more: there is no filename fallback), or if two photos would be published under the same file name. Always call via `partialCached`.
- **`layouts/partials/collect-images.html`** is the single entry point for collecting+filtering images. It merges the YAML's editorial fields with the file's technical EXIF/XMP, picks `.Title` / `.Alt` / `.Description` for `site.Language.Lang` with an English fallback, resolves the license through `layouts/partials/license-index.html` (a missing `license:`, or one that is not a key, is a hard error naming the photo) and the artist (data → `site.Params.author.name`), and takes the tags from the YAML alone: `.Tags` is the lowercased list (photo page, RSS, schema keywords, the similarity scorer, the embedded files), `.Keywords` the stored spelling the lightbox popup prints. There is no `.DisplayTitle` any more — every photo has a `.Title` — and `.File` is the served file name. Filter keys: `category`, `section`, `portfolio`, `project`, `species`, `id`, `excludeArchive` (default true). Each returned item exposes `.Id` (UUID from YAML) — use it as the stable identifier in any new template — plus `.LicenseKey` / `.LicenseText` (the resolved label) / `.LicenseUrl` / `.LicenseTerms`. It is **not** `partialCached` at its call sites and runs once per dex species page, so the per-photo work in it is hot: the language pick is inlined rather than delegated to a partial, and the tag normalisation lives in the cached `gallery-meta.html`, for that reason. It also exposes `.Software` from EXIF (the editing program and version, e.g. `darktable 5.0.1`), with a filter that drops bare version strings: cameras write their own **firmware** version into the same EXIF tag, and 157 of the 633 photos say only `Ver.1.2`, which is not editing software. Use this — do not iterate the bundle directly.
- **`layouts/partials/resolve-featured-image.html`** resolves a `featured_image:` front-matter value (UUID, with legacy filename fallback) to a bundle resource. Used by `get-gallery.html` and `templates/_funcs/get-page-images.html`.
- **Theme dispatch**: gallery pages select a renderer through their front-matter `params.theme`, branched in `layouts/_default/list.html` and `layouts/_default/single.html`. Themes:
  - `gallery-home` → `content/gallery/_index.*` — hero portfolio + nav cards to Projects/General + Archive link.
  - `gallery-general-home` → `content/gallery/general/_index.*` — all non-archive images with category filter bubbles (`gallery-filter-bubbles.html`, JS-only client-side filtering on `data-category`).
  - `gallery-archive` → archive view (forces `section=archive` filter).
  - `gallery-portfolio` → curated subset (`portfolio: true`).
  - `gallery-projects-list` → index of project mini-albums.
  - `gallery-project` → single project album (filters by `project_slug`). An album is kept **out of the projects index** with Hugo build options in its front matter — `build: {list: never, render: always}` (the key is `build`, not the removed `_build`), which also drops it from the sitemap and the section RSS while still rendering it at its URL; pair it with `params.robotsNoIndex: true` for an unlisted album. Note this hides the *album*, not its photos — `/gallery/general/` shows every non-archive photo whatever its project.
  - `gallery-page` / `gallery-page-hidden` → generic gallery single pages.
- **Lightbox**: PhotoSwipe, wired up in `assets/js/lightbox.js`; thumbnail and full-size images are the `fit 600x600` and `fit 4000x4000` variants `gallery.html` gets from `image-variant.html` (*Processed images* in `docs/gallery/images.md`).

## Conventions

- New gallery images: drop the file into the photo store (the gallery mount source), then add a matching entry to `data/gallery.yaml` **including a UUID `id`** (the build will hard-fail without one — `scripts/add-gallery-ids.py` populates missing ids in bulk).
- Renaming an existing gallery image: rename the file in the photo store (the gallery mount source) and update only the matching `src:` in `data/gallery.yaml`. Do not touch `id` — deep links, the likes API key, and any `featured_image:` referencing it all use the id. Nothing a visitor sees changes: the served file name comes from the English title, not from `src`.
- New license values must be added to `data/licenseMap.yaml` — as a **key** with `url`, `label` and `terms` — or the build will `errorf`. Write `license: <key>` in `data/gallery.yaml`, not the display string.
- A new photo's entry is best created with `python3 scripts/sync-gallery.py`, which appends a stub with empty `title` / `alt` slots in all three languages and `tags: []`, and pre-fills only `license` / `artist` from what darktable's preset wrote into the file (once, at stub time). **Title, alt text, description and tags are typed in `data/gallery.yaml`, never in darktable** — whatever the file carries there is ignored, and the export filename can be anything (set darktable's conflict handling to "create unique filename", never "overwrite": camera counters repeat).

## Adding gallery photos, and what happens to them on deploy

Two scripts, at opposite ends of a photo's life: `scripts/sync-gallery.py`
below and `scripts/gallery-embed-metadata.py` in `docs/gallery/images.md`. Both are standard-library only
(no `pip install`) and both edit `data/gallery.yaml` as text, so lines that are
not part of the change stay byte-identical. Neither ever writes to the photo
store — that folder is darktable's export target and a Nextcloud share.

### `scripts/sync-gallery.py` — the photo enters the data file

Run it after exporting new photos into the photo store (the gallery mount
`source` in `config/_default/module.yaml`; the script reads that file, so the two
never drift):

```bash
python3 scripts/sync-gallery.py --dry-run   # look first
python3 scripts/sync-gallery.py
```

- A `src:` in the YAML with no file on disk is an **error**, not a fix: it usually
  means a rename to make by hand. The script reports every one and writes nothing.
- A file on disk with no entry gets a stub appended, with a fresh UUID `id`,
  **empty `title` and `alt` slots in all three languages**, `tags: []`, and only
  `license` / `artist` pre-filled from darktable's preset in the JPEG
  (`scripts/gallery_xmp.py`, one exiftool process for all new files; without
  exiftool those two are simply left out).
- **Title, alt text, description and tags are typed in `data/gallery.yaml`, never
  in darktable** (`docs/concepts/gallery-metadata-yaml-only.md`). Whatever the file
  carries in those fields is ignored, and the export filename can be anything —
  the site publishes the photo under its English title's slug. Set darktable's
  export conflict handling to "create unique filename", never "overwrite": camera
  counters like `DSC_0001` repeat.
- **The build stops on the new photo until `title.en` is written** — that is the
  reminder. An empty alt is a backlog item, not an error.
- `license` is written as a **key** (`cc-by-sa-4.0`), mapped from darktable's
  display string through `data/licenseMap.yaml`.

Left for a human: the title (all three languages), the alt text, the tags,
`category` (the stub says `others`), `section`, `project`, `portfolio`, `species`.

Every tag of a non-archive photo becomes a page at `/<lang>/gallery/tags/<tag>/`
(noindexed, lowercased, no threshold — `docs/concepts/tag-pages.md`), so a new
tag is a new page. Never tag a person by name: the build stops on a tag that
spells a model's slug or name — credit people with `model:` (see *Adding a
model* in `docs/gallery/models.md`).

### Reviewing a new photo's metadata

Suggestions for a new photo's title, alt text and tags go to the owner as a change
list, not as a dump of the whole entry. Once the owner gives the go, write
**every** agreed change — title, alt text and tags together; the list is only how
the suggestions are reviewed, not a sign the owner will type the tags in. Then
update the golden list: `npx playwright test --project build` and
`npm run golden:update` (the full suite only when asked).

### `scripts/gallery-import-xmp.py` — done, do not re-run

The one-time migration that made "the YAML is the truth" literally true. It is
kept for the record; **it has run and there is nothing left for it to do.** Before
it, 282 photos had their licence, 281 their alt text and 21 their title only inside
the exported JPEG, and the build read them back through fallbacks — so a darktable
re-export could change what the site said about a photo with no diff in git.

What it did, in one pass over `data/gallery.yaml` (`docs/concepts/gallery-metadata-import.md`):

| | |
|---|---:|
| licence display strings rewritten to keys | 366 |
| `license` filled from the file | 282 |
| `alt` filled from the file | 281 |
| `title` filled from the file | 22 |
| `description` added from the file | 7 |

`artist` was deliberately **not** imported: all 287 file values are `Lukas Nagel`,
which is `site.Params.author.name` and already the fallback (`--artist` imports
them if uniformity is ever preferred). Tags were not imported by this script; the
second one-time import below did that.

It removed the fallbacks with it, so from here on:

- A photo with no `license:` in `data/gallery.yaml` is a **hard build error** naming
  the file. There is no `Exif.Copyright` to fall back to any more.
- `license:` must be a **key** of `data/licenseMap.yaml`. The old display strings
  were registered there as `aliases`; those lists are now empty.
- `alt` comes from the YAML alone. 60 photos still have none anywhere — that is an
  editorial backlog, not a defect, and the script lists them.
- `layouts/partials/image-alt.html` still exists, but only `sitemap.xml` uses it,
  for page-bundle images that are not gallery photos.

Running it again prints `Nothing to import` and changes nothing, which is the
intended way to confirm the state. It refuses to run at all if `data/gallery.yaml`
and the photo store are out of step, or if any licence value is unknown.

### `scripts/gallery-import-tags.py` and `scripts/gallery-cache-link.py` — done, do not re-run

The two one-time steps of `docs/concepts/gallery-metadata-yaml-only.md`, run on
2026-09-26 and kept for the record. A second run of either prints that there is
nothing to do.

- **`gallery-import-tags.py`** moved the tags the build used to read out of the
  files into `data/gallery.yaml`: 4,422 tags on 289 entries, in darktable's
  camelCase spelling (`bavarianAlps`). The set and order came from Hugo's own
  manifest, so the site showed exactly the same tags before and after — all three
  `gallery-metadata.json` stayed byte-identical, before the template stopped
  reading the files and after. Three German file tags (`Eidechse`,
  `Eidechsenkampf`, `Schnecke`) that duplicated English YAML tags were then
  deleted by hand. Tags are now typed in the YAML only.
- **`gallery-cache-link.py`** kept the image cache warm when the build started
  publishing under slug names: it hardlinked the 5,819 cached variants
  `<store stem>_hu_<hash>.<ext>` to `<file slug>_hu_<hash>.<ext>` (the hash does not
  depend on the name), so the switch reprocessed nothing. It only ever adds links.
  The hash does depend on the Hugo release and the `imaging:` block, though, so
  since 2026-10-14 no URL carries it: every variant is published as
  `<spec>/<file slug>.<ext>` (`docs/gallery/images.md`).
