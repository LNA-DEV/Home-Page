#!/usr/bin/env python3
"""Fetch one driving route once and commit it, for the {{< map >}} shortcode.

The shortcode used to hand its waypoints to leaflet-routing-machine, which asked
OSRM's public demo server for the route on every page view — from the visitor's
browser. A route through a finished trip never changes, so it is asked for once,
here, and stored in the repo:

  assets/data/maps/routes/<name>.geojson

A GeoJSON Feature with a LineString in [lng, lat] order: OSRM's full geometry,
thinned with Ramer–Douglas–Peucker to `--tolerance` degrees (default 0.0005,
~50 m) and rounded to 5 decimals (~1 m). OSRM's own "simplified" overview is
cut for the zoom that fits the whole route — 47 points for 1,365 km — and turns
angular as soon as you zoom in; this keeps the same drive to 1,170 points and
23 KB. The properties record where it came from. The shortcode reads it with
`route="<name>"` and inlines it into the page, so a map with a route makes no
request at all for it (docs/concepts/self-hosted-maps.md §7).

The route data is derived from OpenStreetMap (ODbL) through OSRM; the maps credit
both. One request per run, and the run waits a second afterwards, so a shell loop
over several routes stays within the demo server's limit of one request per
second. Standard library only; never runs git.

Usage:
    python3 scripts/map-route.py sverige-2024-kalmar-stockholm 56.671736,16.367111 59.302125,18.094136
    python3 scripts/map-route.py NAME LAT,LNG LAT,LNG [LAT,LNG ...] [--force] [--dry-run]
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROUTE_DIR = REPO_ROOT / "assets" / "data" / "maps" / "routes"

OSRM = "https://router.project-osrm.org/route/v1/driving"
USER_AGENT = "lna-dev.net map-route.py (+https://lna-dev.net)"
PRECISION = 5
TOLERANCE = 0.0005
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_point(text):
    """'lat,lng' → (lat, lng), checked for range."""
    try:
        lat_s, lng_s = text.split(",")
        lat, lng = float(lat_s), float(lng_s)
    except ValueError:
        raise ValueError(f"not a lat,lng pair: {text!r}") from None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError(f"out of range: {text!r}")
    return lat, lng


def osrm_url(points):
    """The request for a driving route through `points` ([(lat, lng), …]).

    OSRM takes lng,lat pairs separated by semicolons."""
    coords = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in points)
    return f"{OSRM}/{coords}?overview=full&geometries=geojson"


def _distance(point, start, end):
    """Perpendicular distance of `point` from the segment start–end, in degrees."""
    (x, y), (x1, y1), (x2, y2) = point, start, end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    return ((x - (x1 + t * dx)) ** 2 + (y - (y1 + t * dy)) ** 2) ** 0.5


def simplify(coordinates, tolerance=TOLERANCE):
    """Ramer–Douglas–Peucker, iterative: a 15,000-point drive would overflow the
    recursion limit. Keeps the first and last point."""
    if len(coordinates) < 3:
        return list(coordinates)
    keep = [False] * len(coordinates)
    keep[0] = keep[-1] = True
    stack = [(0, len(coordinates) - 1)]
    while stack:
        first, last = stack.pop()
        best, index = 0.0, None
        for i in range(first + 1, last):
            d = _distance(coordinates[i], coordinates[first], coordinates[last])
            if d > best:
                best, index = d, i
        if index is not None and best > tolerance:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    return [c for c, k in zip(coordinates, keep) if k]


def round_line(coordinates, precision=PRECISION):
    """Round [lng, lat] pairs and drop the consecutive duplicates rounding makes."""
    out = []
    for lng, lat in coordinates:
        point = [round(lng, precision), round(lat, precision)]
        if not out or out[-1] != point:
            out.append(point)
    return out


def route_feature(points, coordinates, fetched, tolerance=TOLERANCE):
    """The file's content: one Feature, its provenance in the properties."""
    return {
        "type": "Feature",
        "properties": {
            "source": "OSRM (router.project-osrm.org), OpenStreetMap data (ODbL)",
            "profile": "driving",
            "tolerance": tolerance,
            "waypoints": [[lat, lng] for lat, lng in points],
            "fetched": fetched,
        },
        "geometry": {"type": "LineString", "coordinates": round_line(simplify(coordinates, tolerance))},
    }


def fetch_route(points):
    req = urllib.request.Request(osrm_url(points), headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(f"OSRM answered {data.get('code')}: {data.get('message', '')}")
    return data["routes"][0]["geometry"]["coordinates"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("name", help="file name without extension, lowercase-with-dashes")
    ap.add_argument("points", nargs="+", help="lat,lng — at least two, in driving order")
    ap.add_argument("--tolerance", type=float, default=TOLERANCE, help=f"simplification in degrees (default {TOLERANCE})")
    ap.add_argument("--force", action="store_true", help="overwrite an existing route file")
    ap.add_argument("--dry-run", action="store_true", help="print the request and stop")
    args = ap.parse_args(argv)

    if not NAME_RE.match(args.name):
        ap.error(f"name must be lowercase-with-dashes: {args.name!r}")
    try:
        points = [parse_point(p) for p in args.points]
    except ValueError as exc:
        ap.error(str(exc))
    if len(points) < 2:
        ap.error("a route needs at least two points")

    target = ROUTE_DIR / f"{args.name}.geojson"
    if args.dry_run:
        print(osrm_url(points))
        print(f"→ {target.relative_to(REPO_ROOT)}")
        return 0
    if target.exists() and not args.force:
        print(f"{target.relative_to(REPO_ROOT)} exists; --force to replace it", file=sys.stderr)
        return 1

    try:
        coordinates = fetch_route(points)
    except (urllib.error.URLError, TimeoutError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"no route: {exc}", file=sys.stderr)
        return 1
    finally:
        time.sleep(1)  # the demo server's limit: one request per second

    feature = route_feature(points, coordinates, datetime.date.today().isoformat(), args.tolerance)
    ROUTE_DIR.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(feature, separators=(",", ":")) + "\n", encoding="utf-8")
    n = len(feature["geometry"]["coordinates"])
    print(f"{target.relative_to(REPO_ROOT)}: {n} points, {target.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
