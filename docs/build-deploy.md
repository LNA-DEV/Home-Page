# Build and deploy

- Local build: `hugo` — output goes to `public/`.
- **NEVER render into RAM — no `hugo --renderToMemory`, no plain `hugo server`** (which renders to memory by default). The site is far too large for it (gigabytes of gallery output); it has crashed every machine it ran on, more than once. Build to disk: `hugo -d <scratch dir>`, or `npm test`. A PreToolUse hook in `.claude/settings.json` (`.claude/hooks/block-hugo-memory.py`) blocks both; do not try to get around it.
- Local server (the owner runs it, not Claude): `hugo server -D --renderToDisk` (drafts on).
- Deploy: `./deploy.sh` builds twice (clearnet + Tor onion `baseURL`) and rsyncs `public/` to the production server. **Do not run this without the user's say-so** — it pushes live. Each build is followed by `scripts/gallery-embed-metadata.py` and its `--check` before the rsync — see *Embedded metadata in the served files* in `docs/gallery/images.md`. That adds minutes to each build. After each rsync it reloads the site's nginx container (`nginx -t && nginx -s reload`) so a changed redirect map takes effect — see *Served image names* in `docs/gallery/images.md` — and after the clearnet one it runs `scripts/check-live-urls.py`, HEAD requests against the live site that stop the script before the Tor build if a variant, a redirect or an underscore photo URL does not answer as it should (*Processed images* in `docs/gallery/images.md`). **The nginx config is not in this repo**: it is `../Web-Services/homepage/nginx.conf` and `../Web-Services/homepage-tor/nginx.conf`, deployed by that repo's own `deploy.sh`; a changed `nginx.conf` is a single-file bind mount and needs `docker compose up -d --force-recreate` on the server to take effect.
- Module bootstrap (only if `go.sum` is missing/broken): `go mod download`.
- Image binaries are intentionally **not in git** and live outside the repo. Hugo mounts them in via `module.mounts`, mapping the local photo store to the `assets/images/gallery/` virtual path. Because that source is an **absolute, machine-specific path**, the mount lives in the gitignored **`config/_default/module.yaml`**, not in `hugo.yaml`. Per machine, set it up once: `cp config/_default/module.yaml.example config/_default/module.yaml` and put that machine's photo-store path in the gallery `source`. A clean checkout without it builds fine but renders an empty gallery (`gallery-images.html` warns when the mount is empty). Two things to know:
  - **`mounts` is replace-not-merge.** A `module.mounts` list in `config/_default/module.yaml` silently discards the whole list in `hugo.yaml` — which is why the local file restates the default `assets` mount and why `hugo.yaml` deliberately declares no mounts at all. Everything else in `hugo.yaml` is still read normally.
  - **A symlink can no longer be the mount `source`.** It used to work — that is what the old repo-root `gallery-photos` symlink relied on — but only because of a Hugo regression (`RootMappingFs.statRoot` calling `Stat` instead of `Lstat`, introduced in 0.123.0). That was a symlink-confinement bypass (CVE-2026-58403) and was fixed in 0.163.1, so from Hugo 0.163.1 on a symlinked mount source resolves to nothing — no error, just an empty gallery. Do not reintroduce one.
- **`invalid JPEG format` from `image-variant.html`** means a source file in the photo store is damaged, not a template bug. Check it with `magick -regard-warnings "<file>" null:`, find when the Nextcloud client last downloaded it in `~/.config/Nextcloud/logs`, and restore the good version from the Nextcloud web UI (*Versions*). Which device uploaded the bad version is in the Apache log of the Nextcloud container (user agent per request; how to read it: `../Infra/documentation/betrieb-und-lessons-learned.md`). Never write to the store from the repo. The failed build leaves a zero-byte `<name>_hu_<hash>.jpg` in `resources/_gen/images/` for every variant it tried; delete exactly those files, not the cache. (2026-11-21: the Nextcloud Android app uploaded `_DSC3871_26883.jpg` with 29 MB of zeros.)

## The image cache

`resources/_gen/images/` holds every processed image. **Never clear it** as part
of an ordinary check — no `hugo --gc`, no `rm -rf resources`. With a warm cache a
build takes well under a minute; cold, it takes well over ten minutes (a 600 s
timeout was not enough). The cache is keyed by source image and processing spec,
so template and data changes are picked up with the cache warm. Deleting a build
directory (`public/`, a scratch directory) is cheap and fine.

Clear it only when the image pipeline itself changed (processing spec,
dimensions, format, `images.Process` options) or a cached file is provably stale
or corrupt — and say why before doing it.

The first build after the gallery mount moved (2026-09-10) took ~16 minutes and
grew `resources/_gen/images` from 5,313 to 7,072 files: the cache key is not
purely a function of the mount target. Budget for that when a mount changes.

**Hugo's "Processed images" count means less than it looks.** The row in the
build stats swings between the en/de/sv columns on identical rebuilds (nearly all
under de one run, nearly all under sv the next). That is normal: gallery and dex images
are global resources shared by all three languages, Hugo builds the languages
concurrently and counts each image against whichever language reached it first;
the others get uncounted cache hits. The signals of real reprocessing are a
changed *total*, wall time jumping to minutes, and new mtimes in
`resources/_gen/images`.

## The web server

The site's nginx config lives in `../Web-Services`, not here:

- `homepage/nginx.conf` serves the clearnet site, behind Nginx Proxy Manager,
  which terminates TLS (`absolute_redirect off`); `homepage-tor/nginx.conf` serves
  the onion service. The two differ only in a comment. Both run `nginx:latest`.
- `root` is set inside `location /`, not at server level, so a new regex
  `location` has to repeat it.
- Web-Services has its own `deploy.sh`. `nginx.conf` is a single-file bind mount:
  after the rsync replaces it the container can keep the old inode, and
  `docker compose up -d` does not recreate it. A config change needs
  `docker compose up -d --force-recreate <service>`.
- `nginx:latest` is available in the local docker, so a config change can be
  tried in a throwaway container first.
