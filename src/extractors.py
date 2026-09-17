"""Metadata stored inside the documents themselves.

Everything here goes through the format libraries (python-docx, openpyxl,
python-pptx, pypdf). Reading the OOXML parts by hand is deliberately left to
the container analysis later on, so that the two approaches can be compared
against each other rather than sharing code.

Note that the libraries only expose the core properties of an Office file.
'Company', 'Manager' and 'Hyperlink base' live in docProps/app.xml, which none of
them read, so those values do not appear here.
"""

import contextlib
import datetime
import logging

import docx
import openpyxl
import pptx
import pypdf

# Every result has all of these. Fields a format doesn't have are None.
METADATA_FIELDS = [
    "title",
    "subject",
    "author",
    "keywords",
    "comments",
    "category",
    "last_modified_by",
    "revision",
    "created",
    "modified",
    "last_printed",
    "application",
    "producer",
    "pages",
    "pdf_version",
    "has_xmp_metadata",
    "content_status",
    "identifier",
    "language",
    "version",
]

# Core property names shared by DOCX and PPTX, as python-docx and python-pptx
# spell them.
OOXML_CORE_PROPERTIES = [
    "title",
    "subject",
    "author",
    "keywords",
    "comments",
    "category",
    "content_status",
    "identifier",
    "language",
    "version",
    "last_modified_by",
    "revision",
    "created",
    "modified",
    "last_printed",
]

# openpyxl spells several of the same properties differently.
XLSX_CORE_PROPERTIES = {
    "title": "title",
    "subject": "subject",
    "author": "creator",
    "keywords": "keywords",
    "comments": "description",
    "category": "category",
    "content_status": "contentStatus",
    "identifier": "identifier",
    "language": "language",
    "version": "version",
    "last_modified_by": "lastModifiedBy",
    "revision": "revision",
    "created": "created",
    "modified": "modified",
    "last_printed": "lastPrinted",
}


def extract(path, file_type):
    """Return (metadata, warnings). A file that can't be read gives a warning, not a crash."""
    extractors = {
        "docx": extract_docx,
        "xlsx": extract_xlsx,
        "pptx": extract_pptx,
        "pdf": extract_pdf,
    }
    metadata = dict.fromkeys(METADATA_FIELDS)
    try:
        found, warnings = extractors[file_type](path)
    except Exception as error:
        return metadata, [f"could not read {file_type} metadata: {error}"]
    metadata.update(found)
    return metadata, warnings


def extract_docx(path):
    return read_ooxml_core(docx.Document(path).core_properties)


def extract_pptx(path):
    return read_ooxml_core(pptx.Presentation(path).core_properties)


def read_ooxml_core(props):
    metadata = {}
    for name in OOXML_CORE_PROPERTIES:
        metadata[name] = clean(getattr(props, name, None))
    return metadata, []


def extract_xlsx(path):
    workbook = openpyxl.load_workbook(path, read_only=True)
    try:
        props = workbook.properties
        metadata = {}
        for name, source_name in XLSX_CORE_PROPERTIES.items():
            metadata[name] = clean(getattr(props, source_name, None))
        # openpyxl gives the revision as text, python-docx and python-pptx as a number.
        if metadata["revision"] and metadata["revision"].isdigit():
            metadata["revision"] = int(metadata["revision"])
        return metadata, []
    finally:
        workbook.close()


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


def extract_pdf(path):
    warnings = []
    with collect_pypdf_messages() as messages:
        metadata = read_pdf(path, warnings)
    warnings.extend(messages)
    return metadata, warnings


def read_pdf(path, warnings):
    reader = pypdf.PdfReader(path)

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
        "created": read_pdf_date(info, "creation_date", warnings),
        "modified": read_pdf_date(info, "modification_date", warnings),
        "pages": len(reader.pages),
        "pdf_version": reader.pdf_header.replace("%PDF-", ""),
        "has_xmp_metadata": reader.xmp_metadata is not None,
    }


def read_pdf_date(info, name, warnings):
    """PDF dates are free-form text, so fall back to the raw string."""
    if info is None:
        return None
    try:
        return clean(getattr(info, name))
    except Exception:
        raw = info.get("/CreationDate" if name.startswith("creation") else "/ModDate")
        warnings.append(f"could not parse {name}: {raw!r}")
        return str(raw)


def clean(value):
    """Normalise a property value for output."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        # Office core properties are stored as UTC, but openpyxl hands back a
        # datetime with no timezone on it. Say so rather than leaving dates
        # from different formats looking inconsistent.
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value.isoformat()
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value
