# Design system: tokens, the ratchet, the styleguide

Design: `docs/concepts/design-system.md`. Every colour, spacing length, font
size, radius and shadow is a token in **`assets/css/core/theme-vars.css`**, and
every other stylesheet, script and template reads it with `var(--…)`.

## Working with it

- **Need a value that is not there?** Use the nearest token first — the scales
  are deliberately short (spacing 4·8·12·16·24·32·48·64, type 12·14·16·18·20·24·
  32·40·48). Only if none fits, add a token to `theme-vars.css`, with a one-line
  comment, and use it.
- **A colour is written once, as `light-dark(<light>, <dark>)`.** No
  `[data-theme="dark"]` block, no `prefers-color-scheme` block — `color-scheme`
  on the root picks the value, with and without JavaScript. A colour that is the
  same in both themes (text on a photo, the lightbox, IUCN) is a plain value.
  Check new text colours against the surfaces they sit on: 4.5:1, 3:1 for icons
  and bars. The styleguide's contrast samples are the place to add them.
- **The accent (Schiefer) is never the only cue.** In-text links keep their
  underline, a selected state keeps a border or a marker, and the accent is
  never drawn on a map — maps use the `--map-*` data colours.
- **A script that needs a colour** (Leaflet, a canvas) imports `tokenColor()`
  from `assets/js/token-color.js`. `getPropertyValue()` returns `light-dark()`
  unresolved. No fallback colour in the script.
- **Breakpoints:** 480, 640, 768, 900, 1100 — and 700 for the PhotoSwipe
  dialog only — in range syntax: `@media (width < 640px)`. A custom property
  cannot be used in a media query, so the test holds the list.
- **Widths:** a page's `<main>` width comes from its type in
  `layouts/partials/page-layout.html` (`text` or `wide`); a block that leaves the
  text column takes `l-wide`, `l-full` or `l-bleed`. Never add a second side
  padding inside `<main>` — the gutter is applied once.

```
npm run tokens:ratchet   # after moving a file onto tokens — rewrites tests/golden/css-literals.json
```

The ratchet (`tests/static/design-tokens.spec.ts`) counts literal values per file
and category and must **equal** the golden file: more is a regression to fix,
fewer means the golden is stale — rerun the command and commit the JSON with the
change. It is at zero; keep it there. What counts as a literal is written down in
`tests/support/css-literals.mjs` (1–2px hairlines, `0`, `%`, `vw`/`vh`/`ch` and
`var()` never do).

## How it is built

- **`assets/css/core/theme-vars.css` is the one tokens file** (it overrides PaperMod's file of that name, which PaperMod's head concatenates first, so every bundle — `main.scss` included — sees it): PaperMod's neutrals under their own names, the accent (**Schiefer**, `--accent` / `--accent-soft` / `--on-accent`), `--status-*`, `--on-image` / `--scrim*` for text over photos, `--viewer-*` for the always-dark lightbox and download dialog, the data colours (`--map-*`, `--trip-*`, `--gear-*`, `--iucn-*`, `--feed-*`), the spacing scale `--space-1…8` with role tokens (`--grid-gap`, `--card-pad`, `--section-gap` 48px, `--space-heading`; the image grids keep their pre-design-system gaps by the owner's decision: `--photo-gap` 8px, `--tile-gap` 14px, `--thumb-gap` 6px), widths (`--width-text` 720 / `--width-wide` 1060 / `--width-full` 1440 / `--width-narrow` 560), the type scale `--text-xs…5xl`, radii and four shadows.
- **Every colour token is `light-dark()`** and follows `color-scheme` on the root: the OS preference without JavaScript, PaperMod's `data-theme` with it. That is why `head.html`'s `<noscript>` no longer carries a dark palette and no stylesheet has a `[data-theme="dark"]` block of its own. An `@supports not (color: light-dark(…))` block keeps the neutrals and the accent for browsers older than 2024. Scripts resolve a token with `assets/js/token-color.js` (`getPropertyValue` returns `light-dark()` unresolved); the map scripts do, without fallbacks.
- **Schiefer carries almost no colour, so it is never the only cue**: in-text links keep their underline (`01-roles.css`; 1.22:1 against body text in dark mode), "Photographed" keeps its border and gains a ✓, active filters are filled, and maps never take the accent.
- **Layout**: one gutter, `--gap` (16px up to 768px, 24px above — `00-layout.css` overrides PaperMod's 14px), applied once by `.main`. `<main data-layout>` comes from **`layouts/partials/page-layout.html`, by page type, never by URL**: photo grids, dex, gear, models, photo pages and the photo tag pages are `wide` (the header's width, so the content edge is the logo's), everything else `text`. Blocks leave the text column with `l-wide` / `l-full` / `l-bleed` (edge to edge on a phone only); the story blocks keep their own centring (they also cap at the screen's height) but take `--bleed-wide` / `--bleed-full`. The header's `.nav` fills its track for that alignment. The gallery's old `max-width: 75%` and second `1.5rem` edge are gone.
- **`/en/styleguide/`** (unlisted, `noindex`, out of the sitemap and never in `tests/golden/published-urls.txt`; theme `styleguide`, gets `main.scss` but no lightbox) shows every colour token — read from the CSSOM by `assets/js/styleguide.js`, so it cannot fall behind — and the shared components in a light and a dark panel side by side.
- **Tests**: the ratchet (`tests/static/design-tokens.spec.ts`, golden `tests/golden/css-literals.json`), the contrast samples on the styleguide (`tests/e2e/design-system.spec.ts`) and the page edges at 375/768/1440/1920 (`tests/e2e/layout.spec.ts`).
