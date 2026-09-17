"""What the filesystem knows about a file.

This is deliberately kept apart from the metadata stored inside the document.
The two can disagree, and that disagreement is often the interesting part: a
file copied between machines gets new filesystem timestamps while the dates
written inside the document stay as they were.
"""

import datetime
import hashlib
from pathlib import Path

SUPPORTED_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".pdf"}

READ_SIZE = 65536

FILESYSTEM_FIELDS = ["name", "extension", "size_bytes", "created", "modified", "accessed"]


def file_type(path):
    """Short name for the file type, or None if it is not one we handle."""
    suffix = Path(path).suffix.lower()
    if suffix in SUPPORTED_EXTENSIONS:
        return suffix.lstrip(".")
    return None


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
