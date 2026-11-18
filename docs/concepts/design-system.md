# Concept: one design system — colour, spacing, edges, type

**Status:** proposal, 2026-11-18. Nothing built. Written up from a discussion with the owner the same day: the direction is agreed, and all seven open questions were answered the same day (*Decisions*). The accent is **Schiefer** (slate), chosen on the decision aid (§8). Next is step 2 of §11.
**Read against:** the working tree of 2026-11-18 (`24d9c58`), PaperMod at `v0.0.0-20260125152547-3bb0ca281fd1`. Every count below comes from `grep` over `assets/css/` (30 files in `extended/`, `core/theme-vars.css`, `main.scss`, `_styles.scss`). The edge distances in §5.1 are computed from the CSS, not measured in a browser; step 0 measures them.

The site looks assembled rather than designed. The dex is green, the project stories amber, gear blue, the software projects Tailwind. The reading list is written for a dark page that light mode does not have. A photo grid on a phone sits 38px from the screen edge, while the logo above it sits at 14px. None of this is a single mistake. PaperMod ships greys and nothing else: no accent, no spacing scale, no widths beyond the text column and the header. So every feature concept since has had to invent its own, and most did it carefully: gear's ramp is validated, the story accent documents its contrast ratios. Each decision is sound locally. Nothing holds them together, so every new feature adds another.

This concept adds the missing layer:

- **one tokens file** that every stylesheet draws from;
- **rules** for what may vary (data colours) and what may not (everything else);
- **fixed widths and one edge**;
- **tests that make drift fail the build**, the way `image-urls.spec.ts` keeps `.Resize` out of `layouts/`.

It unifies; it does not redesign. No page changes its structure. The only deliberate visible changes are the accent, the gallery's width, and its edge on a phone.

## Decisions

### Settled (direction agreed 2026-11-18)

| | |
|---|---|
| Scope | Colour, spacing, page edges and widths, breakpoints, type sizes, radii, shadows. Fonts, icons and motion are out (§10) |
| Source of truth | One file of CSS custom properties: `assets/css/core/theme-vars.css`, which is already the repo's override of PaperMod's palette (§2) |
| PaperMod | Its variables stay and become the neutral tokens. Its own CSS is not rewritten; only what PaperMod lacks is added |
| UI vs data colours | Two classes with different rules. UI colours are a few shared tokens. Data colours (gear charts, trip modes, map layers, IUCN status) may be many, but are defined centrally, documented and contrast-checked (§3.3) |
| Dark mode | Every colour token is defined once, with `light-dark()`, and follows `color-scheme`, with and without JavaScript (§3.4) |
| Spacing | A scale on a 4px base, in rem, plus role tokens such as `--section-gap` and `--card-pad` (§4) |
| Page edge | One `--gutter`, applied once at the outermost container. The gallery's second `1.5rem` gutter goes (§5) |
| Widths | Four fixed widths: text, wide, full, narrow. The gallery's `max-width: 75%` goes (§5) |
| Layout selection | By page type (`params.theme`), never by URL (§5.3) |
| Breakpoints | A fixed set, written in range syntax (§6) |
| Enforcement | Static ratchet tests on literals, a geometry test, a contrast test (§9) |
| Reference | An unlisted styleguide page that shows every token and component in both themes (§8) |
| Migration | Foundations first (tokens, then layout), then one pass per area that covers every category at once (§11) |

### Settled by the owner (2026-11-18)

| | |
|---|---|
| Accent | **One accent, site-wide.** No colour per area. Colour that carries meaning stays a data colour (§3.3). Rejected: a colour per area with matched lightness and chroma |
| Density | **Medium:** `--section-gap` 48px, `--photo-gap` 24px (§4.2). Rejected: airy (64 / 24) and compact (48 / 16) |
| Gallery width | **Wide, 1060px**, the header's width, so every grid edge lines up with logo and menu. Full width (1440px) only for story blocks and the travel page (§5.2). At a 1440px viewport the grid gets slightly wider than today (1060 vs 984px), at 1920px narrower (1060 vs 1344px). Rejected: full width for grids |
| Photos on a phone | **Grids keep the gutter** (16px), like text and header. Only the story hero and the lightbox go edge to edge (§5.2). Rejected: everything edge to edge, and a gutter around the story hero too |
| Third-party brand colours | **Brought into the palette.** Rating stars and achievement bars take the accent; Steam blue and IMDb yellow go |
| IUCN badges | **Official Red List colours**, as filled badges, each with whichever text colour reaches 4.5:1 on its fill: yellow and yellow-green fail as text on white (§3.3). Rejected: the site's status colours |
| Accent colour | **Schiefer (slate): `#5b6b7d` light, `#a1b4c8` dark**, a blue-grey of very low chroma (OKLCH C ≈ 0.035). The photos carry the colour; the interface stays almost grey. Chosen on the decision aid (§8) from eleven candidates, then four finalists (Gletscher, Flieder, Heide, Schiefer) shown on eight page types. Its consequences are in §3.2. Rejected: Alpenrose, Rost, Bernstein, Moos, Waldgrün, Gletscher, Petrol, Enzian, Flieder, Heide. Rost, Moos and Waldgrün were ruled out anyway, because their hue sits on a fixed IUCN colour |

No decisions are open.

---

## 1. What the CSS says today

### Colour

PaperMod defines `--theme`, `--entry`, `--primary`, `--secondary`, `--tertiary`, `--content`, `--border` and `--code-bg`; the repo adds `--card`. These are greys only. Every accent on the site was invented by the feature that needed it:

| Area | Colours | Where |
|---|---|---|
| Dex | Accent green `#2f7d5b` / `#6ecfa0`. Map land, water and sighting colours. Difficulty and IUCN badges use a third set (`#4c9a6a`, `#c98a2e`, `#c2553f`) with the same values in both themes | `dex.css`; fallbacks in `dex-map.js` |
| Project stories | Amber `#8a5a00` / `#d8a657` as `--accent`: a site-wide name defined in a feature file | `gallery-story.css` |
| Gear | A blue ramp of eight tokens | `gear.css` |
| Travel | Car blue, flight orange, train green, "here" orange | `travel.css`; fallbacks in `travel.js`; hard-coded in `route-map.js` |
| Software projects | Tailwind colours (`#16a34a`, `#d97706`, `#dc2626`, `#4f46e5`) with dark variants | `project.css` |
| Alerts | GitHub's palette | `alert.css` |
| Activity feed | Flat UI colours (`#e67e22`, `#f1c40f`, `#3498db`) | `activity.css` |
| Newsletter | Its own error and success colours (`#e05252`, `#4aa96c`) | `newsletter.css` |
| Gaming, reading | Steam blue `#66c0f4`, IMDb yellow `#f5c518` | `gamingList.css`, `gamePage.css`, `readingList.css` |
| Likes | `#ef4444`, defined twice | `main.scss`, `_styles.scss` |
| Text on photos | Five versions of overlay plus light text: `rgba(0,0,0,.55)` with `rgb(235,235,236)`; `.7` with `rgb(218,218,219)`; `.55` / `.6` with `#fff` / `#f2f2f2`; `.72` / `.9`; `rgba(18,18,20,.78)` with `#e4e4e5` | models, gallery nav, dex, gaming, stories |

In numbers:

- About 250 colour literals in 18 of the 32 stylesheets, counting the local token definitions. `main.scss` alone has 53, and not one variable.
- Status colours exist four times: alerts, software projects, newsletter, dex badges.
- One "warning orange" exists five times: `#d97706`, `#c98a2e`, `#ba7517`, `#d8a657`, `#f5a524`.
- Two map scripts read their colours from CSS with a hard-coded fallback, and the fallbacks have already drifted: `dex-map.js` falls back to land `#d9d4c7`, while the CSS says `#e8e4d8`.

**Two bugs this inventory turned up:**

- **The reading list is unreadable in light mode.** `readingList.css` and `recentReading.css` set their text to `#fff`, `#eee`, `#ddd`, `#ccc` and `#aaa`, with no background of their own: they were written for a dark page. On light mode's white, that gives 1:1 for titles, 1.4:1 for notes and 2.3:1 for meta lines; WCAG asks for 4.5:1. It affects `/reading-list/` and the recent-reading row on the About page. This is computed from the CSS; it has not been seen rendered yet.
- **Feature colours ignore dark mode when JavaScript is off.** PaperMod's greys have a `<noscript>` fallback on `prefers-color-scheme` in `head.html`. The feature tokens switch only on `[data-theme="dark"]`, which only JavaScript sets. So with JavaScript off, a dark page gets the light-mode dex green, gear blues and trip colours. Only `alert.css` and `gallery-story.css` handle this case.

### Shape and type

- **Radii:** 24 distinct values. Cards use 12px (dex, gear, software), `0.75rem` (models, gallery nav: also 12px, in another unit), `1rem` (albums) and 8px (project nav).
- **Shadows:** about 20 distinct definitions. The gallery SCSS carries Tailwind's (`0 10px 15px -3px …`), covers use `0 2px 8px rgba(0,0,0,.2)`, dialogs `0 20px 60px rgba(0,0,0,.5)`.
- **Font sizes:** 62 distinct values: 137 in px, 153 in rem, 3 in em. PaperMod itself uses px: 12, 13, 14, 16, 18, 24, 26, 32, 34 and 40.

### Spacing

There are about 770 margin, padding and gap declarations, with 77 distinct values: 366 in px, 327 in rem, 21 in em.

- The most frequent values already sit on a 4px grid: 8px, 12px, 16px/`1rem`, `0.5rem`, `1.5rem`, 24px, `2rem`.
- Around them are near-duplicates (`0.4rem` and 6px, `0.6rem` and 10px, `0.9rem` and 14px, `1.1rem` and 18px, `1.25rem` and 20px) and odd small values (`0.15rem`, `0.35rem`).
- Files are either px (`gallery-story.css`, `travel.css`, `main.scss`) or rem (dex, gear, gaming, models). A reader who enlarges the browser font therefore gets larger spacing in the dex but not in a story.
- PaperMod's own `--gap` and `--content-gap` appear 15 times.

The same element in different areas:

| | Dex | Gear | Models | Gaming | Project nav | Albums | Software |
|---|---|---|---|---|---|---|---|
| Card-grid gap | 0.9rem | 1rem | 1.25rem | 1.1rem | 16px | 1.5 / 2rem | – |
| Card padding | 0.5rem | 1.1–1.2rem | – | – | 12px | – | 1.5rem |
| Heading → content | 0.8rem | 0.35rem | 1rem | | | | |
| Between sections | | 3rem | 2–2.5rem | | 56px | | |

### Widths and breakpoints

- Text-like maximum widths alone come in eight forms: 720px, 68ch, 60ch, 32em, 800px, 768px, 1024px, 1536px.
- There are 19 distinct breakpoints between 399px and 1150px, among them `699`/`700`/`701`, `399`/`400`, `499`/`500` and `999`/`1024`.
- The page edges are in §5.1.

## 2. Where the tokens live

In `assets/css/core/theme-vars.css`. That file is already the repo's override of PaperMod's palette, and PaperMod concatenates it first (core, then common, then extended; see `head.html`). Custom properties resolve when they are used, so every file can read them: the extended bundle; `main.scss` and `_styles.scss`, which are compiled separately and only for the gallery (Dart Sass leaves `var()` alone); and the map scripts.

There are two exceptions to "one file", both because CSS allows nothing else:

- **The mobile gutter.** PaperMod's `core/zmedia.css` is concatenated last in core and sets `--gap: 14px` below 768px, which would override any value in `theme-vars.css`. So the gutter is set in an extended file, `assets/css/extended/00-layout.css`, which loads after core. Overriding `zmedia.css` itself is the alternative; it is short. To be decided in the build.
- **Breakpoints** cannot be custom properties: `@media (width < var(--x))` is invalid. They are a documented list that a test enforces (§6).

The file has these sections: neutrals (PaperMod's), accent, status, image and viewer, data palettes, spacing, widths, type, radius, shadow. Every token gets a one-line comment saying what it is for, and every data palette says what it encodes.

## 3. Colour

### 3.1 Neutrals: PaperMod's, kept

`--theme`, `--entry`, `--primary`, `--secondary`, `--tertiary`, `--content`, `--border`, `--code-bg` and `--card` keep their names. They are used nearly 400 times, and renaming them buys nothing.

One addition: **`--rule`**, a 1px line that stays visible on white. PaperMod's light `--border` (`#eee`) all but disappears as a rule. The stories found that and created `--story-rule`; that token becomes site-wide.

### 3.2 Accent and status

| Token | Use |
|---|---|
| `--accent` | Links that should stand out, the active filter, focus ring, selected state, rating stars, progress bars |
| `--accent-soft` | Tinted background behind accent content (active chip, highlighted card) |
| `--on-accent` | Text on an accent fill |
| `--status-ok` / `-warn` / `-danger` / `-info`, each with a `-soft` variant | Alerts, form messages, project status, newsletter feedback |
| `--like` | The heart (today `#ef4444`, defined twice) |

Rules:

- The accent marks **state and emphasis**. It is never decoration for a section.
- Every pair reaches **4.5:1** in both themes, and a test checks it (§9): `--accent` on `--theme`, on `--entry` and on `--code-bg`; `--on-accent` on `--accent`; each status colour on its surface.
- GitHub alerts have five kinds. "Important" (purple) either maps to `--accent` or keeps an alert-only token; to be decided in the build.

**The accent is Schiefer** (`#5b6b7d` / `#a1b4c8`). It reaches 5.46 / 5.01:1 on the light surfaces (`--theme`, `--code-bg`) and 7.85 / 6.35 / 5.49:1 on the dark ones (`--theme`, `--entry`, `--code-bg`); text on an accent fill reaches 5.46:1 (white, light) and 7.85:1 (`--theme`, dark). Because it carries almost no colour, three rules follow. The decision aid made each of them visible:

- **In-text links keep their underline, always.** Against the body text (`--content`), a Schiefer link differs by only 3.02:1 in light mode and **1.22:1** in dark mode. Colour alone does not mark it as a link (WCAG 1.4.1 asks for 3:1 when colour is the only cue). PaperMod's `box-shadow` underline already does the work, in the accent colour; it must never be removed for a "cleaner" look.
- **No state is carried by the tint alone.** `--accent-soft` (12% light / 16% dark over `--entry`) differs from the card by only 1.17:1 / 1.37:1, so it is decoration, not a signal. "Fotografiert" keeps its accent border and gains a marker (a ✓, or a filled dot) so that it still reads as a state; the same applies to any other selected or active state that would otherwise rely on a tinted background.
- **The accent is not drawn on maps.** A Schiefer range over the land of the dex map stands out by only 1.54:1 (light) and 1.94:1 (dark). So the dex range, the sighting pin and the trip map's "you are here" keep data colours of their own (§3.3), and do not take the accent, as the decision aid had tried.
- `--status-warn` keeps the amber the warning alert uses today (`#8a5a00` / `#d8a657`). With a slate accent it no longer collides with anything, so nothing has to move. The project stories' amber `--accent` becomes Schiefer.

### 3.3 Data colours

Colour that **encodes something** is not UI colour, and it may come in many shades: the gear charts (an ordinal ramp: more is darker), the trip modes (categorical: train, flight, car), the dex map (land, water, borders, range, sighting), IUCN status. Rules:

- They are defined in the tokens file, in a *data* section, one group per feature (`--gear-*`, `--trip-*`, `--map-*`, `--iucn-*`), with light and dark values like every other token.
- Each group's comment says what it encodes and whether it is ordinal or categorical, and it is checked for that. An ordinal ramp must be monotone in lightness. Categorical colours must stay distinguishable, including for the common colour-vision deficiencies.
- **A data colour never uses the accent's hue for a meaning the accent does not have.** With a slate accent this holds trivially: a hue at chroma 0.035 is no hue. The rule stays for the day the accent changes.
- **Maps keep their own colours** (§3.2): the dex range, the sighting pin and the trip map's "you are here" are data colours. Today's dex range green and the trip map's "here" orange are the starting point. Each must stand out at least 3:1 against the map's land in both themes, which is checked like any other data palette.
- The maps share one palette. The dex map, the trip map and the route map use the same land, water and line tokens instead of three sets.
- **IUCN status uses the official Red List colours** (settled): CR `#d81e05`, EN `#fc7f3f`, VU `#f9e814`, NT `#cce226`, LC `#60c659`, DD `#d1d1c6`. These are the values in common use; verify them against the IUCN's own sheet in the build. The dex uses LC, NT, VU, EN and DD today; CR is defined for the first species that needs it.
  - The badges become **filled**, each with whichever text colour reaches 4.5:1 on its fill. Yellow and yellow-green fail as text on white, which is how today's outlined badges would show them.
  - Today LC and DD carry no colour at all; with the Red List scale every step has one.
  - The difficulty badges (easy, moderate, challenging) use `--status-ok` / `-warn` / `-danger`.
- JavaScript reads tokens through one helper, **with no hard-coded fallback**: a fallback is a second copy, and it drifts (§1).
  - Caveat: with `light-dark()` (§3.4), `getPropertyValue("--x")` returns the unresolved text `light-dark(…)`, not a colour, and Leaflet cannot use that.
  - So the helper resolves through a probe element (set `el.style.color = "var(--x)"`, then read `getComputedStyle(el).color`) and reads again after a theme switch. To be verified in the build.

### 3.4 Dark mode: each token defined once

Today a dark value is written up to three times:

- in `:root[data-theme="dark"]`;
- in the `<noscript>` block of `head.html` (PaperMod's greys only);
- in two files, in `@media (prefers-color-scheme: dark) :root:not([data-theme])`.

The proposal:

```css
:root                     { color-scheme: light dark; } /* no JS: follow the OS */
:root[data-theme="light"] { color-scheme: light; }
:root[data-theme="dark"]  { color-scheme: dark; }

:root {
  --accent: light-dark(#8a5a00, #d8a657);
  /* … every colour token, once */
}
```

- `light-dark()` picks its value from the element's `color-scheme`. The theme toggle, the stored preference and the no-JavaScript case all follow from the three lines above, and the duplicate `<noscript>` block in `head.html` can go.
- Browser support: `light-dark()` has been in all engines since 2024 (Firefox 120, Chrome 123, Safari 17.5), and the current Tor Browser ESR should have it. Check before relying on it.
- Older browsers drop the declaration and get no colour at all. Step 2 decides whether a plain light value goes in front as a fallback.
- Side effect to check: `color-scheme` also themes scrollbars and form controls, which is wanted.

### 3.5 Photos and the viewer

Two groups do not follow the theme, on purpose:

- **On image**, for text over a photo: `--scrim` (the gradient or overlay) and `--on-image` (light text). One value each instead of five (§1).
- **Viewer:** PhotoSwipe's controls, the info popup and the download dialog are always dark, like the lightbox itself. Tokens: `--viewer-bg`, `--viewer-text`, `--viewer-muted`, `--viewer-line`. Today that is about 50 literals in `main.scss`.

## 4. Spacing

### 4.1 Scale

`--space-1` … `--space-8` = 0.25 · 0.5 · 0.75 · 1 · 1.5 · 2 · 3 · 4 rem, which is 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64px at the default font size.

- **Spacing is in rem**, so it scales with the reader's font size. px stays only for hairlines (1–2px) and borders.
- At the default font size `16px` and `1rem` are the same, so switching units changes no screenshot. Only snapping values to the scale moves anything.

### 4.2 Roles

Steps alone would bring the drift back: one area picks `--space-3`, the next `--space-4`. So features use **role tokens**:

| Token | Default | Use |
|---|---|---|
| `--space-inline` | `--space-1` or `-2` | Icon ↔ label, inside a badge |
| `--space-heading` | `--space-3` | Heading → its content |
| `--card-pad` | `--space-4` | Inside a card |
| `--grid-gap` | `--space-4` | Between cards |
| `--photo-gap` | `--space-5` (24px) | Between photos |
| `--section-gap` | `--space-7` (48px) | Between sections of a page |
| `--content-gap` | PaperMod's, re-pointed to the scale | Inside PaperMod's own templates |

Density is settled as medium: 48px between sections, 24px between photos. Should it ever change, that is two lines in one file.

Computed geometry stays out of the system on purpose: `--pull` of the floating `galleryImage`, the story widths derived from an aspect ratio, and `calc()` against `100vw`. That is layout arithmetic, not spacing.

## 5. Page edges and widths

### 5.1 Today

PaperMod's defaults:

- `--gap` is 24px, and 14px at 768px and below.
- `.main` is the text column: 720px plus `2 × --gap`.
- The header track is 1060px plus `2 × --gap`, and logo and menu are inset by `--gap`.

On every page whose path contains `/gallery`, `head.html` also loads `main.scss`. That stylesheet:

- gives `main > section`, `hgroup`, `.gallery-nav` and `section.featured` another `1.5rem` of side padding;
- sets `.main { max-width: 75% }` from 1040px up.

Distance from the screen edge to the content, in px:

| Page | Phone 375 | 1440 | 1920 |
|---|---|---|---|
| Header (logo) | 14 | 190 | 430 |
| Text pages (posts, About, gaming, reading) | 14 | 360 | 600 |
| Gallery, dex, gear, models | **38** | 228 | **288** |
| Photo tag pages (`/gallery/tags/…`) | 14 | 360 | 600 |
| Story "full" photo | 14 | 24 | 240 |
| Travel page (map and feed) | 8 | 20 | 260 |
| Lightbox, download dialog | 0 | – | – |

What that does:

- **On a phone**, the gallery is indented 24px against the logo and spends about a fifth of the screen width on margins. That happens on photos, where margin hurts most.
- **On a large screen**, there are three left edges: text, header and gallery.
  - From about 1540px up, the gallery is wider than the header. On a 2560px monitor its grid is about 1820px wide.
  - The gallery's width follows the monitor, not a design decision.
- **Whether a page gets the gallery edge depends on its path, not its type.** Photo tag pages are published under `/gallery/tags/`, but their `.Path` is `/phototags/…` (`tag-pages.md`). So they don't get `main.scss` and lay out a photo grid inside the text column.
- **The edge is already being patched.** `dex.css` adds `padding-inline: 1.5rem` to the species page by hand, because the page is an `<article>` and `main > section` does not reach it.
- **Breaking out of the column is built three times**: in `galleryImageText`, the stories and the travel page. Two of them use `100vw - 2 × gap`; the travel page uses `100vw - 2rem`, and `- 1rem` below 820px. That is why the travel page has an 8px edge on a phone.

### 5.2 Proposal

- **One gutter**, `--gutter`: 16px (`--space-4`) below 768px, 24px (`--space-5`) above.
  - PaperMod's `--gap` is set to the same values, so header, footer and `.main` follow.
  - It is applied **once**, at the outermost container, and nothing inside adds a second one. The `1.5rem` side paddings in `_styles.scss`, `gallery-nav.css`, `dex.css` and `gallery-story.css` go.
- **Four widths:**

  | Token | Value | For |
  |---|---|---|
  | `--width-text` | 720px (= `--main-width`) | Posts, bios, species text |
  | `--width-wide` | 1060px (= `--nav-width`) | Photo grids, dex overview, gear, card grids. The content edge lines up with logo and menu |
  | `--width-full` | 1440px | Story hero and full-width blocks, the travel page |
  | `--width-narrow` | 560px | Dialogs, forms |

  Each width is capped at `100vw - 2 × --gutter`.
- **Edge to edge** is a fifth, explicit case, `bleed`, used only for the story hero and the lightbox (settled). Photo grids on a phone keep the gutter.
- **`max-width: 75%` goes.**

### 5.3 Built once, chosen by page type

- **Four layout classes** (`l-text`, `l-wide`, `l-full`, `l-bleed`) own the breakout arithmetic: `width: min(var(--width-…), 100vw - 2 * var(--gutter))`, centred with `margin-left: calc(50% - width / 2)`. That includes the scrollbar caveat the existing comments already document. The three hand-built breakouts switch to them.
- **The page's own width comes from `params.theme`.** One partial maps the theme to a layout and writes it onto `.main` (`data-layout="wide"`). It never comes from `strings.Contains .Path "/gallery"`, so the tag pages lay out like every other photo grid.
- **Layout rules move** from `_styles.scss` (gallery only) into the extended bundle (every page). Whether `main.scss` keeps loading by path is a separate question, since it carries PhotoSwipe, but no layout may depend on it.

## 6. Breakpoints

A fixed set: **480 · 640 · 768 · 900 · 1100**, plus **700** as a documented exception.

- **700** is where PhotoSwipe's `paddingFn` drops its padding, and the download dialog follows it.
- **768** is PaperMod's own breakpoint (`zmedia.css`, the header).
- **900** is where `galleryImageText` stacks, for the reason given in CLAUDE.md.

Rules:

- Write them in **range syntax**, `(width < 640px)` and `(width >= 640px)`, so `639`/`640`/`641` cannot recur.
- Go mobile-first wherever a file is rewritten anyway.
- Container queries are welcome where a component decides rather than the page (cards in a grid); they do not count against the set.

## 7. Type, radius, shadow

- **Type:** a scale of about eight sizes in rem, `--text-xs` … `--text-3xl`. It **includes PaperMod's own steps** (14, 16, 18, 24, 32, 40px), so our headings sit next to PaperMod's without near-misses. Two or three line-height tokens. 62 sizes become about 8.
- **Radius:**
  - `--radius-s` 4px
  - `--radius` 8px (PaperMod's)
  - `--radius-l` 12px, the card radius most areas already use
  - `--radius-pill` 999px
  - `50%` for circles

  Albums (16px) and the project nav (8px) move to `--radius-l`.
- **Shadow:** `--shadow-1` resting, `--shadow-2` raised or hovered, `--shadow-3` dialogs, `--shadow-cover` for book and game covers. About 20 become 4.

## 8. Components and the styleguide page

Tokens come first. Shared components come only where the markup is already alike; this is not a component library.

- **Card:** dex, gear, models, software projects, project nav, albums. One radius, one padding, one hover.
- **Chip / filter button:** dex filters, reading list, gallery filter bubbles, achievements filter.
- **Image with scrim:** gallery nav cards, the featured card, model cover, dex hero credit, gaming overlays.
- **Badge:** dex difficulty, IUCN and caught; software project status.
- **Stat row:** dex count, gaming header, gear.
- The breadcrumb is already one partial.

**The styleguide page** lives at `/<lang>/styleguide/`:

- It shows every token as a swatch or sample with its contrast ratios, every component, both themes side by side, and the four widths and the gutter drawn out.
- It is unlisted like the demo projects (`build: {list: never, render: always}`, `robotsNoIndex`, `searchHidden`), so it is in no sitemap, feed, search or golden URL list.
- It stays permanently, as the reference.
- It reads the token list from the stylesheet at runtime (the `:root` rules in the CSSOM), so it cannot fall behind the file.
- It must load everything a gallery page loads: one more reason to decouple layout from `main.scss` first.

**A throw-away decision aid** was built on 2026-11-18, outside the repository, to choose the accent on a page rather than in hex codes. It came in two parts:

- eleven candidates around the hue wheel, each tuned to reach 4.5:1 in both themes and checked for hue collisions with the data and status colours, with today's state beside them;
- four finalists rendered on eight page types: post, gallery, photo page, dex species, game page, reading list, project story, trip map.

The outcome is Schiefer (*Decisions*). The aid also produced the three rules in §3.2.

## 9. Tests: drift fails the build

1. **Literal ratchet:** `tests/static/design-tokens.spec.ts`, a source test like `image-urls.spec.ts`.
   - Per file, it counts literals outside the tokens file: colours (hex, `rgb()`, `hsl()`, named), spacing lengths, font sizes, radii, shadows.
   - The counts live in `tests/golden/css-literals.json` and **may only fall**. A file that gains a literal fails; a migrated file's count is lowered in the same commit.
   - Not counted: `0`, `auto`, `%`, `inherit`, `currentColor`, `transparent`, 1–2px hairlines, and `calc()` over tokens.
   - It ends at zero, with a short named allowlist (for example, a brand colour the owner decides to keep).
   - The same scan covers `assets/js/` (the map colours) and inline `style=` attributes in `layouts/`.
2. **Breakpoints:** the same spec rejects any media-query width outside the set in §6.
3. **Geometry:** an e2e spec in Chromium measures, for each page type at 375, 768, 1440 and 1920px, the left edges of logo, content and first grid. It checks three things:
   - a wide grid lines up with the logo;
   - text is centred at `--width-text`;
   - nothing except a `bleed` element comes closer than `--gutter` to the screen edge.

   That is the rule people perceive as "tidy", and the one screenshots are worst at catching.
4. **Contrast:** on the styleguide page, every text-on-surface sample reaches 4.5:1 in both themes (3:1 for large text and UI elements). The reading-list bug is exactly what this catches. Extending it to the real pages later is an option, using axe-core's colour-contrast rule, vendored like everything else, with no network.
5. **Screenshots:** Playwright `toHaveScreenshot` per area, light and dark, at 375 and 1440px, as a **review aid during migration**: a baseline before, a diff after, and the owner looks.
   - It is not a permanent gate. Font rendering differs between the owner's Fedora machine and a CI container, and a gate that flakes gets ignored.

As with everything else, `npm test` runs these tests and `deploy.sh` stops on them.

## 10. Deliberately out

- **Fonts.** Cantarell stays.
- **PaperMod's own CSS.** It stays the base. We set its variables; we do not rewrite its rules.
- **A framework or a build change** (Tailwind, SCSS everywhere, PostCSS). Plain CSS with custom properties does all of this. The SCSS in `main.scss` stays for PhotoSwipe.
- **Icons, motion, transitions.**
- **A redesign.** No page changes structure. The visible changes are the accent, the gallery's width on large screens, its edge on a phone, and a few pixels wherever spacing snaps to the scale.
- **Per-language styling.**

## 11. Build order

0. **Baseline and the bug.**
   - Fix the reading list's light mode now: it is a bug, not a design question, and needs no decision.
   - Record screenshots of every area (light and dark, 375 and 1440px).
   - Measure the edge table of §5.1 in a browser.
1. **Decisions.** All seven were settled on 2026-11-18; the accent is Schiefer.
2. **Foundations, with nothing visible changing.**
   - The tokens file, holding every value as it is today and aliasing the existing feature tokens.
   - `color-scheme` plus `light-dark()`.
   - The styleguide page.
   - The ratchet, set at today's counts.

   Nothing fails, and from here nothing can get worse.
3. **Layout.** Gutter, widths, layout classes, page type → layout, and the geometry test. This is the largest visible change, so it is reviewed on its own.
4. **One pass per area.** Each pass covers colour, spacing, type, radius and shadow together, so each area is reviewed once, and it lowers that area's ratchet in the same commit. Order:
   1. stories
   2. dex, with its map
   3. gear
   4. travel, with the maps
   5. models
   6. gaming and reading
   7. software projects
   8. alerts, newsletter, activity
   9. the gallery SCSS and the viewer
5. **Close.**
   - Ratchets at zero; allowlist final.
   - The rules go into CLAUDE.md's *Conventions* ("colour, spacing and widths only through tokens; breakpoints only from the set") and into AGENTS.md.

**Cost:** mostly mechanical: about 250 colour literals, about 770 spacing declarations, 62 font sizes. Unlike colours, though, snapping spacing moves things by a few pixels in many places, so every area pass needs the owner to look at the screenshot diff. Steps 2 and 3 need care; step 4 is repetition.
