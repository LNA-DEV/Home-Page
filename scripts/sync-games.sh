#!/usr/bin/env bash
#
# Run every game-library sync in sequence, fail-fast.
#
# Each child (sync-steam.py / sync-epic.py / sync-gog.py) owns only its own
# `platform:` slice of data/gaming.yaml, so they are independent and the order
# does not matter. If ANY child exits non-zero, this wrapper stops there and
# exits with that same status — nothing after the failing sync runs.
#
# (sync-gallery.py is intentionally NOT run here — it syncs the photo gallery,
# not games.)
#
# Any arguments given to this script are forwarded verbatim to EVERY child, so
# only pass flags all three accept — most usefully `--dry-run` and
# `--include-unplayed`. An Epic/GOG-only flag such as `--no-cloud` would make the
# Steam sync error out on an unknown argument, which — by design — fails the run.
#
# Devices (docs/concepts/gaming-devices.md): the same command runs on every
# machine with Heroic. Each machine's Heroic-local data lives in its own
# snapshot, sources/gaming-devices/<GAMING_DEVICE>.json; a run writes only this
# machine's snapshot and merges all of them, so no machine overwrites another.
# Before any sync writes, `gaming_devices.py check` validates every snapshot and
# this machine's export (device id set, nothing shrinking) — writing nothing
# itself. At the end, `gaming_devices.py status` lists the devices.
#
# This script runs no git command: pull before, review the diff and commit after,
# by hand.
#
# Usage:
#   scripts/sync-games.sh              # sync all three (writes data/gaming.yaml)
#   scripts/sync-games.sh --dry-run    # preview all three, write nothing
#   GAMING_DEVICE=laptop scripts/sync-games.sh   # override the device id from .env
#
# Does NOT deploy — ./deploy.sh remains a separate, explicitly-authorized step.

set -euo pipefail

# Resolve the scripts dir so this works no matter where it's invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

SYNCS=(
  sync-steam.py
  sync-epic.py
  sync-gog.py
)

echo "================================================================" >&2
echo ">>> gaming_devices.py check" >&2
echo "================================================================" >&2
"$PYTHON" "$SCRIPT_DIR/gaming_devices.py" check

for sync in "${SYNCS[@]}"; do
  echo "================================================================" >&2
  echo ">>> $sync $*" >&2
  echo "================================================================" >&2
  "$PYTHON" "$SCRIPT_DIR/$sync" "$@"
done

echo "================================================================" >&2
echo ">>> gaming_devices.py status" >&2
echo "================================================================" >&2
"$PYTHON" "$SCRIPT_DIR/gaming_devices.py" status >&2

echo "================================================================" >&2
echo "All game syncs completed. Eyeball 'git diff data/gaming.yaml sources/gaming-devices/'" >&2
echo "and run 'hugo' to sanity-check. Do NOT run ./deploy.sh — separate, authorized step." >&2
