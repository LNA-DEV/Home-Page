# Conventions

## Principles

- Pages work without JavaScript wherever they can; JavaScript enhances them.
  Prefer a CSS solution to a JavaScript one.
- Scripts only write files and never run git — pulling, reviewing, committing and
  pushing are the owner's manual steps.
- Gallery scripting/migration helpers are written in Python.

## Hugo

- **Relative Markdown links are resolved at build time** and need no special spelling: `[x](../../media/fediverse/)` and `[x](/en/posts/media/fediverse/)` produce a byte-identical `href`. `layouts/_markup/render-link.html` resolves a relative destination against the page's own URL — the way a browser would, because Hugo's `.GetPage` does not understand `..` at all — then looks the result up in `layouts/partials/permalink-index.html` to get the canonical URL (trailing slash included) and to confirm a page is actually published there. A relative link that resolves to nothing is a **`warnf` naming the page and the link**, which the build test turns into a stopped deploy. Anything with a scheme, `//host`, a bare `#fragment` or a leading `/` is passed through untouched — an absolute link is the author's explicit statement. Shortcode-produced destinations (`[x]({{< ref "y" >}})`, used by the footer text in `hugo.yaml`) are still opaque placeholders at hook time and are skipped; resolving one would break Hugo's own substitution. **Why this matters beyond tidiness:** a relative link is correct on its page and wrong everywhere the body is reused — RSS 2.0 defines no base URL for HTML inside `content:encoded`, so a feed reader resolves `../x` against its own origin and the link is lost. `rss.xml` already rewrites root-relative URLs to absolute ones, but it cannot rewrite `../` because it does not know which page the body came from. The hook does.
- **`translationKey` is a top-level key of `.AddPage`, not a param** — the same
  shape as `aliases` and `build`. Inside `params` Hugo ignores it and pairs
  translations by path instead, which silently works wherever the slug is
  language-neutral (the dex, the models) and silently fails where it is not: it
  left all 648 photo pages in all three languages with no hreflang cluster at all.
- Content adapters live in `content/**/_content.<lang>.gotmpl`, one per language,
  because Hugo scopes an adapter to the language of its filename.
- **Single-page theme dispatch lives in both `layouts/_default/page.html` and
  `layouts/_default/single.html`.** Which of the two Hugo executes has changed
  between releases since the 0.146 template system (`page.html` on 0.163; on
  0.166 `--printUnusedTemplates` reported `page.html` as unused). Both carry the
  identical dispatch — edit both. `--printUnusedTemplates` also false-flags
  partials invoked with `template` (schema_json, opengraph, twitter_cards), so
  treat it as a hint. Section lists dispatch in `layouts/_default/list.html`.
- `{{ with partial "x.html" (dict …) }}…{{ end }}` is Hugo's **partial-decorator**
  syntax, not a conditional; it fails with a garbled
  "…_pushPartialDecorator… is nil". Assign first:
  `{{ $v := partial "x.html" … }}{{ with $v }}`.
- **Hugo's resource cache is capped by count** — about 4,000 entries for
  everything fetched with `resources.Get` / `resources.Match`, and every
  `resources.Copy`. Past the cap, evicted resources are published a second time
  and the build warns `Duplicate target paths`, naming files you did not touch.
  Details under *Achievements* in `docs/gaming/overview.md` and *Processed images*
  in `docs/gallery/images.md`; the open fix is
  `docs/concepts/duplicate-target-paths.md`.
- A JS bundle built per language (`js.Build` with `params`) whose output is the
  same in all three languages is published three times to one fingerprinted
  path → `Duplicate target paths`. Give it language-specific params, or none.
- A paired shortcode that renders `.Inner` with `RenderString` loses the HTML of
  the shortcodes nested in it, and Hugo finds `.Inner` textually in the
  shortcode's own template. Both, with the workaround, are in
  `docs/gallery/project-stories.md`.
- `errorf` marks the build failed but does not stop template execution. A gate
  that must fail closed is an allowlist, never a denylist
  (`docs/gallery/models.md`).
