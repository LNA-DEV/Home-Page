# Concept: the portraits page

Status: built (2026-11). How it works: `docs/gallery/portraits.md`.

## Why

Portraits are new on the site, made with friends so far. To find people in the
region who want to be photographed, the site needs one page that can be sent to
someone and that can be found: what kind of photos, who takes them, how a TFP
shoot (*Time for Pictures* — no money, both sides get the photos) goes, what the
person gets, and what happens to their name. Searches for TFP in the Rosenheim
area turned up no page of this kind at all (checked 2026-11-22), so the page can
rank for its terms;
the search volume is small, though, and most of its value is as a link from a
profile or a message.

## Decisions

- **Its own page, curated, in the shape of a project essay** — not a grid of
  every portrait. The essay already has hero, chapters, photo blocks and the
  photo-beside-text split; the page reuses them instead of a second set of
  components, and the new blocks (steps, cards, FAQ, contact, people cards) were
  written as story shortcodes so an essay can use them too.
- **Not a project.** A project is an album and is listed among the projects;
  this page is neither. So it has its own theme, and the story data gets a
  second pool next to "the project's photos".
- **Only `public` people, enforced by the build.** The page is a showcase: a
  listing. `unlisted` means "in no listing", `hidden` means "nowhere". The pool,
  the people cards and the test all hold that rule; a placement that breaks it
  stops the build rather than skipping a photo silently.
- **Visibility explained in plain words on the page**, as three cards, because
  the three settings are the strongest argument the page has: a person decides
  whether their name appears, and can change it later.
- **German first.** The audience is local; other languages follow when they are
  written, and every link to the page appears only where the page exists.
- **The kicker inside the h1.** The search terms (TFP, the region) belong in the
  h1 and the `<title>`; the display heading stays short.
- **No `LocalBusiness`, no FAQ schema.** The page names no address and is not a
  business; Google shows FAQ results only for government and health sites.

## Open

- An imprint (Impressum): a page that offers shoots may count as more than a
  private site under § 5 DDG. Not decided; not legal advice.
