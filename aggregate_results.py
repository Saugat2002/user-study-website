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

METHODS    = ['sd', 'ddpo', 'b2', 'ours']
METHODS_3D = ['sd', 'ddpo', 'b2', 'ours', 'none']


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


def build_output(counts, methods=None):
    if methods is None:
        methods = METHODS
    total = sum(counts[m] for m in methods)
    result = {}
    for m in methods:
        c = counts[m]
        result[m]            = f"{round(c / total * 100, 1)}%" if total else "0%"
        result[f"total_{m}"] = c
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
    counts_3d['none'] = 0  # ensure 'none' always appears in output

    # Per-sample aggregation across all files
    sample_2d = {}          # sample_idx -> counts dict
    sample_3d = {}
    prompts_2d_global = {}  # sample_idx -> prompt (2D only)

    # Per-file metrics
    per_file = {}

    skipped = 0

    for fname in sorted(json_files):
        path = os.path.join(input_dir, fname)
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"  [skip] {fname} — could not parse: {e}")
            skipped += 1
            continue

        # Per-file local counts
        c2d_file = empty_counts()
        c3d_file = empty_counts()
        c3d_file['none'] = 0

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
            sec2d = details.get('sec2d', {}) or {}
            sec3d = details.get('sec3d', {}) or {}

            # 2D section
            for idx, entry in sec2d.items():
                method = entry.get('preferred_method')
                if not method or method not in METHODS:
                    continue
                counts_2d[method] += 1
                c2d_file[method] += 1
                prompts_2d_global.setdefault(str(idx), entry.get('prompt', ''))
                if idx not in sample_2d:
                    sample_2d[idx] = empty_counts()
                sample_2d[idx][method] += 1

            # 3D section (includes 'none')
            for idx, entry in sec3d.items():
                method = entry.get('preferred_method')
                if not method or method not in METHODS_3D:
                    continue
                counts_3d[method] += 1
                c3d_file[method] += 1
                if idx not in sample_3d:
                    sample_3d[idx] = empty_counts()
                _ = sample_3d[idx]['none']  # ensure key exists
                sample_3d[idx][method] += 1

            total_2d = sum(c2d_file[m] for m in METHODS)
            total_3d = sum(c3d_file[m] for m in METHODS_3D)
            print(f"  {fname:40s}  2D: {total_2d} votes  3D: {total_3d} votes")

        else:
            # Format C — old flat details (all 2D)
            sec2d = details or {}
            for idx, entry in sec2d.items():
                method = entry.get('preferred_method')
                if not method or method not in METHODS:
                    continue
                counts_2d[method] += 1
                c2d_file[method] += 1
                prompts_2d_global.setdefault(str(idx), entry.get('prompt', ''))
                if idx not in sample_2d:
                    sample_2d[idx] = empty_counts()
                sample_2d[idx][method] += 1
            total_2d = sum(c2d_file[m] for m in METHODS)
            print(f"  {fname:40s}  2D: {total_2d} votes  (old format, no 3D)")

        # Store per-file metrics (percentages + totals) in output
        per_file[fname] = {
            "image": build_output(c2d_file, METHODS),
            "3d":    build_output(c3d_file, METHODS_3D),
        }

    print(f"\n{'─'*55}")
    print(f"  Files processed : {len(json_files) - skipped}")
    print(f"  Files skipped   : {skipped}")
    print(f"  Total 2D votes  : {sum(counts_2d[m] for m in METHODS)}")
    print(f"  Total 3D votes  : {sum(counts_3d[m] for m in METHODS_3D)}")
    print(f"{'─'*55}\n")

    # Build per-sample summaries
    per_sample_image = {}
    for idx, cnts in sorted(sample_2d.items(), key=lambda kv: int(kv[0])):
        obj = build_output(cnts, METHODS)
        obj["prompt"] = prompts_2d_global.get(str(idx), "")
        per_sample_image[idx] = obj

    per_sample_3d = {}
    for idx, cnts in sorted(sample_3d.items(), key=lambda kv: int(kv[0])):
        per_sample_3d[idx] = build_output(cnts, METHODS_3D)

    output = {
        "image":      build_output(counts_2d, METHODS),
        "3d":         build_output(counts_3d, METHODS_3D),
        "per_file":   per_file,
        "per_sample": {
            "image": per_sample_image,
            "3d":    per_sample_3d,
        },
    }

    output_str = json.dumps(output, indent=2)
    print(output_str)

    if out_file:
        with open(out_file, 'w') as f:
            f.write(output_str)
        print(f"\n[saved] {out_file}")


if __name__ == '__main__':
    main()
