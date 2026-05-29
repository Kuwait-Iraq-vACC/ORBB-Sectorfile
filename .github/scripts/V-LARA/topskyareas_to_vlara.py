#!/usr/bin/env python3
"""
topskyareas_to_vlara.py
-----------------------
Reads TopSky area definition files (.txt) from one or more input
directories and writes a single GeoJSON FeatureCollection to disk.

Each .txt file may define a polygon using COORD lines, or a circle
using a single CIRCLE line. Mixed use of both in the same file is
not permitted.

Usage:
    python topskyareas_to_vlara.py \
        --input-dir ".data/TopSky Shared/Areas/Danger" \
        --input-dir ".data/TopSky Shared/Areas/Prohibited" \
        --input-dir ".data/TopSky Shared/Areas/Restricted" \
        --input-dir ".data/TopSky Shared/Areas/MOA" \
        --output ".data/V-LARA/orbb.geojson" \
        --debug
"""

import argparse
import json
import math
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Coordinate conversion
# ---------------------------------------------------------------------------

# Matches DMS tokens such as N029.58.11.000 or E048.35.24.000
_DMS_RE = re.compile(r'^([NSEW])(\d{1,3})\.(\d{1,2})\.(\d{1,2}(?:\.\d+)?)$')


def dms_to_decimal(token: str) -> float:
    """
    Convert a DMS coordinate token to decimal degrees.
    Hemisphere S and W produce negative values.
    """
    match = _DMS_RE.match(token.strip())
    if not match:
        raise ValueError(f"Unrecognised coordinate token: {token!r}")
    hemi, deg, mnt, sec = match.groups()
    value = int(deg) + int(mnt) / 60.0 + float(sec) / 3600.0
    if hemi in ('S', 'W'):
        value = -value
    return value


def _parse_flexible(token: str) -> float:
    """Accept plain decimal degrees or DMS format."""
    try:
        return float(token)
    except ValueError:
        return dms_to_decimal(token)


def coord_pair(lat_token: str, lon_token: str) -> List[float]:
    """Return [longitude, latitude] as required by GeoJSON."""
    return [dms_to_decimal(lon_token), dms_to_decimal(lat_token)]


# ---------------------------------------------------------------------------
# Circle approximation
# ---------------------------------------------------------------------------

_EARTH_RADIUS_NM = 3440.065


def _dest_point(lat: float, lon: float, bearing: float, dist_nm: float):
    """
    Compute the destination point on a sphere given an origin (decimal degrees),
    a bearing (decimal degrees) and a distance (nautical miles).
    Returns (latitude, longitude) in decimal degrees.
    """
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    brg_r = math.radians(bearing)
    ang   = dist_nm / _EARTH_RADIUS_NM

    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    sin_ang = math.sin(ang)
    cos_ang = math.cos(ang)

    sin_lat2 = sin_lat * cos_ang + cos_lat * sin_ang * math.cos(brg_r)
    lat2     = math.asin(sin_lat2)
    lon2     = lon_r + math.atan2(
        math.sin(brg_r) * sin_ang * cos_lat,
        cos_ang - sin_lat * sin_lat2,
    )
    lon2 = (lon2 + math.pi) % (2 * math.pi) - math.pi
    return math.degrees(lat2), math.degrees(lon2)


def circle_to_ring(
    center_lat: float, center_lon: float,
    radius_nm: float, spacing_deg: float,
) -> List[List[float]]:
    """
    Approximate a circle as a closed GeoJSON polygon ring.
    Points are generated every `spacing_deg` degrees around the centre.
    """
    if not (0.1 <= radius_nm <= 9999.9):
        raise ValueError(f"Circle radius out of range: {radius_nm} NM")
    if not (0.1 <= spacing_deg <= 120.0):
        raise ValueError(f"Circle spacing out of range: {spacing_deg} deg")

    n    = max(3, math.ceil(360.0 / spacing_deg))
    step = 360.0 / n
    ring = []
    for i in range(n):
        lat, lon = _dest_point(center_lat, center_lon, i * step, radius_nm)
        ring.append([lon, lat])
    ring.append(ring[0])  # close
    return ring


def parse_circle_line(line: str) -> List[List[float]]:
    """Parse a CIRCLE:Lat:Lon:Radius:Spacing definition line."""
    parts = [p.strip() for p in line.split(':')]
    if len(parts) != 5 or parts[0].upper() != 'CIRCLE':
        raise ValueError(f"Malformed CIRCLE line: {line!r}")
    return circle_to_ring(
        center_lat  = _parse_flexible(parts[1]),
        center_lon  = _parse_flexible(parts[2]),
        radius_nm   = float(parts[3]),
        spacing_deg = float(parts[4]),
    )


# ---------------------------------------------------------------------------
# Altitude helpers
# ---------------------------------------------------------------------------

def parse_fl(value: str) -> int:
    """
    Parse a flight level string to an integer.
    SFC and GND map to 0; UNL and UNLIMITED map to 999.
    """
    normalised = value.strip().upper()
    if normalised in ('SFC', 'GND'):
        return 0
    if normalised in ('UNL', 'UNLIMITED'):
        return 999
    return int(normalised)


# ---------------------------------------------------------------------------
# Area file parser
# ---------------------------------------------------------------------------

def parse_area_file(path: Path, fallback_type: str) -> Dict[str, Any]:
    """
    Parse a single TopSky area definition file.

    Returns a dictionary with the following keys:
        name            str   – area identifier
        type            str   – airspace category
        lowerFL         int   – lower flight level limit
        upperFL         int   – upper flight level limit
        coords          list  – list of [lon, lat] pairs (closed ring)
        activePermanent bool  – True if ACTIVE:1 is set
    """
    name:             Optional[str]         = None
    area_type:        Optional[str]         = None
    lower_fl:         Optional[int]         = None
    upper_fl:         Optional[int]         = None
    poly_coords:      List[List[float]]     = []
    circle_coords:    List[List[float]]     = []
    has_coord_lines                         = False
    has_circle_line                         = False
    active_permanent                        = False

    try:
        with path.open('r', encoding='utf-8', errors='ignore') as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith(';'):
                    continue

                if line.startswith('AREA:'):
                    parts = line.split(':')
                    if len(parts) >= 3:
                        name = parts[-1].strip()

                elif line.startswith('CATEGORY:'):
                    _, val = line.split(':', 1)
                    area_type = val.strip()

                elif line.startswith('LIMITS:'):
                    parts = line.split(':')
                    if len(parts) >= 3:
                        lower_fl = parse_fl(parts[1])
                        upper_fl = parse_fl(parts[2])

                # Handle coordinates with OR without COORD: prefix
                elif line.startswith('COORD:'):
                    if has_circle_line:
                        raise ValueError(
                            f"{path.name}: cannot mix COORD and CIRCLE lines"
                        )
                    # Remove 'COORD:' prefix and process
                    coord_line = line[6:].strip()
                    parts = coord_line.split(':')
                    if len(parts) >= 2:
                        poly_coords.append(
                            coord_pair(parts[0].strip(), parts[1].strip())
                        )
                        has_coord_lines = True

                # Handle coordinate lines without COORD: prefix (direct coordinates)
                elif re.match(r'^[NS]\d{3}\.\d{2}\.\d{2}\.\d{3}:[EW]\d{3}\.\d{2}\.\d{2}\.\d{3}', line):
                    if has_circle_line:
                        raise ValueError(
                            f"{path.name}: cannot mix COORD and CIRCLE lines"
                        )
                    parts = line.split(':')
                    if len(parts) >= 2:
                        poly_coords.append(
                            coord_pair(parts[0].strip(), parts[1].strip())
                        )
                        has_coord_lines = True

                elif line.startswith('CIRCLE:'):
                    if has_coord_lines:
                        raise ValueError(
                            f"{path.name}: cannot mix COORD and CIRCLE lines"
                        )
                    circle_coords   = parse_circle_line(line)
                    has_circle_line = True

                elif line.startswith('ACTIVE:'):
                    _, val = line.split(':', 1)
                    if val.strip() == '1':
                        active_permanent = True

    except Exception as exc:
        print(f"WARNING: Error while parsing {path}: {exc}", file=sys.stderr)
        traceback.print_exc()

    if has_circle_line:
        final_coords = circle_coords
    else:
        final_coords = poly_coords
        if final_coords and final_coords[0] != final_coords[-1]:
            final_coords.append(final_coords[0])

    return {
        "name":            name or path.stem,
        "type":            area_type or fallback_type,
        "lowerFL":         lower_fl if lower_fl is not None else 0,
        "upperFL":         upper_fl if upper_fl is not None else 999,
        "coords":          final_coords,
        "activePermanent": active_permanent,
    }


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def collect_txt_files(directories: List[str]) -> List[Path]:
    """Recursively collect all .txt files under the given directories."""
    files: List[Path] = []
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            print(f"WARNING: Skipping missing directory: {path}", file=sys.stderr)
            continue
        files.extend(sorted(path.rglob('*.txt')))
    return files


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert TopSky area files to a V-LARA GeoJSON FeatureCollection."
    )
    parser.add_argument(
        '--input-dir', action='append', required=True,
        metavar='DIR',
        help='Directory to scan for .txt files. May be specified multiple times.',
    )
    parser.add_argument(
        '--output', required=True,
        metavar='FILE',
        help='Destination path for the output GeoJSON file.',
    )
    parser.add_argument(
        '--debug', action='store_true',
        help='Print additional diagnostic information.',
    )
    parser.add_argument(
        '--include-active', action='store_true',
        help='Include areas marked as permanently active (ACTIVE:1). By default they are skipped.',
    )
    args = parser.parse_args()

    source_files = collect_txt_files(args.input_dir)

    if args.debug:
        print(f"Located {len(source_files)} source file(s).")

    features: List[Dict[str, Any]] = []

    for file_path in source_files:
        # Use the parent folder name as a fallback type (e.g. Danger, Restricted)
        fallback = file_path.parent.name
        area     = parse_area_file(file_path, fallback)

        # Skip permanently active areas unless explicitly included
        if not args.include_active and area['activePermanent']:
            if args.debug:
                print(f"Skipping {file_path.name} — marked as permanently active.")
            continue

        if not area['coords']:
            if args.debug:
                print(f"Skipping {file_path.name} — no coordinates found.")
            continue

        features.append({
            "type": "Feature",
            "properties": {
                "name":    area["name"],
                "type":    area["type"],
                "lowerFL": area["lowerFL"],
                "upperFL": area["upperFL"],
            },
            "geometry": {
                "type":        "Polygon",
                "coordinates": [area["coords"]],
            },
        })

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with output_path.open('w', encoding='utf-8') as fh:
            json.dump(
                {"type": "FeatureCollection", "features": features},
                fh,
                ensure_ascii=False,
                indent=2,
            )
        print(f"GeoJSON written to {output_path} — {len(features)} feature(s) included.")
    except Exception as exc:
        print(f"ERROR: Could not write output file: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()