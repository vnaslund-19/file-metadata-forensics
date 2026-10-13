"""Print results as text, JSON or CSV, to the screen or a file."""

import csv
import json
import sys
from pathlib import Path

from . import fileinfo, scan

LIST_FIELDS = [
    "hyperlinks",
    "external_relationships",
    "embedded_objects",
    "macros",
    "javascript",
    "received",
    "mime_parts",
]

CSV_COLUMNS = (
    ["file", "type", "sha256"]
    + [f"filesystem.{name}" for name in fileinfo.FILESYSTEM_FIELDS]
    + [f"metadata.{name}" for name in scan.METADATA_FIELDS]
    + LIST_FIELDS
    + ["warnings"]
)


def print_json(results, stream=sys.stdout):
    json.dump(results, stream, indent=2, ensure_ascii=False)
    print(file=stream)


def print_csv(results, stream=sys.stdout):
    writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for result in results:
        row = {"file": result["file"], "type": result["type"], "sha256": result["sha256"]}
        for group in ("filesystem", "metadata"):
            for name, value in result[group].items():
                row[f"{group}.{name}"] = value
        for name in LIST_FIELDS:
            row[name] = "; ".join(as_text(item) for item in result[name] or [])
        row["warnings"] = "; ".join(result["warnings"])
        writer.writerow(row)


def print_text(results, skipped, stream=sys.stdout):
    for result in results:
        print_result(result, stream)
        print(file=stream)

    if skipped:
        print("skipped:", file=stream)
        for result in skipped:
            print(f"  {result['file']}  ({'; '.join(result['warnings'])})", file=stream)
        print(file=stream)

    print(f"scanned: {len(results)}, skipped: {len(skipped)}", file=stream)


def print_result(result, stream):
    print(f"{Path(result['file']).name}  ({result['type']})", file=stream)
    file_info = {"path": result["file"], "sha256": result["sha256"], **result["filesystem"]}
    print_section("file", file_info, stream)
    print_section("metadata", result["metadata"], stream)
    print_list("hyperlinks", result["hyperlinks"], stream)
    print_list("external relationships", result["external_relationships"], stream)
    print_list("attachments and embedded objects", result["embedded_objects"], stream)
    print_list("macro parts", result["macros"], stream)
    print_list("javascript", result["javascript"], stream)
    print_list("received (newest first)", result["received"], stream)
    print_list("mime structure", result["mime_parts"], stream)
    for warning in result["warnings"]:
        print(f"  warning: {warning}", file=stream)


def print_list(heading, values, stream):
    if not values:
        return
    print(f"  {heading}:", file=stream)
    for value in values:
        print(f"    {as_text(value)}", file=stream)


def as_text(value):
    """An external relationship is a type and a target, everything else is a string."""
    if isinstance(value, dict):
        return f"{value['type']}  {value['target']}"
    return str(value)


def print_section(heading, values, stream):
    present = {name: value for name, value in values.items() if value not in (None, "")}
    if not present:
        return
    print(f"  {heading}:", file=stream)
    width = max(len(name) for name in present)
    for name, value in present.items():
        print(f"    {name:<{width}}  {value}", file=stream)
