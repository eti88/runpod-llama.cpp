#!/usr/bin/env python3
"""
Generate a CSV report listing all source files under a data directory and whether
they have corresponding outputs under an output directory.

Usage examples:
  python3 scripts/generate_elaboration_report.py \
      --data FabioTestOcr/data --output FabioTestOcr/output -o report.csv

Output columns (CSV):
  source_path, relative_path, basename, status, matched_outputs, notes

Matching is strict: an output corresponds only if it's in the same relative subdirectory as the source and has the same basename.

Status precedence: ELABORATED (has .csv) > TIMEOUT (has .timeout) > ERROR (has .error) > NOT_ELABORATED
"""

from __future__ import annotations
import argparse
import csv
import os
from datetime import datetime
from typing import List, Dict

COMMON_IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.pdf', '.bmp']


def iso_mtime(path: str) -> str:
    try:
        return datetime.fromtimestamp(os.path.getmtime(path)).isoformat(sep=' ', timespec='seconds')
    except Exception:
        return ''


def scan_outputs(output_dir: str) -> List[Dict]:
    outputs = []
    for root, _, files in os.walk(output_dir):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, output_dir)
            name, ext = os.path.splitext(os.path.basename(f))
            typ = ext.lower().lstrip('.')
            # classify known types
            if ext.lower() == '.csv':
                kind = 'csv'
            elif ext.lower() == '.timeout':
                kind = 'timeout'
            elif ext.lower() == '.error':
                kind = 'error'
            else:
                kind = 'other'
            outputs.append({
                'full': full,
                'rel': rel,
                'basename': name,
                'ext': ext.lower(),
                'kind': kind,
                'mtime': iso_mtime(full),
            })
    return outputs


def find_matches_for_source(src_rel: str, src_basename: str, outputs: List[Dict]) -> List[Dict]:
    # Strict matching but tolerant of wrapper folders like 'ftp' or 'data'.
    # We strip common leading wrapper segments from both source and output relative dirs
    # and only match when directory (after stripping) and basename are exact.
    SKIP_LEADING = {'ftp', 'data', 'source', 'files', 'input', 'in', 'out', 'output', 'tmp'}

    def strip_leading(path: str) -> str:
        parts = [p for p in path.split(os.sep) if p]
        for i, p in enumerate(parts):
            if p and p.lower() not in SKIP_LEADING:
                return os.sep.join(parts[i:])
        return ''

    matches = []
    src_dir = strip_leading(os.path.dirname(src_rel))
    for out in outputs:
        out_dir = strip_leading(os.path.dirname(out['rel']))
        if out_dir == src_dir and out['basename'] == src_basename:
            matches.append(out)
    return matches


def determine_status(match_kinds: List[str]) -> str:
    kinds = set(match_kinds)
    if 'csv' in kinds:
        return 'ELABORATED'
    # timeout should be preferred over generic error when no csv exists
    if 'timeout' in kinds:
        return 'TIMEOUT'
    if 'error' in kinds:
        return 'ERROR'
    return 'NOT_ELABORATED'


def generate_report(data_dir: str, output_dir: str, out_csv: str, exts: List[str], include_all: bool = False, delimiter: str = ',', sort_rows: bool = True, verbose: bool = False) -> int:
    outputs = scan_outputs(output_dir)
    if verbose:
        print(f"Found {len(outputs)} files under {output_dir}")

    rows = []
    total_sources = 0

    for root, _, files in os.walk(data_dir):
        for f in files:
            _, ext = os.path.splitext(f)
            # include_all overrides extension filtering
            if not include_all and ext.lower() not in exts:
                continue
            total_sources += 1
            full = os.path.join(root, f)
            rel = os.path.relpath(full, data_dir)
            basename = os.path.splitext(os.path.basename(f))[0]

            matches = find_matches_for_source(rel, basename, outputs)
            match_descs = []
            kinds = []
            for m in matches:
                match_descs.append(f"{m['rel']} ({m['kind']}, {m['mtime']})")
                kinds.append(m['kind'])

            status = determine_status(kinds)
            num_outputs = len(matches)
            has_output = num_outputs > 0

            parts = rel.split(os.sep)
            # skip generic top-level wrappers (ftp, data, etc.) to get the real category (e.g. 'PROTOCOLLO DENUNCE')
            skip = {'ftp', 'data', 'source', 'files', 'input', 'in', 'out', 'output', 'tmp'}
            idx = 0
            for i, p in enumerate(parts):
                if p and p.lower() not in skip:
                    idx = i
                    break
            category = parts[idx] if len(parts) > idx else ''
            # book_container is the next path segment after category (e.g. '1 protocollo denunce CA')
            book_container = parts[idx+1] if len(parts) > idx+1 else ''

            rows.append({
                'source_path': os.path.abspath(full),
                'relative_path': rel,
                'basename': basename,
                'category': category,
                'book_container': book_container,
                'status': status,
                'has_output': has_output,
                'num_outputs': num_outputs,
                'matched_outputs': '; '.join(match_descs),
                'notes': ''
            })

    # sort rows (default True)
    if sort_rows:
        rows.sort(key=lambda r: r['relative_path'])

    # write CSV
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['source_path', 'relative_path', 'basename', 'category', 'book_container', 'status', 'has_output', 'num_outputs', 'matched_outputs', 'notes']
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter, extrasaction='ignore')
        writer.writeheader()
        for r in rows:
            # ensure missing optional fields don't cause KeyError
            row = {k: r.get(k, '') for k in fieldnames}
            writer.writerow(row)

    # print a summary
    counts = {'ELABORATED': 0, 'ERROR': 0, 'TIMEOUT': 0, 'NOT_ELABORATED': 0}
    for r in rows:
        counts[r['status']] = counts.get(r['status'], 0) + 1

    # per-category summary
    cat_counts = {}
    for r in rows:
        cat = r.get('category') or 'UNKNOWN'
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    print(f"Wrote report to {out_csv} — scanned {total_sources} source files")
    print(', '.join([f"{k}: {v}" for k, v in counts.items()]))
    if verbose:
        print(f"Categories: {len(cat_counts)} (showing up to 10): " + ', '.join([f"{k}: {v}" for k, v in list(cat_counts.items())[:10]]))
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Generate elaboration report from data and output dirs')
    p.add_argument('--data', '-d', default='data', help='Path to data directory (default: data)')
    p.add_argument('--output', '-o', dest='output_dir', default='output', help='Path to output directory (default: output)')
    p.add_argument('--out-csv', '-O', default='elaboration_report.csv', help='Path to output CSV file (default: elaboration_report.csv)')
    p.add_argument('--exts', default=','.join(COMMON_IMAGE_EXTS), help=f"Comma-separated source extensions to include (default: {','.join(COMMON_IMAGE_EXTS)})")
    p.add_argument('--include-all', action='store_true', help='Include files with any extension (overrides --exts)')
    p.add_argument('--delimiter', default=',', help='CSV delimiter to use for output (default: ,)')
    p.add_argument('--no-sort', dest='sort', action='store_false', help='Do not sort rows by relative_path')
    p.add_argument('--verbose', '-v', action='store_true')
    return p.parse_args()


def main() -> None:
    args = parse_args()
    exts = [e.lower() if e.startswith('.') else f".{e.lower()}" for e in args.exts.split(',') if e]
    rc = generate_report(args.data, args.output_dir, args.out_csv, exts, include_all=args.include_all, delimiter=args.delimiter, sort_rows=args.sort, verbose=args.verbose)
    raise SystemExit(rc)


if __name__ == '__main__':
    main()
