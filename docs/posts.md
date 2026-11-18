# Posts

## Posts are text-led

Blog posts are **text-led**. Even photography posts use photos as sparse accents
(about three per 1,000 words), not as a photo essay — `galleryImage` and
`galleryImageText` (`docs/gallery/in-posts.md`) exist to place a *few* photos
well, not to fill the page.

When reviewing a post, critique the placement, order and caption fit of its
photos (does the photo belong in this section, does it spoil a later reveal),
never their *count*. If the prose teases a motif that is never shown, fix the
prose so the description stands on its own instead of proposing another photo.

## Proofreading

"Fix the grammar" on a post means characters and spelling, changed in place with
targeted edits: commas, quotation marks („…“), hyphenation, compound spelling,
capitalisation. A single word fixed in place is fine as well — a missing ending
(deutlich**e**), a wrong preposition.

Every sentence, word choice, word order and paragraph otherwise stays as written.
Anything beyond that — rephrasing, reordering, rewriting a sentence — goes into a
list for the owner to decide, not into the file. Check `git diff --word-diff`
afterwards so only the intended tokens changed. The owner's voice (Denglisch,
stretched words like "seeehr") is deliberate.

## Posts in more than one language

The site writes different posts in different languages; every home and every
`/posts/` list shows the newest posts that exist **only** in the other languages
(`docs/concepts/multilingual-home.md`, *The other languages* in `docs/site.md`).
That block is worked out from the content, so a post needs nothing special:

- **A post in one language** appears in the other languages' blocks by itself,
  if it is among that language's three newest untranslated posts.
  `hiddenInHomeList: true` keeps it out, as it does on its own home.
- **Translating a post** is a second `index.<lang>.md` in the same bundle. The
  translation then takes the post's place in that language's own list, drops out
  of that language's block, gets a hint bar on the original ("this page is also
  in …") and is where the language switcher goes. Nothing else to edit.
- **Wording**: the block's texts are the `lang_more_*` keys and `all_posts` in
  `i18n/{en,de,sv}.yaml`; the bar's are `langHint` under each
  `languages.<lang>.params` in `hugo.yaml`, because the bar has to speak the
  *visitor's* language and i18n only reaches the page's own.
- **Checking it by hand**: a browser in another language (or devtools' locale
  override) shows the bar and reorders the block; `localStorage` keys
  `lang-choice` and `lang-hint-dismissed` remember the switcher and the ✕. Clear
  them to start over. `/` sends you to the home in your browser's language.
- Run `npm test` after adding a language or touching any of this:
  `tests/static/multilingual-home.spec.ts` recomputes every block from
  `content/posts/`.
