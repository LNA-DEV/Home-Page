#!/usr/bin/env bash
#
# Build and publish, twice: the clearnet site and the Tor onion, which differ
# only in baseURL.
#
# Between `hugo` and `rsync` sits the metadata embedding step. Hugo cannot write
# image metadata: it re-encodes every variant and emits no metadata segment at
# all, so a downloaded photo used to carry no licence and no creator, while the
# published original carried camera serial numbers, GPS coordinates and an
# embedded thumbnail of the uncropped frame. The step fixes both ends, reading
# the values Hugo resolved into public/<lang>/gallery-metadata.json.
#
# Cost: ~3m40s per build for 4,161 files / 7.6 GB, so ~7m30s per deploy. It is
# deterministic — a second run leaves every file byte-identical — so rsync has
# nothing extra to transfer because of it. `--check` then reads every served file
# back and refuses to ship if any of them is missing its photo's UUID.
#
# Nothing here writes to the photo store. See CLAUDE.md "Build / Deploy" and
# docs/concepts/gallery-metadata-single-source.md.

set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

ONION="http://lnadevwj2vzomixiunv7i4lahwpoxh6zw56cxbce3uui5ijmwt4czpyd.onion"
REMOTE="root@lna-dev.net"

# Where the Web-Services deploy puts the two nginx compose projects that serve
# the sites (Web-Services/homepage and Web-Services/homepage-tor).
SERVICES="/home/lnadev/services-v2"

# $1 = site directory on the server, $2 = compose project, $3 = its nginx service.
#
# The reload is for the gallery redirect map (/_nginx/gallery-image-redirects.map,
# docs/concepts/gallery-metadata-yaml-only.md §5): nginx reads it only when it
# loads its config, so a new map does nothing until the next reload. `nginx -t`
# runs first and refuses a config that would not load — the reload never happens
# then, the old config keeps serving, and `set -e` stops the deploy loudly. On a
# deploy that did not change the map the reload is a graceful no-op.
publish() {
  python3 scripts/gallery-embed-metadata.py
  python3 scripts/gallery-embed-metadata.py --check
  rsync -avz --delete public/ "${REMOTE}:$1"
  ssh "$REMOTE" "cd ${SERVICES}/$2 && docker compose exec -T $3 sh -c 'nginx -t && nginx -s reload'"
}

# The gate. `npm test` runs all four layers of docs/concepts/testing.md against
# its own build in .test-site/ — the build itself with warnings counted as
# failures, the Python unit tests, the static checks over the built site, and the
# browser scenarios. A failure here stops the script before anything is written
# to the server, because `set -e` is on.
npm test

# The artefact, as before, with --panicOnWarning: the test build deliberately
# collects every warning so the report can show them all at once, but here the
# first one is reason enough to stop.
#
# --cleanDestinationDir empties public/ (everything that is not in static/)
# before rendering. A plain `hugo` overwrites but never deletes, so every page
# that stops being generated stays behind — a reworded photo title under
# `hugo server` once left 14 half-typed photo pages there (`vad-f/`, …) with
# localhost links in them, and `rsync --delete` would have shipped them. The
# image cache is resources/_gen/, which this does not touch: the cost is copying
# the ~1 GB of variants back out of it, seconds.
hugo --cleanDestinationDir --panicOnWarning --printI18nWarnings --printPathWarnings

# The one check that can catch a stale or development build in the artefact
# itself: the same static project, run over the very files rsync is about to
# ship, with the production base URL. It costs about two seconds and would have
# refused the `hugo server` output that used to sit in public/. With SITE_DIR
# set, the project drops its dependency on `build` and rebuilds nothing.
SITE_DIR=public SITE_BASE=https://lna-dev.net npx playwright test --project static

publish /mnt/homepage/homepage-site-data homepage homepage

# The Tor build has to come out of hugo and be reachable; that is the whole
# requirement. No second test pass, no clearnet-leak policy. Cleaned for the same
# reason as above: nothing of the clearnet build may survive into the onion one.
hugo -b "$ONION" --cleanDestinationDir --panicOnWarning --printI18nWarnings --printPathWarnings
publish /mnt/homepage/homepage-tor-site-data homepage-tor nginx
