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

publish() {
  python3 scripts/gallery-embed-metadata.py
  python3 scripts/gallery-embed-metadata.py --check
  rsync -avz --delete public/ "${REMOTE}:$1"
}

hugo
publish /mnt/homepage/homepage-site-data

hugo -b "$ONION"
publish /mnt/homepage/homepage-tor-site-data
