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


def new_result(path):
    """A result with every field empty, so all results have the same shape."""
    path = Path(path)
    return {
        "file": str(path.resolve()),
        "type": fileinfo.file_type(path),
        "sha256": None,
        "filesystem": dict.fromkeys(fileinfo.FILESYSTEM_FIELDS),
        "metadata": dict.fromkeys(extractors.METADATA_FIELDS),
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

    result["metadata"], result["warnings"] = extractors.extract(path, result["type"])
    return result
