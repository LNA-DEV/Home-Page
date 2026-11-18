# Gear

`/gallery/gear/` — cameras and lenses, counted from the published photos alone. Design: `docs/concepts/gallery-gear.md`.

- **`data/gear.yaml` is the register**: `bodies` and `lenses`, each with a `slug` (the identity, and the anchor on the page), a display `name`, an optional chart `short`, and the EXIF spellings under `match:` (compared ignoring case). The EXIF strings cannot be the identity: **the Lumix G91 writes its lens only into the Panasonic maker note, which Hugo does not read**, so `.Exif.LensModel` is empty on all its photos — `lens_default:` on the body supplies its one and only lens. A teleconverter the camera appends to the lens name is a `match` entry `{text, teleconverter}`, counted with the lens. A `kind: drone | phone` body is its own lens.
- **`layouts/partials/gear-map.html`** (`partialCached`) validates the file and returns the lookup maps; **`collect-images.html`** resolves every photo through them in one `index` each and exposes `.BodySlug`, `.LensSlug`, `.Teleconverter`, the raw `.CameraExif` / `.LensExif`, and numbers for aggregation (`.FNumber`, `.ISOValue`, `.FocalMM`, `.Focal35` — the file's 35 mm equivalent, else focal length × the body's `crop`). **`.CameraModel` and `.LensModel` are the display names now** (`Nikon Z 8`, not `NIKON Z 8`), and fall back to the raw string only for gear with no record.
- **An EXIF camera or lens string with no record stops the build**, from `gear-index.html` (once per language, not in the hot collector). A photo with **no camera EXIF at all is not an error** — 92 today, the same 92 whose capture year is unknown — and is counted in the page's footnote, never guessed. Gear that took no published photo needs no record: **nothing is read from darktable**, deliberately (no shot counts, no ratings).
- **`layouts/partials/gear-index.html`** (`partialCached` per language) is the one aggregate the page reads: one unit per lens or drone/phone body, with counts (portfolio / gallery / archive — the archive counts, as in the dex), portfolio share, dex species, medians, the most used focal length of a zoom, 35 mm-equivalent bins and quarter counts. `gear-overview.html` renders it (theme `gear-home` in `list.html`), `gear-card.html` one lens, `gear-segments.html` the stacked bar, `gear-pct.html` a localised percentage.
- **The charts are HTML tables styled by `assets/css/extended/gear.css`** — no chart library, no JS: the data is fixed per build, and a table is readable without JavaScript and to a screen reader. PaperMod sets `table { display: block }`; `.gear table` resets it. Colours are one blue ramp validated as ordinal against white and PaperMod's dark `--entry`, flipped in dark mode — the `--gear-*` data tokens in `assets/css/core/theme-vars.css`.
- Photo pages, grid captions and the lightbox popup link camera and lens to `/gallery/gear/#<slug>` (`data-gear-url` on the `.gear-item` spans). The gallery home links the page as a text link beside *Archive*, not as a card; `index.json` adds it to the search like `/travel`. The section stubs set `outputs: [HTML]`.
- Tests: `tests/static/gear.spec.ts` — every card counts exactly the photo pages that link to it, cards + footnote = every photo, and a `lens_default` body never leaves a photo page without a lens row.

## Conventions

- A photo from a camera or lens `data/gear.yaml` does not know stops the build — add a record (or the new EXIF spelling to an existing one). Workflow below.

## A photo from a new camera or lens

`data/gear.yaml` is the register behind `/gallery/gear/` and the camera / lens
rows on every photo page (`docs/concepts/gallery-gear.md`). The build stops on
the first published photo whose EXIF `Model` or `LensModel` matches no record:

```
data/gear.yaml: photo "DSC_1234.jpg" was taken with the lens "NIKKOR Z 24-120mm f/4 S", which no lens record matches …
```

Add a record — `slug`, `name`, optional `short` for the chart rows, `type`
(`zoom | prime | macro | telephoto | wide`) and the exact EXIF string under
`match:` — or add the string to an existing record if it is another spelling
of a lens already listed (a teleconverter appended to the lens name is
`{text: …, teleconverter: <name>}`). A new body needs `match:` with its EXIF
`Model`, a `crop:` factor, and `kind: drone | phone` when it is its own lens.
`lens_default:` is only for a body that has never carried any other lens: it
fills in the lens when the file names none (the Lumix G91 writes its lens only
into the maker note, which Hugo cannot read).

Gear that took no published photo needs no record — nothing is read from
darktable. A photo with no camera EXIF at all is not an error: the gear page
counts it in its "without camera data" footnote and nothing is guessed for it.
Renaming a record's `name` changes the text on every photo page; its `slug` is
an anchor that photo pages and lightboxes link to, so keep it.
