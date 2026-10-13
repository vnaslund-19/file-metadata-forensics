"""Command line interface."""

import argparse
import sys
from pathlib import Path

from . import __version__, fileinfo, output, scan

EXAMPLES = """\
supported files:
  Word, Excel, PowerPoint  .docx .docm .xlsx .xlsm .pptx .pptm
  PDF                      .pdf
  Email                    .eml
  Images                   .jpg .jpeg .png

examples:
  extract-metadata report.docx
  extract-metadata evidence/ -r
  extract-metadata evidence/ -r --json -o results.json
"""


def build_parser():
    parser = argparse.ArgumentParser(
        prog="extract-metadata",
        description="Extract metadata from documents, emails and images. "
        "Files are only read, never changed, opened or run.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="+", type=Path, metavar="path",
                        help="file or folder to scan")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="also scan subfolders")
    formats = parser.add_mutually_exclusive_group()
    formats.add_argument("--json", action="store_true", help="output JSON")
    formats.add_argument("--csv", action="store_true", help="output CSV")
    parser.add_argument("-o", "--output", type=Path, metavar="FILE",
                        help="write the results to FILE instead of the screen")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    files, skipped, missing = [], [], []
    for path in args.paths:
        if not path.exists():
            missing.append(path)
        elif path.is_file():
            if fileinfo.file_type(path):
                files.append(path)
            else:
                skipped.append(scan.skipped(path, "unsupported file type"))
        else:
            found, unsupported, unreadable = scan.find_files(path, args.recursive)
            files += found
            skipped += [scan.skipped(p, "unsupported file type") for p in unsupported]
            skipped += [scan.skipped(p, "could not open folder") for p in unreadable]

    for path in missing:
        print(f"error: {path}: no such file or folder", file=sys.stderr)
    if missing and not files and not skipped:
        return 1

    # Open the output first, so a bad path fails before a long scan.
    try:
        stream = open(args.output, "w", encoding="utf-8", newline="") if args.output else sys.stdout
    except OSError as error:
        print(f"error: cannot write to {args.output}: {error.strerror}", file=sys.stderr)
        return 1

    results = [scan.extract_metadata(path) for path in files]

    try:
        if args.json:
            output.print_json(results + skipped, stream)
        elif args.csv:
            output.print_csv(results + skipped, stream)
        else:
            output.print_text(results, skipped, stream)
    except BrokenPipeError:
        # The reader stopped early, such as `| head`. Nothing left to do.
        sys.stderr.close()
        return 0
    finally:
        if args.output:
            stream.close()

    if args.output:
        print(f"scanned: {len(results)}, skipped: {len(skipped)}, written to {args.output}",
              file=sys.stderr)
    return 1 if missing else 0
