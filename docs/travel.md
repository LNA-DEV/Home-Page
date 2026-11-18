# Travel

`/travel/` is one JavaScript-driven page fed live by the HomePageCompanion API.
There are no per-trip Hugo pages.

- **One content page**: `content/travel/_index.{en,de,sv}.md` with
  `params.theme: travel-list`, dispatched in `layouts/_default/list.html` to
  `layouts/partials/travel-list.html`, which renders the header and an empty
  `<div class="trip-index" data-trip-index>`.
- **`assets/js/travel.js` is the page.** On `[data-trip-index]` it routes on the
  hash: empty → the card list (`GET /api/trips`), `#<slug>` → one trip
  (`GET /api/trips/<slug>`). `teardownApps()` disposes the previous Leaflet map on
  every route change. The same script renders the `{{< trip "slug" >}}` shortcode
  (`layouts/shortcodes/trip.html`) inside a post.
- **The data comes from the companion.** `head.html` builds `tripsBaseUrl` =
  `<companion>/api/trips`: `https://companion.lna-dev.net` in production,
  `http://localhost:8080` under `hugo server`. Photo `src` values are
  server-relative (`/api/trips/media/…`) and resolved against the companion's
  origin. Trips are created and edited only in the companion's admin UI; a change
  shows up live, with no rebuild or deploy.
- **The browser routes nothing.** The companion computes each leg's road or rail
  geometry when a trip is saved and delivers it as `transportIn.geometry`; a leg
  without one is drawn straight through its via-points. The basemap is the site's
  own (`docs/maps.md`).
- **Leaflet** is the vendored 1.2.0 at `/packages/leaflet/`, which `head.html`
  loads only on `/travel` paths and on pages with the `trip` shortcode (the
  `{{< map >}}` shortcode loads the same file). Styles:
  `assets/css/extended/travel.css`.
- **SEO trade-off, accepted by the owner:** trips are not Hugo pages, so only
  `/travel/` is in the sitemap and the search index; a trip's link is a fragment
  (`/travel/#<slug>`) and is not indexed.
- **Not in the nav menu**, by the owner's decision — `/travel/` is reached through
  the site search. Do not add a menu entry.
- **Search:** PaperMod's index iterates `site.RegularPages`, which a branch page is
  not part of, so `layouts/_default/index.json` appends `/travel` by hand (as it
  does `/gaming/`, `/gallery/gear/` and `/gallery/models/`). Single trips are not
  searchable; that would take a build-time `resources.GetRemote` of `/api/trips`
  plus a `security.http.urls` entry. Keep the theme's exclusions (`searchHidden`,
  the `archives` and `search` layouts) when editing that override.
