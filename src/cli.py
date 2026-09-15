"""Command line interface."""

import argparse
import sys
from pathlib import Path

from . import extractors, fileinfo


def analyse(path):
    """Filesystem facts and document metadata for one file."""
    file_type = fileinfo.file_type(path)
    result = {
        "file": fileinfo.describe(path),
        "type": file_type,
        "metadata": {},
        "warnings": [],
    }
    if file_type is None:
        result["warnings"].append("unsupported file type")
        return result

    metadata, warnings = extractors.extract(path, file_type)
    result["metadata"] = metadata
    result["warnings"] = warnings
    return result


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
    parser.add_argument("path", type=Path, help="file to analyse")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if not args.path.exists():
        print(f"error: no such file or directory: {args.path}", file=sys.stderr)
        return 1
    if args.path.is_dir():
        print("error: directory scanning is not implemented yet", file=sys.stderr)
        return 1

    report(analyse(args.path))
    return 0
