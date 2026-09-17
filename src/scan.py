"""Scan a directory and extract metadata from the files in it."""

from pathlib import Path

from . import extractors, fileinfo


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


def extract_metadata(path):
    """Extract file info and document metadata. Problems become warnings, not crashes."""
    path = Path(path)
    result = {
        "file": {"name": path.name, "path": str(path.resolve())},
        "type": fileinfo.file_type(path),
        "metadata": {},
        "warnings": [],
    }

    try:
        result["file"] = fileinfo.describe(path)
    except OSError as error:
        result["warnings"].append(f"could not read file: {error.strerror}")
        return result

    if result["type"] is None:
        result["warnings"].append("unsupported file type")
        return result

    metadata, warnings = extractors.extract(path, result["type"])
    result["metadata"] = metadata
    result["warnings"] = warnings
    return result
