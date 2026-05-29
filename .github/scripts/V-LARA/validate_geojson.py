#!/usr/bin/env python3
"""
validate_geojson.py
-------------------
Validates the built GeoJSON against a strict schema:
  - Must be a FeatureCollection
  - Every feature must have a Polygon geometry
  - Each polygon must have exactly one ring (no holes)
  - Every ring must be closed (first == last coordinate)

Reads the output path from the GEOJSON_OUT environment variable,
falling back to .data/V-LARA/orbb.geojson.

Exits with code 1 if any validation errors are found.
"""

import json
import os
import sys

GEOJSON_PATH = os.environ.get("GEOJSON_OUT", ".data/V-LARA/orbb.geojson")

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

try:
    with open(GEOJSON_PATH, "r", encoding="utf-8") as fh:
        fc = json.load(fh)
except Exception as exc:
    print(f"❌ Failed to read {GEOJSON_PATH}: {exc}", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Top-level checks
# ---------------------------------------------------------------------------

if fc.get("type") != "FeatureCollection":
    print("❌ Root object is not a FeatureCollection.", file=sys.stderr)
    sys.exit(1)

features = fc.get("features", [])
if not isinstance(features, list):
    print("❌ 'features' is not a list.", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Per-feature checks
# ---------------------------------------------------------------------------

errors = 0

for i, ft in enumerate(features):
    name = ft.get("properties", {}).get("name", f"feature[{i}]")

    geom = ft.get("geometry", {})

    if geom.get("type") != "Polygon":
        print(f"❌ {name}: geometry type is {geom.get('type')!r}, expected 'Polygon'.", file=sys.stderr)
        errors += 1
        continue

    rings = geom.get("coordinates")

    if not rings or not isinstance(rings, list):
        print(f"❌ {name}: 'coordinates' is missing or not a list.", file=sys.stderr)
        errors += 1
        continue

    if len(rings) != 1:
        print(
            f"❌ {name}: has {len(rings)} ring(s); only a single exterior ring (no holes) is allowed.",
            file=sys.stderr,
        )
        errors += 1
        continue

    ring = rings[0]

    if not ring:
        print(f"❌ {name}: ring is empty.", file=sys.stderr)
        errors += 1
        continue

    if ring[0] != ring[-1]:
        print(f"❌ {name}: ring is not closed (first != last coordinate).", file=sys.stderr)
        errors += 1

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

if errors:
    print(f"❌ Validation failed: {errors} issue(s) found.", file=sys.stderr)
    sys.exit(1)

print(f"✅ Validation passed: {len(features)} feature(s) checked.")