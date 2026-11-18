# Site features

## Software projects page (different from gallery projects)

`content/projects/index.{en,de}.md` lists the user's software projects in front-matter (`projects:` array). Rendered by `layouts/projects/single.html`, which fetches live GitHub stats per repo/org via `resources.GetRemote` against the GitHub API (allowed by the `security.http.urls` whitelist in `hugo.yaml`). Don't confuse these with gallery `projects/` (photo series).

## Activity feed

`content/feed/_index.*` + `layouts/feed/list.html` builds a unified activity timeline by merging:
1. All `RegularPages` in the `posts` section across all languages (`lang.Merge`),
2. Photos from the gallery headless bundle (filtered to non-archive, dated >2000),
3. Talks from `data/talks.yaml`.

Items are grouped by year/month and filterable client-side. Photo permalinks use `#<uuid>` so they jump to the right gallery item — `gallery.html` writes the matching `data-id` attribute. Keep the two consistent if you change either side.

## RSS

Custom `layouts/_default/rss.xml`. The gallery overhaul preserves RSS URL stability — when moving images around, generate redirects rather than breaking old item links.

## security.txt

- `security.txt` (RFC 9116) is **generated, not static** — `layouts/_default/home.securitytxt.txt` plus the `securitytxt` output format in `hugo.yaml`. It was a static file whose `Expires` sat four months in the past before anyone noticed; generating it refreshes the date on every build (build day + 1 year - 1 day, so it stays inside the RFC's "less than a year" recommendation, truncated to whole days so rebuilds are byte-identical). Two things are load-bearing: the format's `path` is `../.well-known` because `path` resolves relative to the **language** directory and the file must sit at the domain root, and it is listed under `languages.en.outputs.home` **only** — putting it in the top-level `outputs` makes all three languages write the same target path. `Canonical` uses `absURL`, so the Tor build in `deploy.sh` emits the onion URL instead of the clearnet one. Do not re-add `static/.well-known/security.txt`; a static file of the same name would collide with the generated one.

## i18n

UI strings in `i18n/{en,de,sv}.yaml`. Per-language menus, descriptions, and home content live under `languages.<lang>.params` in `hugo.yaml`. Content files use `index.<lang>.md` for branch bundles and `_index.<lang>.md` for sections.
