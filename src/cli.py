"""Command line interface."""

import argparse
import sys
from pathlib import Path

from . import output, scan


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Extract metadata from Office documents, PDFs and related files.",
    )
    parser.add_argument("path", type=Path, help="file or directory to scan")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="also scan subdirectories"
    )
    formats = parser.add_mutually_exclusive_group()
    formats.add_argument("--json", action="store_true", help="print results as JSON")
    formats.add_argument("--csv", action="store_true", help="print results as CSV")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if not args.path.exists():
        print(f"error: no such file or directory: {args.path}", file=sys.stderr)
        return 1

    if args.path.is_file():
        files, unsupported, unreadable = [args.path], [], []
    else:
        files, unsupported, unreadable = scan.find_files(args.path, args.recursive)

    results = [scan.extract_metadata(path) for path in files]
    skipped = [scan.skipped(path, "unsupported file type") for path in unsupported]
    skipped += [scan.skipped(path, "could not open folder") for path in unreadable]

    if args.json:
        output.print_json(results + skipped)
    elif args.csv:
        output.print_csv(results + skipped)
    else:
        output.print_text(results, skipped)
    return 0
