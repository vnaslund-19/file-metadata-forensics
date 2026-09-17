"""Command line interface."""

import argparse
import sys
from pathlib import Path

from . import scan


def report(result):
    print(f"{result['file']['name']}  ({result['type'] or 'unsupported'})")
    print_section("file", result["file"])
    print_section("document metadata", result["metadata"])
    for warning in result["warnings"]:
        print(f"  warning: {warning}")


def print_section(heading, values):
    present = {name: value for name, value in values.items() if value not in (None, "")}
    if not present:
        return
    print(f"  {heading}:")
    width = max(len(name) for name in present)
    for name, value in present.items():
        print(f"    {name:<{width}}  {value}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Extract metadata from Office documents, PDFs and related files.",
    )
    parser.add_argument("path", type=Path, help="file or directory to scan")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="also scan subdirectories"
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if not args.path.exists():
        print(f"error: no such file or directory: {args.path}", file=sys.stderr)
        return 1

    if args.path.is_file():
        report(scan.extract_metadata(args.path))
        return 0

    supported, unsupported, unreadable = scan.find_files(args.path, args.recursive)
    for path in supported:
        report(scan.extract_metadata(path))
        print()

    print_paths("skipped, unsupported file type:", unsupported)
    print_paths("could not open folder:", unreadable)

    print(
        f"scanned: {len(supported)}, skipped: {len(unsupported)}, "
        f"folders not opened: {len(unreadable)}"
    )
    return 0


def print_paths(heading, paths):
    if not paths:
        return
    print(heading)
    for path in paths:
        print(f"  {path}")
    print()
