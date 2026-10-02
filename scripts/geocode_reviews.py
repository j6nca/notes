#!/usr/bin/env python3
"""Fill in `location: [lat, lng]` frontmatter for food reviews.

Reads the address from each review's `📌: [address](link)` line, geocodes it via
OpenStreetMap Nominatim, and writes the coordinates back into the frontmatter.
Reviews that already have a `location` are skipped, so each address is only
looked up once. Coordinates can be corrected by hand and won't be overwritten.

Usage: python3 scripts/geocode_reviews.py [--dry-run] [paths...]
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REVIEWS_DIR = Path(__file__).resolve().parent.parent / "docs" / "food" / "reviews"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "blog.j6n.ca review geocoder (https://github.com/j6nca/notes)"

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
ADDRESS_RE = re.compile(r"📌:\s*\[([^\]]+)\]")
LOCATION_RE = re.compile(r"^location:", re.M)

# Address fragments Nominatim tends to choke on: units, suites, floors.
UNIT_PATTERNS = [
    r"#\s*[\w-]+",
    r"\bUnit\s+[\w-]+",
    r"\bSuite\s+[\w-]+",
    r"\b\w+\s+Floor\b",
]


def simplify(address: str) -> str:
    for pattern in UNIT_PATTERNS:
        address = re.sub(pattern, "", address, flags=re.I)
    # "Highway 7 E" -> "Highway 7"; OSM doesn't name the direction on highways.
    address = re.sub(r"\b(Highway|Hwy)\s+(\d+)\s+[EWNS]\b", r"\1 \2", address, flags=re.I)
    address = re.sub(r"\s+,", ",", address)
    address = re.sub(r",\s*(,\s*)+", ", ", address)
    return re.sub(r"\s{2,}", " ", address).strip(" ,")


def drop_postal_code(address: str) -> str:
    # Canadian postal codes ("ON L3R 0G6" -> "ON"), US zips and trailing countries.
    address = re.sub(r"\s+[A-Z]\d[A-Z]\s?\d[A-Z]\d\b", "", address)
    address = re.sub(r"\s+\d{5}(-\d{4})?\b", "", address)
    address = re.sub(r",?\s*(United States|USA|Canada)$", "", address, flags=re.I)
    return address.strip(" ,")


def nominatim(query: str):
    params = urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": 1, "countrycodes": "ca,us"}
    )
    req = urllib.request.Request(
        f"{NOMINATIM_URL}?{params}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        results = json.load(resp)
    # Nominatim's usage policy allows at most 1 request per second.
    time.sleep(1.1)
    if not results:
        return None
    return round(float(results[0]["lat"]), 6), round(float(results[0]["lon"]), 6)


def geocode(address: str):
    tried = []
    for candidate in (address, simplify(address), drop_postal_code(simplify(address))):
        if candidate in tried:
            continue
        tried.append(candidate)
        coords = nominatim(candidate)
        if coords:
            return coords, candidate
    return None, None


def process(path: Path, dry_run: bool) -> str:
    text = path.read_text()
    fm = FRONTMATTER_RE.match(text)
    if not fm:
        return "skip (no frontmatter)"
    if LOCATION_RE.search(fm.group(1)):
        return "skip (has location)"
    addr = ADDRESS_RE.search(text)
    if not addr or addr.group(1).strip().lower() == "address":
        return "skip (no address)"

    coords, matched = geocode(addr.group(1).strip())
    if not coords:
        return f"FAILED to geocode {addr.group(1)!r}"

    if not dry_run:
        new_fm = fm.group(1) + f"\nlocation: [{coords[0]}, {coords[1]}]"
        path.write_text(text[: fm.start(1)] + new_fm + text[fm.end(1) :])
    return f"{coords} via {matched!r}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*", type=Path, help="review files (default: all)")
    ap.add_argument("--dry-run", action="store_true", help="don't write changes")
    args = ap.parse_args()

    paths = args.paths or sorted(
        p for p in REVIEWS_DIR.rglob("*.md") if p.name != "index.md"
    )
    failed = False
    for path in paths:
        result = process(path, args.dry_run)
        failed |= result.startswith("FAILED")
        print(f"{path.name}: {result}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
