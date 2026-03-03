"""
aggregate_results.py
--------------------
Reads all result JSON files from a directory and outputs aggregated
preference statistics split by section (2D images and 3D images).

Usage:
    python aggregate_results.py                        # reads from ./sheet_results/
    python aggregate_results.py path/to/results/       # custom directory
    python aggregate_results.py --out summary.json     # write output to file

Output format:
{
  "image": {
    "sd":         "<percentage>%",
    "ddpo":       "<percentage>%",
    "b2":         "<percentage>%",
    "ours":       "<percentage>%",
    "total":      <total votes>,
    "total_sd":   <count>,
    "total_ddpo": <count>,
    "total_b2":   <count>,
    "total_ours": <count>
  },
  "3d": { ... same structure ... }
}
"""

import os
import sys
import json
from collections import defaultdict

METHODS = ['sd', 'ddpo', 'b2', 'ours']


def empty_counts():
    return defaultdict(int)


def aggregate_section(details_dict):
    """Count preferred_method votes from a {sampleIdx: {preferred_method: ...}} dict."""
    counts = empty_counts()
    for entry in details_dict.values():
        method = entry.get('preferred_method')
        if method:
            counts[method] += 1
    return counts


def build_output(counts):
    total = sum(counts[m] for m in METHODS)
    result = {}
    for m in METHODS:
        c = counts[m]
        result[m]             = f"{round(c / total * 100, 1)}%" if total else "0%"
        result[f"total_{m}"]  = c
    result["total"] = total
    return result


def main():
    # --- parse simple CLI args ---
    args      = sys.argv[1:]
    input_dir = 'sheet_results'
    out_file  = None

    i = 0
    while i < len(args):
        if args[i] == '--out' and i + 1 < len(args):
            out_file = args[i + 1]
            i += 2
        else:
            input_dir = args[i]
            i += 1

    if not os.path.isdir(input_dir):
        print(f"[error] Directory not found: {input_dir}")
        sys.exit(1)

    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    if not json_files:
        print(f"[error] No JSON files found in '{input_dir}'")
        sys.exit(1)

    print(f"Reading {len(json_files)} file(s) from '{input_dir}' ...\n")

    counts_2d = empty_counts()
    counts_3d = empty_counts()
    skipped   = 0

    for fname in sorted(json_files):
        path = os.path.join(input_dir, fname)
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [skip] {fname} — could not parse: {e}")
            skipped += 1
            continue

        # Detect format:
        # A) details-only:  { "sec2d": {...}, "sec3d": {...} }          (top-level keys)
        # B) new full:      { ..., "details": { "sec2d": {...}, ... } }
        # C) old full:      { ..., "details": { "1": {...}, "2": {...} } } (flat, all 2D)

        if 'sec2d' in data or 'sec3d' in data:
            # Format A — file IS the details object
            details = data
        else:
            details = data.get('details', {})

        if 'sec2d' in details or 'sec3d' in details:
            # Formats A & B
            c2d = aggregate_section(details.get('sec2d', {}))
            c3d = aggregate_section(details.get('sec3d', {}))
            for m in METHODS:
                counts_2d[m] += c2d[m]
                counts_3d[m] += c3d[m]
            total_2d = sum(c2d[m] for m in METHODS)
            total_3d = sum(c3d[m] for m in METHODS)
            print(f"  {fname:40s}  2D: {total_2d} votes  3D: {total_3d} votes")

        else:
            # Format C — old flat details (all 2D)
            c2d = aggregate_section(details)
            for m in METHODS:
                counts_2d[m] += c2d[m]
            total_2d = sum(c2d[m] for m in METHODS)
            print(f"  {fname:40s}  2D: {total_2d} votes  (old format, no 3D)")

    print(f"\n{'─'*55}")
    print(f"  Files processed : {len(json_files) - skipped}")
    print(f"  Files skipped   : {skipped}")
    print(f"  Total 2D votes  : {sum(counts_2d[m] for m in METHODS)}")
    print(f"  Total 3D votes  : {sum(counts_3d[m] for m in METHODS)}")
    print(f"{'─'*55}\n")

    output = {
        "image": build_output(counts_2d),
        "3d":    build_output(counts_3d),
    }

    output_str = json.dumps(output, indent=2)
    print(output_str)

    if out_file:
        with open(out_file, 'w') as f:
            f.write(output_str)
        print(f"\n[saved] {out_file}")


if __name__ == '__main__':
    main()
