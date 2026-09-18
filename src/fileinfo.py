"""What the filesystem knows about a file.

This is deliberately kept apart from the metadata stored inside the document.
The two can disagree, and that disagreement is often the interesting part: a
file copied between machines gets new filesystem timestamps while the dates
written inside the document stay as they were.
"""

import datetime
import hashlib
from pathlib import Path

# The macro-enabled extensions hold the same format as their plain counterparts,
# so they are read the same way.
SUPPORTED_EXTENSIONS = {
    ".docx": "docx",
    ".docm": "docx",
    ".xlsx": "xlsx",
    ".xlsm": "xlsx",
    ".pptx": "pptx",
    ".pptm": "pptx",
    ".pdf": "pdf",
}

READ_SIZE = 65536

FILESYSTEM_FIELDS = ["name", "extension", "size_bytes", "created", "modified", "accessed"]


def file_type(path):
    """Short name for the file type, or None if it is not one we handle."""
    return SUPPORTED_EXTENSIONS.get(Path(path).suffix.lower())


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(READ_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def describe(path):
    """Filesystem facts about the file. Timestamps are UTC."""
    path = Path(path)
    stat = path.stat()
    return {
        "name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "created": _as_utc(getattr(stat, "st_birthtime", None)),
        "modified": _as_utc(stat.st_mtime),
        "accessed": _as_utc(stat.st_atime),
    }


def _as_utc(timestamp):
    if timestamp is None:
        return None
    moment = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
    return moment.isoformat()
