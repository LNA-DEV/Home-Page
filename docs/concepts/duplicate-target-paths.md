# Task: tolerate Hugo's cache-eviction duplicates, then move the achievement icons back to `assets/`

**Status:** task, not started. Deliberately out of scope for the game pages (`gaming-game-pages.md`). It comes after them, and the second half undoes a workaround those pages needed.
**Read against:** the `gaming-game-pages` worktree of 2026-09-28. The measurements are from that day, on Hugo 0.166.0.

The game pages put ~3,100 achievement icons into `static/` instead of `assets/`. The reason was not that `static/` is the better place. With the icons as `resources.Get` files the build warned `Duplicate target paths`, and the warning stops a deploy.

The warning was a **false positive**:
- The same file was written twice, byte for byte.
- It will come back without any icons once the gallery or the game screenshots grow far enough.

This task makes the build tell a harmless re-publish from a real path conflict. Then the icons go back to where every other image lives.

## Decisions

| | |
|---|---|
| `--printPathWarnings` | **Stays** in the build test and in `deploy.sh`. It is the only thing that catches two *different* sources writing one file |
| The false positive | Recognised and let through by a **classifier** that knows what harmless looks like — not silenced |
| Every other warning | Still a failure, exactly as now |
| The icons | Back to `assets/images/games/achievements/`, published through `resources.Get` like every other image |

---

## 1. What happens, and why it is harmless

Measured while building the game pages; the details are in `gaming-game-pages.md`, *As built*.

- **The cache.** Every file fetched with `resources.Get` / `resources.Match` goes through one partition of Hugo's **in-memory** cache (dynacache, the partition behind `GetOrCreateFile`). The partition is an LRU capped by **count**: 100,000 / 10 × weight 0.4 ≈ 4,000 entries at start.
  - Memory only nudges the cap. `HUGO_MEMORYLIMIT=64` changed nothing, and the current site builds clean even at `HUGO_MEMORYLIMIT=1`.
  - This is not `resources/_gen/`, the on-disk cache of *processed* output, which is untouched by all of this.
- **What eviction does.** An evicted resource is re-created from the same source file on its next use. The `.RelPermalink` publishes it a second time: same source, same bytes, same path.
- **Why it still stops a deploy.**
  - `--printPathWarnings` makes Hugo count the writes per target path after rendering. Anything written twice becomes one line: `WARN  Duplicate target paths: /a (2), /b (2), …`.
  - The build test (`tests/build/hugo.spec.ts`) fails on every `WARN`.
  - `deploy.sh` runs both of its `hugo` builds with `--panicOnWarning`.
- **It cannot be silenced selectively.** Hugo logs it with `Warnln` (hugolib/hugo_sites_build.go), without an id, so `ignoreLogs` cannot target it. And one line carries every path, harmless and real alike.
- **Where the ceiling is.** The site sends ~1,200 files through that partition today: 650 gallery photos, 156 game covers, 153 dex data files, 108 dex images, 69 book covers, CSS/JS.

  | Extra `resources.Get` icons | Duplicates reported |
  |---:|---|
  | 0 … 3,104 | none |
  | 3,145 (all of them) | all 150 dex range files, 28–65 icons (varies with render order) |
  | 3,145, gallery mount emptied | none |

  The gallery alone has room for roughly 2,800 more photos. Game screenshots also go through `resources.Match` and are the likelier trigger: 20 per game for 150 games is 3,000.

## 2. The classifier

`scripts/hugo-warnings.py`, Python, stdlib only (the repo's scripting convention), one implementation for both callers. It takes the hugo log on stdin and the build directory as `--site-dir`. It exits non-zero, with a report, on anything it cannot prove harmless.

**Every `WARN` line** other than `Duplicate target paths` is a failure. That is the current policy, unchanged.

**A duplicated path P is harmless only if all of this holds:**

1. **No file at P under a `static` mount.** A static file and a generated or asset file on one path is a real conflict — the `security.txt` case `CLAUDE.md` warns about — even if the bytes happen to match.
2. **The built file equals exactly one source, byte for byte:**
   - a file at P in an **asset mount**: `assets/`, the gallery store mounted at `images/gallery/`, the screenshot store at `images/games/screenshots/`. Read the mounts from `hugo config mounts`, never hard-code them, because `module.yaml` is machine-specific;
   - for a processed variant (`…_hu_<hash>.<ext>`): the file at P under `resources/_gen/images/`, which mirrors the published paths (checked: `resources/_gen/images/images/…`, `…/en/…`);
   - for a **copied** resource published under another name (the gallery originals: store `DSC_2632.jpg`, published as `<english-slug>.jpg`, via `resources.Copy`): any asset-mount file with the same bytes. To stay fast, build a size index with `stat` and hash only same-size candidates. Never hash the whole 7.6 GB store.
3. Anything else — an HTML page, a feed, an alias, a JSON manifest, bytes that match nothing — is a **failure**.

**It prints the number of harmless re-publishes** on every run ("cache pressure: 180 files published twice"), so the pressure stays visible even while nothing fails.

**It must run on hugo's output directly.** In `deploy.sh`, `publish()` runs `gallery-embed-metadata.py`, which rewrites every file under `images/gallery/`. After that, no gallery file matches its source any more.

## 3. Where it plugs in

- **`tests/build/hugo.spec.ts`:** instead of `expect(warnings).toEqual([])`, pipe the log through `python3 scripts/hugo-warnings.py --site-dir .test-site`. Keep attaching the full log. The failure message is the classifier's report.
- **`deploy.sh`, both builds (lines 64 and 78):**
  - drop `--panicOnWarning`;
  - tee the log;
  - run the classifier on it right after `hugo` and before `publish`.

  `set -euo pipefail` is already on, so a non-zero exit stops the deploy exactly where `--panicOnWarning` stopped it. The comment above line 64 explains why the deploy build stops at the first warning; it needs rewriting. The meaning does not change: every warning still stops it, except the one the classifier has proven harmless.

## 4. Moving the icons back

Once the classifier is in, the workaround goes:

- **Files:** `git mv static/images/games/achievements assets/images/games/achievements`. The published URLs stay the same, `/images/games/achievements/…`.
- **`scripts/gaming_common.py`:** `ACH_ICON_DIR` back to `assets/…`, and its comment.
- **`layouts/partials/game-achievements.html`:**
  - `{{ with resources.Get . }}<img src="{{ .RelPermalink }}" …>`;
  - drop the `fileExists "static/…"` check (the `with` covers a missing icon);
  - rewrite the comment.
- **`tests/static/gaming.spec.ts`:** `ICON_DIR` and the ref computation back to `assets/`.
- **Docs:**
  - `CLAUDE.md`: the *Gaming* paragraph "Static, not `assets/`, on purpose" becomes a pointer to this document and to the classifier;
  - `AGENTS.md`: the icon paths;
  - `gaming-game-pages.md`: an *As built* note that the workaround is gone;
  - the docstrings of `sync-steam.py` / `sync-gog.py`;
  - the memory note `reference_hugo_template_traps.md`.
- **Acceptance.** Build the site before and after the move into two directories and `diff -r` them.
  - Only `.RelPermalink` vs. `relURL` could differ; both give `/images/games/achievements/<platform>/<id>/<file>`. So the expected diff is **none**, apart from what the classifier now reports as harmless.
  - The build test and a dry run of the deploy's `hugo` step both pass, with the classifier counting the ~180 re-publishes.

## 5. Tests

`tests/py/test_hugo_warnings.py`, on a fixture site directory and hand-written logs:

- an asset file published twice, identical → harmless;
- the same, but a `static/` twin exists → failure;
- a duplicated `index.html` → failure;
- the built bytes differ from the source → failure;
- a copied resource under another name, identical to one store file → harmless;
- a `_hu_` variant identical to its `resources/_gen/images/` file → harmless;
- any other `WARN` line → failure;
- no warnings at all → pass, and the count line says 0.

Plus the end-to-end proof: the build test with the icons in `assets/` reproduces the warning from §1 and passes.

## 6. Build order

1. `scripts/hugo-warnings.py` and its unit tests.
2. `tests/build/hugo.spec.ts` on the classifier; `npm test` green on the current tree (the classifier has nothing to do yet).
3. `deploy.sh`: `--panicOnWarning` out, classifier in, for both builds. Check it by running the `hugo` + classifier lines by hand, never the deploy itself.
4. The icons back to `assets/`, with the docs; the `diff -r` acceptance; `npm test`.

## 7. Files touched

**New:** `scripts/hugo-warnings.py`, `tests/py/test_hugo_warnings.py`.
**Modified:** `tests/build/hugo.spec.ts`, `deploy.sh`, `scripts/gaming_common.py`, `layouts/partials/game-achievements.html`, `tests/static/gaming.spec.ts`, `CLAUDE.md`, `AGENTS.md`, `docs/concepts/gaming-game-pages.md`, `scripts/sync-steam.py`, `scripts/sync-gog.py`.
**Moved:** `static/images/games/achievements/` → `assets/images/games/achievements/`.

## 8. Out of scope

- **Raising Hugo's cap.** Not configurable; `HUGO_MEMORYLIMIT` does not reach it.
- **Moving other unprocessed files to `static/`** (dex ranges, world GeoJSON). Buys a few hundred places, and after this task there is no reason to.
- **An upstream Hugo issue.** Worth filing — the threshold table in §1 is a ready reproduction: an identical re-publish of an evicted resource should not count as a duplicate. But this task does not wait for it.
