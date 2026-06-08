#!/usr/bin/env python3

import json
import math
import os
import sys

GEOJSON_PATH = os.environ.get("GEOJSON_OUT", ".data/V-LARA/orbb.geojson")

try:
    with open(GEOJSON_PATH, "r", encoding="utf-8") as fh:
        fc = json.load(fh)
except Exception as exc:
    print(f"❌ Failed to read {GEOJSON_PATH}: {exc}", file=sys.stderr)
    sys.exit(1)

features = fc.get("features", [])
n = len(features)

minx = miny =  math.inf
maxx = maxy = -math.inf

for ft in features:
    coords = ft.get("geometry", {}).get("coordinates", [])
    if not coords:
        continue
    for lon, lat in coords[0]:
        if lon < minx: minx = lon
        if lon > maxx: maxx = lon
        if lat < miny: miny = lat
        if lat > maxy: maxy = lat

# Count by type
type_counts: dict = {}
for ft in features:
    t = ft.get("properties", {}).get("type", "Unknown")
    type_counts[t] = type_counts.get(t, 0) + 1

print("## ORBB Airspace GeoJSON")
print(f"- **File:** `{GEOJSON_PATH}`")
print(f"- **Total features:** {n}")

if type_counts:
    print("- **By type:**")
    for t, c in sorted(type_counts.items()):
        print(f"  - `{t}`: {c}")

if math.isfinite(minx):
    print(f"- **Bounding box:** [{minx:.5f}, {miny:.5f}, {maxx:.5f}, {maxy:.5f}]")
else:
    print("- **Bounding box:** N/A (no valid coordinates found)")