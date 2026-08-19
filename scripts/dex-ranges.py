#!/usr/bin/env python3
"""Fetch the dex map data and store it inside the repo.

A species page draws its distribution map entirely from this site — no tile
server, no CDN — so the page works on the Tor onion build and makes no
third-party request until the visitor presses "detailed map". That needs two
things committed here:

  assets/data/dex/world-land.geojson     Natural Earth 110m land polygons
  assets/data/dex/world-borders.geojson  Natural Earth 110m country outlines
  assets/data/dex/world-ocean.geojson    Natural Earth 110m ocean, used as a
                                         mask that clips a terrestrial range
                                         back to the coastline
  assets/data/dex/ranges/<slug>.geojson  iNaturalist modelled species ranges

Natural Earth is public domain; the iNaturalist Open Range Map Dataset is
CC BY 4.0 and both are credited in the map footer.

Raw iNaturalist ranges are ~200–450 KB each, which would be ~50 MB over the
whole dex. They are therefore run through Ramer–Douglas–Peucker simplification,
rounded to `--precision` decimals (2 ≈ 1 km, far finer than a world map needs)
and stripped of properties. Anything still above `--max-kb` after that is
skipped rather than committed, and reported — a species without a local range
file simply renders without the range layer.

Standard library only.

Usage:
    python3 scripts/dex-ranges.py --world-only
    python3 scripts/dex-ranges.py --dry-run
    python3 scripts/dex-ranges.py
    python3 scripts/dex-ranges.py --only red-fox --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dex_common import REPO_ROOT, http_get, load_dex  # noqa: E402

DATA_DIR = REPO_ROOT / "assets" / "data" / "dex"
RANGE_DIR = DATA_DIR / "ranges"

NE_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson"
NE_LAND = f"{NE_BASE}/ne_110m_land.geojson"
NE_COUNTRIES = f"{NE_BASE}/ne_110m_admin_0_countries.geojson"
NE_OCEAN = f"{NE_BASE}/ne_110m_ocean.geojson"
INAT_RANGE = "https://inaturalist-open-data.s3.us-east-1.amazonaws.com/geomodel/geojsons/latest"


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def _perpendicular_distance(point, start, end):
    (px, py), (x1, y1), (x2, y2) = point, start, end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
    return abs(dy * px - dx * py + x2 * y1 - y2 * x1) / ((dx * dx + dy * dy) ** 0.5)


def simplify(points, tolerance):
    """Ramer–Douglas–Peucker, iterative so deep rings cannot blow the stack."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        index, furthest = -1, 0.0
        for i in range(first + 1, last):
            distance = _perpendicular_distance(points[i], points[first], points[last])
            if distance > furthest:
                index, furthest = i, distance
        if furthest > tolerance:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    return [point for point, wanted in zip(points, keep) if wanted]


def ring_area(ring):
    """Shoelace area in square degrees — only used to drop specks."""
    total = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def clean_ring(ring, tolerance, precision, min_area):
    ring = simplify([(float(x), float(y)) for x, y in ring], tolerance)
    ring = [(round(x, precision), round(y, precision)) for x, y in ring]

    deduped = []
    for point in ring:
        if not deduped or point != deduped[-1]:
            deduped.append(point)
    if len(deduped) >= 3 and deduped[0] != deduped[-1]:
        deduped.append(deduped[0])
    if len(deduped) < 4:
        return None
    if ring_area(deduped) < min_area:
        return None
    return [[x, y] for x, y in deduped]


def clean_geometry(geometry, tolerance, precision, min_area):
    kind = geometry.get("type")

    if kind == "Polygon":
        rings = [clean_ring(r, tolerance, precision, min_area) for r in geometry["coordinates"]]
        rings = [r for r in rings if r]
        return {"type": "Polygon", "coordinates": rings} if rings else None

    if kind == "MultiPolygon":
        polygons = []
        for polygon in geometry["coordinates"]:
            rings = [clean_ring(r, tolerance, precision, min_area) for r in polygon]
            rings = [r for r in rings if r]
            if rings:
                polygons.append(rings)
        return {"type": "MultiPolygon", "coordinates": polygons} if polygons else None

    if kind == "GeometryCollection":
        parts = [
            clean_geometry(g, tolerance, precision, min_area)
            for g in geometry.get("geometries", [])
        ]
        parts = [p for p in parts if p]
        return {"type": "GeometryCollection", "geometries": parts} if parts else None

    return None


def clean_document(document, tolerance, precision, min_area):
    """Reduce any GeoJSON document to a bare geometry-only FeatureCollection."""
    geometries = []
    kind = document.get("type")
    if kind == "FeatureCollection":
        for feature in document.get("features", []):
            if feature.get("geometry"):
                geometries.append(feature["geometry"])
    elif kind == "Feature":
        if document.get("geometry"):
            geometries.append(document["geometry"])
    else:
        geometries.append(document)

    features = []
    for geometry in geometries:
        cleaned = clean_geometry(geometry, tolerance, precision, min_area)
        if cleaned:
            features.append({"type": "Feature", "properties": {}, "geometry": cleaned})
    if not features:
        return None
    return {"type": "FeatureCollection", "features": features}


def write_geojson(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    return path.stat().st_size


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def fetch_world(args):
    targets = [
        ("world-land.geojson", NE_LAND, 0.08),
        ("world-borders.geojson", NE_COUNTRIES, 0.08),
        # Painted back over the range so a terrestrial species' polygon is
        # clipped to the coastline — iNaturalist's geomodel spills well out to
        # sea. Species flagged `marine: true` in dex.yaml skip this layer.
        ("world-ocean.geojson", NE_OCEAN, 0.08),
    ]
    for name, url, tolerance in targets:
        path = DATA_DIR / name
        if path.exists() and not args.force:
            print(f"  {name}: present ({path.stat().st_size / 1024:.0f} KB), skipping")
            continue
        raw = http_get(url, accept_json=False)
        if not raw:
            print(f"  {name}: FAILED to download")
            continue
        document = clean_document(
            json.loads(raw.decode("utf-8")), tolerance, args.precision, args.min_area
        )
        if not document:
            print(f"  {name}: nothing left after simplification")
            continue
        if args.dry_run:
            payload = json.dumps(document, separators=(",", ":"))
            print(f"  {name}: would write {len(payload) / 1024:.0f} KB")
            continue
        size = write_geojson(path, document)
        print(f"  {name}: {size / 1024:.0f} KB")


def fetch_ranges(args):
    species = load_dex()
    todo = [s for s in species if not args.only or s.get("slug") in args.only]

    written, skipped, missing, oversize = 0, 0, [], []
    total_bytes = 0

    for index, entry in enumerate(todo, 1):
        slug = entry.get("slug")
        taxon_id = entry.get("inat_taxon_id")
        path = RANGE_DIR / f"{slug}.geojson"

        if path.exists() and not args.force:
            total_bytes += path.stat().st_size
            skipped += 1
            continue
        if not taxon_id:
            missing.append(f"{slug} (no inat_taxon_id)")
            continue

        raw = http_get(f"{INAT_RANGE}/{taxon_id}.geojson", accept_json=False)
        if not raw:
            missing.append(f"{slug} (no range published)")
            continue

        try:
            source = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            missing.append(f"{slug} (unparseable)")
            continue

        # A globally distributed species carries far more coastline than a
        # local one, so rather than dropping its range layer we coarsen it
        # until it fits the budget. Islands go first, then detail.
        document, payload, kilobytes, tolerance = None, "", 0.0, args.tolerance
        for step in range(6):
            factor = 2 ** step
            document = clean_document(
                source, tolerance * factor, args.precision, args.min_area * factor
            )
            if not document:
                break
            payload = json.dumps(document, separators=(",", ":"), ensure_ascii=False)
            kilobytes = len(payload.encode("utf-8")) / 1024
            if kilobytes <= args.max_kb:
                tolerance = tolerance * factor
                break
        else:
            document = None

        if not document:
            missing.append(f"{slug} (empty after simplification)")
            continue
        if kilobytes > args.max_kb:
            oversize.append(f"{slug} ({kilobytes:.0f} KB > {args.max_kb} KB)")
            continue

        raw_kb = len(raw) / 1024
        coarse = " (coarsened)" if tolerance > args.tolerance else ""
        print(f"  [{index}/{len(todo)}] {slug}: {raw_kb:.0f} KB → {kilobytes:.0f} KB{coarse}")
        if not args.dry_run:
            total_bytes += write_geojson(path, document)
        else:
            total_bytes += len(payload)
        written += 1

    print()
    print(f"written  : {written}")
    print(f"unchanged: {skipped}")
    print(f"no range : {len(missing)}")
    for item in missing:
        print(f"    - {item}")
    if oversize:
        print(f"too large (skipped, species renders without a range layer): {len(oversize)}")
        for item in oversize:
            print(f"    ! {item}")
    print(f"\nranges on disk: {total_bytes / 1024 / 1024:.1f} MB")



def audit_ranges():
    """Report the area each stored range covers, smallest first.

    iNaturalist's geomodel quality varies a lot by species. Most are sensible —
    the Galapagos giant tortoise really is 3 sq deg and the orca really is
    88,000 — but some come out far sparser than the animal's actual range, and
    the only way to notice is to compare. Red fox is the known example: 608 sq
    deg, against 7,748 for grey wolf and 25,189 for wild boar, so it renders as
    scattered coastal fragments. Nothing here can fix that; it is upstream data.
    """
    species = {s["slug"]: (s.get("names") or {}).get("en", s["slug"]) for s in load_dex()}
    rows = []
    for path in sorted(RANGE_DIR.glob("*.geojson")):
        document = json.loads(path.read_text(encoding="utf-8"))
        total = 0.0
        for feature in document.get("features", []):
            geometry = feature["geometry"]
            polygons = (
                geometry["coordinates"]
                if geometry["type"] == "MultiPolygon"
                else [geometry["coordinates"]]
            )
            for polygon in polygons:
                total += ring_area(polygon[0])
        rows.append((total, path.stem, path.stat().st_size / 1024))

    rows.sort()
    print(f"{len(rows)} ranges, by area covered (square degrees)\n")
    for area, slug, kilobytes in rows:
        print(f"  {area:10.1f}  {kilobytes:6.1f} KB  {slug}  ({species.get(slug, '?')})")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", action="append", default=[], help="Limit to these slugs")
    parser.add_argument("--world-only", action="store_true", help="Only fetch the base map")
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Report the area each stored range covers and exit — a range far "
             "smaller than the animal's real one means poor upstream geomodel data",
    )
    parser.add_argument("--force", action="store_true", help="Refetch files that already exist")
    parser.add_argument("--dry-run", action="store_true", help="Report sizes, write nothing")
    parser.add_argument(
        "--tolerance", type=float, default=0.06,
        help="Douglas–Peucker tolerance in degrees (default: 0.06, ≈6 km)",
    )
    parser.add_argument(
        "--precision", type=int, default=2,
        help="Decimal places kept per coordinate (default: 2, ≈1 km)",
    )
    parser.add_argument(
        "--min-area", type=float, default=0.01,
        help="Drop rings smaller than this many square degrees (default: 0.01)",
    )
    parser.add_argument(
        "--max-kb", type=float, default=45.0,
        help="Skip a species whose simplified range exceeds this size (default: 45)",
    )
    args = parser.parse_args(argv)

    if args.audit:
        return audit_ranges()

    print(f"base map -> {DATA_DIR.relative_to(REPO_ROOT)}")
    fetch_world(args)
    if args.world_only:
        return 0
    print(f"\nspecies ranges -> {RANGE_DIR.relative_to(REPO_ROOT)}")
    fetch_ranges(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
