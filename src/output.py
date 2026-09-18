"""Print results as text, JSON or CSV."""

import csv
import json
import sys
from pathlib import Path

from . import extractors, fileinfo

LIST_FIELDS = ["hyperlinks", "embedded_objects", "macros"]

CSV_COLUMNS = (
    ["file", "type", "sha256"]
    + [f"filesystem.{name}" for name in fileinfo.FILESYSTEM_FIELDS]
    + [f"metadata.{name}" for name in extractors.METADATA_FIELDS]
    + LIST_FIELDS
    + ["warnings"]
)


def print_json(results):
    json.dump(results, sys.stdout, indent=2, ensure_ascii=False)
    print()


def print_csv(results):
    writer = csv.DictWriter(sys.stdout, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for result in results:
        row = {"file": result["file"], "type": result["type"], "sha256": result["sha256"]}
        for group in ("filesystem", "metadata"):
            for name, value in result[group].items():
                row[f"{group}.{name}"] = value
        for name in LIST_FIELDS:
            row[name] = "; ".join(result[name] or [])
        row["warnings"] = "; ".join(result["warnings"])
        writer.writerow(row)


def print_text(results, skipped):
    for result in results:
        print_result(result)
        print()

    if skipped:
        print("skipped:")
        for result in skipped:
            print(f"  {result['file']}  ({'; '.join(result['warnings'])})")
        print()

    print(f"scanned: {len(results)}, skipped: {len(skipped)}")


def print_result(result):
    print(f"{Path(result['file']).name}  ({result['type'] or 'unsupported'})")
    file_info = {"path": result["file"], "sha256": result["sha256"], **result["filesystem"]}
    print_section("file", file_info)
    print_section("document metadata", result["metadata"])
    print_list("hyperlinks", result["hyperlinks"])
    print_list("embedded objects", result["embedded_objects"])
    print_list("macro parts", result["macros"])
    for warning in result["warnings"]:
        print(f"  warning: {warning}")


def print_list(heading, values):
    if not values:
        return
    print(f"  {heading}:")
    for value in values:
        print(f"    {value}")


def print_section(heading, values):
    present = {name: value for name, value in values.items() if value not in (None, "")}
    if not present:
        return
    print(f"  {heading}:")
    width = max(len(name) for name in present)
    for name, value in present.items():
        print(f"    {name:<{width}}  {value}")
