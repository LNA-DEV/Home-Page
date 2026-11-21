---
name: photo-metadata
description: Suggest titles, alt texts, tags (social-media hashtags), category and species for the newly added photos in data/gallery.yaml, i.e. the entries in its uncommitted diff. Use when the owner asks for metadata, a title, alt text or hashtags for new gallery photos.
---

# Metadata for new gallery photos

Background: `docs/gallery/overview.md` (fields; *Reviewing a new photo's metadata*)
and `docs/gallery/photo-pages.md` (the English title is the URL).

## Ground rules

- **Suggest, don't write.** `data/gallery.yaml` is edited only after the owner's go.
- **No tests.** Never `npm test` or another test project; the one exception is the
  build project for the golden list (step 6).
- **Look at every photo** before writing a word about it.
- **Existing values stay as close to the owner's version as possible.** If one is
  fine, fix only grammar and spelling. Change more only when it is wrong or weak,
  and say why.

## 1. Find the photos

- `git diff data/gallery.yaml`: the new entries (`src`, `id`).
- The file is `<source>/<src>`, where `<source>` is the gallery mount in
  `config/_default/module.yaml`.
- The exports are far too big to view directly (~40 MB, 5520×8280). Make a preview
  and read that: `magick "<file>" -resize 2000x2000 "$TMPDIR/<id>.jpg"`. Never write
  into the photo store or the repo.

## 2. Title (en, de, sv)

`<lyrical part> - <descriptive part>`, with a plain hyphen between spaces, never `—`:

    Smiling Lamb - Spring Lamb Basking in the Afternoon Sun
    The Warmth Ahead - Spring Lamb in a Sunlit Meadow

- About five English options, from plain to creative.
- The descriptive part carries the search terms: subject, species, place, light.
  It is the photo page's `<title>`, so keep the whole title short, roughly 50–65
  characters.
- English in title case. German and Swedish follow their own capitalisation, as in
  the existing entries. Translate the chosen title by meaning, not word for word.
- The English title also names the page URL and the image files. If the photo's
  URL is already in `tests/golden/published-urls.txt`, a new title needs the old
  slug in `slugAliases:`, so say so in the proposal.

## 3. Alt text (en, de, sv)

- Concrete and visible only: subject, action, setting, light. It must work on the
  web and in a social-media post.
- If an alt text already exists, keep its spirit and only improve it.
- German and Swedish say the same as the English.

## 4. Tags / hashtags

- The `tags:` list. It is also posted unchanged as hashtags on social media.
- camelCase as in the existing entries (`bavarianAlps`). Aim for being found; no
  platform tags (`catsOfInstagram`).
- A species: its common name, and the scientific name where it helps
  (`whiteTailedEagle`, `haliaeetusAlbicilla`).
- Lagom: 10–24 tags, most often 14–19 (the 30 newest entries on 2026-11-21). Fewer for a
  simple photo.
- Reuse an existing spelling (`grep -ic -- "- <tag>$" data/gallery.yaml`). Every
  tag gets its own page, and two spellings split it.
- Never a person's name: the build stops on a model's slug or name. People are
  credited with `model:`.
- Deliver a **change list**, never the whole list:
  `+ tag`, `- tag (why)`, `~ old → new`. Say so if the existing tags are weak.

## 5. The proposal, per photo

File and `id`, the title options, the alt text in three languages, the tag change
list. Also propose `category:` and `species:` whenever they are not right
(`category: others` left from the stub, an empty or wrong `species:` when a species
is visible); they are filled in, never only pointed out. A species not yet in
`data/dex.yaml` gets its dex record in the same go, or the build warns
(`docs/gallery/dex.md`, *Adding a species you just photographed*).

## 6. After the go

- Write every agreed change into `data/gallery.yaml`: title, alt, tags, category
  and species; a new species gets its dex record first.
- Once the title is set, update the golden list:
  `npx playwright test --project build`, then `npm run golden:update`.
- Commit only when asked.
