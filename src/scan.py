"""Scan a directory and extract metadata from the files in it."""

import zipfile
from pathlib import Path

from . import extractors, fileinfo, ooxml, pdf

OOXML_TYPES = ("docx", "xlsx", "pptx")


def find_files(directory, recursive=False):
    """Return the supported files, unsupported files and folders that couldn't be opened."""
    files = []
    unreadable = []

    def could_not_open(error):
        unreadable.append(error.filename)

    for folder, _, names in Path(directory).walk(on_error=could_not_open):
        files.extend(folder / name for name in names)
        if not recursive:
            break

    files = sorted(path for path in files if path.is_file())
    supported = [path for path in files if fileinfo.file_type(path)]
    unsupported = [path for path in files if not fileinfo.file_type(path)]
    return supported, unsupported, unreadable


def new_result(path):
    """A result with every field empty, so all results have the same shape."""
    path = Path(path)
    return {
        "file": str(path.resolve()),
        "type": fileinfo.file_type(path),
        "sha256": None,
        "filesystem": dict.fromkeys(fileinfo.FILESYSTEM_FIELDS),
        "metadata": dict.fromkeys(extractors.METADATA_FIELDS),
        # None means the file was never checked for these, an empty list means
        # it was checked and none were found.
        "hyperlinks": None,
        "external_relationships": None,
        "embedded_objects": None,
        "macros": None,
        "javascript": None,
        "warnings": [],
    }


def skipped(path, reason):
    result = new_result(path)
    result["warnings"].append(reason)
    return result


def extract_metadata(path):
    """Extract file info and document metadata. Problems become warnings, not crashes."""
    result = new_result(path)

    try:
        result["filesystem"] = fileinfo.describe(path)
        result["sha256"] = fileinfo.sha256(path)
    except OSError as error:
        result["warnings"].append(f"could not read file: {error.strerror}")
        return result

    if result["type"] is None:
        result["warnings"].append("unsupported file type")
        return result

    if result["type"] == "pdf":
        add_pdf_details(result, path)
        return result

    from_library, result["warnings"] = extractors.extract(path, result["type"])
    if from_library is not None:
        result["metadata"] = from_library
    add_container_details(result, path, from_library)
    return result


def add_pdf_details(result, path):
    """Add everything a PDF holds: metadata, links, attachments and JavaScript."""
    try:
        details, warnings = pdf.inspect(path)
    except Exception as error:
        result["warnings"].append(f"could not read pdf metadata: {error}")
        return

    result["metadata"].update(details["metadata"])
    result["hyperlinks"] = details["hyperlinks"]
    result["embedded_objects"] = details["embedded_objects"]
    result["javascript"] = details["javascript"]
    result["warnings"] += warnings


def add_container_details(result, path, from_library):
    """Add what the ZIP container holds.

    Where the library also read the properties, the two readings are compared.
    Where it could not open the file, the properties come from the XML instead.
    """
    try:
        details, warnings = ooxml.inspect(path)
    except (OSError, zipfile.BadZipFile) as error:
        result["warnings"].append(f"could not read the archive: {error}")
        return

    result["metadata"].update(
        {name: value or None for name, value in details["app_properties"].items()}
    )
    result["hyperlinks"] = details["hyperlinks"]
    result["external_relationships"] = details["external_relationships"]
    result["embedded_objects"] = details["embedded_objects"]
    result["macros"] = details["macros"]
    result["warnings"] += warnings

    if from_library is None:
        result["metadata"].update(ooxml.as_library_values(details["core_properties"]))
        result["warnings"].append("core properties were read from the XML, not the library")
    else:
        result["warnings"] += ooxml.compare_with_library(
            details["core_properties"], result["metadata"]
        )
