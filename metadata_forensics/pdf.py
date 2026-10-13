"""Read everything this tool takes from a PDF, opening the file once.

That is the document information fields, the links, the attached files, any
JavaScript, and the identifiers in the XMP metadata stream.

Only clickable links are found. A web address that is just typed out on the
page is not, because the words on the page are not read. JavaScript is reported
by where it is stored, never read out or run.
"""

import contextlib
import datetime
import logging

import pypdf


def inspect(path):
    """Read the metadata, links, attachments, JavaScript and identifiers of one PDF."""
    warnings = []
    with collect_pypdf_messages() as messages:
        reader = pypdf.PdfReader(path)
        metadata = read_document_information(reader, warnings)
        metadata.update(read_xmp_identifiers(reader, warnings))
        details = {
            "metadata": metadata,
            "hyperlinks": read_hyperlinks(reader, warnings),
            "embedded_objects": read_attachments(reader, warnings),
            "javascript": find_javascript(reader, warnings),
        }
    return details, warnings + messages


def read_document_information(reader, warnings):
    """The title, author and related fields a PDF stores about itself."""
    if reader.is_encrypted:
        warnings.append("PDF is encrypted; metadata may be incomplete")

    info = reader.metadata
    if info is None:
        warnings.append("PDF has no document information dictionary")

    return {
        "title": clean(getattr(info, "title", None)),
        "subject": clean(getattr(info, "subject", None)),
        "author": clean(getattr(info, "author", None)),
        "keywords": clean(getattr(info, "keywords", None)),
        # /Creator is the program the document was written in, /Producer the
        # one that turned it into a PDF. They are often different programs.
        "application": clean(getattr(info, "creator", None)),
        "producer": clean(getattr(info, "producer", None)),
        "created": read_date(info, "creation_date", warnings),
        "modified": read_date(info, "modification_date", warnings),
        "pages": len(reader.pages),
        "pdf_version": reader.pdf_header.replace("%PDF-", ""),
        "has_xmp_metadata": reader.xmp_metadata is not None,
    }


def read_date(info, name, warnings):
    """PDF dates are free-form text, so fall back to the raw string."""
    if info is None:
        return None
    try:
        return clean(getattr(info, name))
    except Exception:
        raw = info.get("/CreationDate" if name.startswith("creation") else "/ModDate")
        warnings.append(f"could not parse {name}: {raw!r}")
        return str(raw)


def read_xmp_identifiers(reader, warnings):
    """Identifiers from the XMP metadata stream, if the file has one."""
    try:
        xmp = reader.xmp_metadata
        if xmp is None:
            return {}
        return {
            "document_id": xmp.xmpmm_document_id,
            "instance_id": xmp.xmpmm_instance_id,
        }
    except Exception as error:
        warnings.append(f"could not read the XMP metadata: {error}")
        return {}


def read_hyperlinks(reader, warnings):
    """Addresses held in the link annotations on each page."""
    links = []
    for number, page in enumerate(reader.pages, 1):
        try:
            annotations = page.get("/Annots") or []
        except Exception as error:
            warnings.append(f"could not read annotations on page {number}: {error}")
            continue
        for annotation in annotations:
            target = read_annotation_target(annotation)
            if target and target not in links:
                links.append(target)
    return links


def read_annotation_target(annotation):
    try:
        action = annotation.get_object().get("/A")
        target = action.get_object().get("/URI") if action else None
    except Exception:
        return None
    return str(target) if target else None


def read_attachments(reader, warnings):
    """Names of the files attached to the document."""
    try:
        return list(reader.attachments)
    except Exception as error:
        warnings.append(f"could not read attachments: {error}")
        return []


def find_javascript(reader, warnings):
    """Where JavaScript is stored in the file, if anywhere."""
    found = []
    try:
        root = reader.trailer["/Root"]
        names = resolve(root.get("/Names")) or {}
        if "/JavaScript" in names:
            found.append("stored in the document (/Names /JavaScript)")

        action = resolve(root.get("/OpenAction"))
        if hasattr(action, "get") and action.get("/S") == "/JavaScript":
            found.append("runs when the file is opened (/OpenAction)")
    except Exception as error:
        warnings.append(f"could not check for JavaScript: {error}")
    return found


def resolve(value):
    """Follow a reference to the object it points at."""
    return value.get_object() if value is not None else None


def clean(value):
    """Normalise a value pypdf returns."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value.isoformat()
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class MessageCollector(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@contextlib.contextmanager
def collect_pypdf_messages():
    """Keep pypdf's complaints instead of letting them print.

    pypdf logs damaged structure rather than raising, and those complaints say
    something about the file, so they belong in the results.
    """
    logger = logging.getLogger("pypdf")
    handler = MessageCollector()
    propagate = logger.propagate
    logger.addHandler(handler)
    logger.propagate = False
    try:
        yield handler.messages
    finally:
        logger.propagate = propagate
        logger.removeHandler(handler)
