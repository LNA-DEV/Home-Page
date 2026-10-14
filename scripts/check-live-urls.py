#!/usr/bin/env python3
"""Ask the LIVE site whether the image URLs and redirects just shipped work.

The test suite never reaches the network, so it cannot see the server -- and
that is exactly where this failed twice: a redirect that ended in a 404 (old
gallery store names went through the stem map to a `_hu_` hash that no longer
existed), and an nginx change that is silently not loaded because a single-file
bind mount needs a recreated container. deploy.sh runs this right after the
clearnet publish and its nginx reload, before the Tor build.
docs/concepts/stable-image-urls.md §7.3.

    python3 scripts/check-live-urls.py [SITE_DIR] [--base https://lna-dev.net]

It requests a DETERMINISTIC sample of the artefact just shipped -- every n-th
line of a sorted list, so two runs check the same URLs -- with HEAD, following
exactly one redirect by hand:

    gallery and other variants from SITE_DIR            200
    keys of the variant map (old `_hu_` names)          301 -> its target -> 200
    keys of the stem map (store stems, slugAliases)     301 -> its target -> 200
    the filename-era photo URLs with an underscore      200 (the alias page)
    `_hu_` names with a made-up hash, in no map         404, never a 301

A failure exits 1. The clearnet site is live by then, so this cannot prevent a
broken deploy; it reports one within seconds instead of weeks, and stops the
Tor build from being published on top of it. It checks the clearnet site only:
the onion serves the same files under the same nginx rules.

Standard library only.
"""

import argparse
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gallery_common import repo_root  # noqa: E402

SPEC_DIR_RE = re.compile(r"^(?:resize|fit|fill|crop)-[a-z0-9]+(?:-[a-z0-9]+)*$")
MAP_LINE_RE = re.compile(r'^"((?:[^"\\]|\\.)*)" (\S+);$')
USER_AGENT = "lna-dev-live-check/1 (+https://lna-dev.net; deploy self-check)"
# Never in any map: hex, but made of one repeated digit no hash will ever be.
MADE_UP_HASHES = ("0000000000000000", "1111111111111111", "fffffffffffffff0")


def sample(items, n):
    """Every k-th item of the sorted list, n at most: the same URLs every run."""
    items = sorted(items)
    if len(items) <= n:
        return items
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def read_map(path):
    out = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        m = MAP_LINE_RE.match(line)
        if m:
            out[re.sub(r'\\(["\\])', r"\1", m.group(1))] = m.group(2)
    return out


def variants(site):
    """Every file in a spec directory: (gallery URL paths, other URL paths)."""
    gallery, other = [], []
    for path in site.rglob("*"):
        if path.is_file() and SPEC_DIR_RE.match(path.parent.name):
            url = "/" + path.relative_to(site).as_posix()
            (gallery if url.startswith("/images/gallery/") else other).append(url)
    return gallery, other


def underscore_photo_urls(gallery_yaml):
    """/<lang>/gallery/photo/<alias>/ for every slugAlias with an underscore."""
    out = []
    for line in gallery_yaml.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^  slugAliases: \[(.*)\]\s*$", line)
        if m:
            for alias in (a.strip() for a in m.group(1).split(",")):
                if "_" in alias:
                    out += [f"/{lang}/gallery/photo/{alias}/" for lang in ("en", "de", "sv")]
    return out


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def head(url):
    """(status, Location or None) for one HEAD request, no redirect followed."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with OPENER.open(req, timeout=20) as resp:
            return resp.status, resp.headers.get("Location")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, str(e)


def encode(path):
    return quote(path, safe="/%")


def check(base, case):
    """One case: (path, expect, target). Returns a problem string or None."""
    path, expect, target = case
    url = urljoin(base, encode(path))
    status, location = head(url)
    if expect == 200:
        return None if status == 200 else f"{path}: {status}, expected 200"
    if expect == 404:
        return None if status == 404 else f"{path}: {status}{f' -> {location}' if location else ''}, expected 404"
    # 301 to `target`, which answers 200.
    if status != 301:
        return f"{path}: {status}, expected 301 -> {target}"
    got = unquote(urlsplit(urljoin(url, location or "")).path)
    if got != unquote(target):
        return f"{path}: 301 -> {got}, expected {unquote(target)}"
    status2, _ = head(urljoin(url, location))
    return None if status2 == 200 else f"{path}: 301 -> {got} -> {status2} (a redirect into a 404)"


def main(argv=None):
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("site", nargs="?", type=Path, default=root / "public",
                        help="the artefact just shipped (default: public/)")
    parser.add_argument("--base", default="https://lna-dev.net",
                        help="the live site (default: https://lna-dev.net)")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)

    site = args.site
    if not (site / "_nginx").is_dir():
        sys.exit(f"ERROR: no build at {site} (no _nginx/ maps) — run `hugo` first")
    base = args.base.rstrip("/") + "/"

    cases = []
    gallery, other = variants(site)
    cases += [(u, 200, None) for u in sample(gallery, 100)]
    cases += [(u, 200, None) for u in sample(other, 50)]

    vmap = read_map(site / "_nginx" / "image-variant-redirects.map")
    for key in sample(vmap, 100):
        # Any stem and extension reach the same line: nginx keys on dir + hash.
        d, h = key.rsplit("/", 1)
        cases.append((f"{d}/x{h}.jpg", 301, vmap[key]))

    smap = read_map(site / "_nginx" / "gallery-image-redirects.map")
    for i, key in enumerate(sample(smap, 50)):
        # Alternate the original and a variant: the spec directory is carried over.
        spec = "" if i % 2 == 0 else "fit-600x600/"
        cases.append((f"/images/gallery/{spec}{key}.jpg", 301, f"/images/gallery/{spec}{smap[key]}.jpg"))

    cases += [(u, 200, None) for u in sample(underscore_photo_urls(root / "data" / "gallery.yaml"), 60)]

    for h in MADE_UP_HASHES:
        cases.append((f"/images/gallery/x_hu_{h}.jpg", 404, None))
    cases.append((f"/images/books/covers/x_hu_{MADE_UP_HASHES[0]}.jpg", 404, None))

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        problems = [p for p in pool.map(lambda c: check(base, c), cases) if p]

    if problems:
        for p in problems[:40]:
            print(f"ERROR: {p}", file=sys.stderr)
        if len(problems) > 40:
            print(f"       … and {len(problems) - 40} more", file=sys.stderr)
        print(f"\n{len(problems)} of {len(cases)} live checks against {base} failed.", file=sys.stderr)
        return 1
    print(f"OK: {len(cases)} live checks against {base} — variants, both redirect maps, "
          "the underscore photo URLs and unknown hashes all answer as they should.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
