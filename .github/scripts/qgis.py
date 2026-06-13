#!/usr/bin/env python3
"""
AIP Coordinate Pair → QGIS Converter
Converts NDDMMSS.mmm EDDDMMSS.mmm coordinate pair format to:
  - WKT CSV (lines)      → import via Add Delimited Text Layer
  - GeoJSON (lines)      → drag-and-drop into QGIS
  - GeoJSON (polygon)    → if points form a closed boundary

Usage:
    python aip_to_qgis.py input.txt [--format wkt|geojson|polygon] [--output out.csv]

Input format expected (any whitespace/column layout):
    [Label]  N034.39.13.000 E041.07.21.000 N034.41.30.000 E041.09.00.000
    Lines with two coordinate pairs per line become line segments.
    Label (anything before the first N/S coordinate) is captured as an attribute.
"""

import re
import json
import argparse
import sys
from pathlib import Path


# ── Coordinate parsing ────────────────────────────────────────────────────────

COORD_RE = re.compile(
    r'([NS])(\d{2,3})\.(\d{2})\.(\d{2}\.\d+)\s+'
    r'([EW])(\d{2,3})\.(\d{2})\.(\d{2}\.\d+)'
)

def dms_to_dd(deg, minu, sec, hemi):
    """Degrees-minutes-seconds → decimal degrees."""
    dd = float(deg) + float(minu) / 60 + float(sec) / 3600
    if hemi in ('S', 'W'):
        dd = -dd
    return round(dd, 8)

def parse_coord(ns, dlat, mlat, slat, ew, dlon, mlon, slon):
    lat = dms_to_dd(dlat, mlat, slat, ns)
    lon = dms_to_dd(dlon, mlon, slon, ew)
    return (lon, lat)   # GeoJSON / WKT order: X (lon), Y (lat)

def extract_segments(text):
    """
    Parse all lines, returning list of:
        { 'label': str, 'p1': (lon,lat), 'p2': (lon,lat) }
    Lines with only one coordinate pair are skipped.
    """
    segments = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        matches = list(COORD_RE.finditer(line))
        if len(matches) < 2:
            continue
        # Everything before the first coordinate match is the label
        label_end = matches[0].start()
        label = line[:label_end].strip() or ""
        p1 = parse_coord(*matches[0].groups())
        p2 = parse_coord(*matches[1].groups())
        segments.append({'label': label, 'p1': p1, 'p2': p2})
    return segments


# ── Output formatters ─────────────────────────────────────────────────────────

def to_wkt_csv(segments):
    lines = ['label,wkt']
    for s in segments:
        lbl = s['label'].replace('"', '""')
        x1, y1 = s['p1']
        x2, y2 = s['p2']
        wkt = f'LINESTRING ({x1} {y1}, {x2} {y2})'
        lines.append(f'"{lbl}","{wkt}"')
    return '\n'.join(lines)

def to_geojson_lines(segments):
    features = []
    for s in segments:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': [list(s['p1']), list(s['p2'])]
            },
            'properties': {'label': s['label']}
        })
    return json.dumps({'type': 'FeatureCollection', 'features': features}, indent=2)

def to_geojson_polygon(segments):
    """
    Attempt to chain segments into a polygon ring.
    Falls back to a MultiLineString if segments don't chain cleanly.
    """
    if not segments:
        return '{}'

    # Build adjacency: try to walk a chain
    SNAP = 6  # decimal places to snap endpoints

    def key(p):
        return (round(p[0], SNAP), round(p[1], SNAP))

    # Build a map: start_point → segment
    remaining = list(segments)
    ring = [remaining[0]['p1'], remaining[0]['p2']]
    remaining.pop(0)

    max_iter = len(remaining) * 2
    iterations = 0
    while remaining and iterations < max_iter:
        iterations += 1
        tail = key(ring[-1])
        found = False
        for i, seg in enumerate(remaining):
            if key(seg['p1']) == tail:
                ring.append(seg['p2'])
                remaining.pop(i)
                found = True
                break
            elif key(seg['p2']) == tail:
                ring.append(seg['p1'])
                remaining.pop(i)
                found = True
                break
        if not found:
            break  # chain broken

    if remaining:
        print(f"  ⚠  {len(remaining)} segment(s) couldn't be chained — "
              "outputting as MultiLineString instead.", file=sys.stderr)
        coords = [[list(s['p1']), list(s['p2'])] for s in segments]
        feature = {
            'type': 'Feature',
            'geometry': {'type': 'MultiLineString', 'coordinates': coords},
            'properties': {}
        }
    else:
        # Close the ring if not already closed
        if key(ring[0]) != key(ring[-1]):
            ring.append(ring[0])
        feature = {
            'type': 'Feature',
            'geometry': {'type': 'Polygon', 'coordinates': [[list(p) for p in ring]]},
            'properties': {}
        }

    return json.dumps({'type': 'FeatureCollection', 'features': [feature]}, indent=2)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Convert AIP NDDMMSS coordinate pairs to QGIS-ready formats.'
    )
    parser.add_argument('input', help='Input .txt file with coordinate pairs')
    parser.add_argument(
        '--format', choices=['wkt', 'geojson', 'polygon'], default='geojson',
        help='Output format: wkt (CSV), geojson (lines), polygon (closed ring). Default: geojson'
    )
    parser.add_argument('--output', help='Output file path (default: auto-named)')
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"Error: file not found: {src}", file=sys.stderr)
        sys.exit(1)

    text = src.read_text(encoding='utf-8', errors='replace')
    segments = extract_segments(text)
    print(f"  Parsed {len(segments)} line segment(s).")

    if not segments:
        print("No coordinate pairs found. Check input format.", file=sys.stderr)
        sys.exit(1)

    fmt = args.format
    if fmt == 'wkt':
        ext = '.csv'
        content = to_wkt_csv(segments)
    elif fmt == 'polygon':
        ext = '_polygon.geojson'
        content = to_geojson_polygon(segments)
    else:
        ext = '_lines.geojson'
        content = to_geojson_lines(segments)

    out_path = Path(args.output) if args.output else src.with_name(src.stem + ext)
    out_path.write_text(content, encoding='utf-8')
    print(f"  Written → {out_path}")

    # QGIS import hint
    if fmt == 'wkt':
        print("\nQGIS import: Layer → Add Layer → Add Delimited Text Layer")
        print("  Set geometry column to 'wkt', CRS to EPSG:4326")
    else:
        print("\nQGIS import: drag the .geojson file onto the QGIS canvas, or")
        print("  Layer → Add Layer → Add Vector Layer → select the file")


if __name__ == '__main__':
    main()