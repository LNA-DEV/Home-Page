# Protomaps basemap assets

Glyphs and sprites for the Protomaps basemap style, served from this site so a
map never asks a third party for its labels or icons
(`docs/concepts/self-hosted-maps.md` §7). `assets/js/basemap.js` points the
MapLibre style's `glyphs` and `sprite` here.

Taken from <https://github.com/protomaps/basemaps-assets> at commit
`028c18f713baecad011301ff7a69acc39bcc2ae7` (2026-10-06):

- `fonts/` — the four fontstacks the style uses (Noto Sans Regular / Medium /
  Italic, Noto Sans Devanagari Regular v1), 256 PBF ranges each. SIL Open Font
  License, `fonts/OFL.txt`. Upstream, 252 of the Devanagari ranges are symlinks
  to Noto Sans Regular; they are real copies here, because Hugo does not publish
  symlinks out of `static/`. Git stores identical files once.
- `sprites/v4/` — the spritesheets of the v4 style, one per flavor. Derived from
  the MIT-licensed tangrams/icons, `sprites/LICENSE-tangrams-icons.md`.

The style itself comes from `@protomaps/basemaps` (`../protomaps-basemaps/`).
Its major version must stay paired with the tile schema the companion serves:
`@protomaps/basemaps` 5.7.2 draws schema 4.x.
