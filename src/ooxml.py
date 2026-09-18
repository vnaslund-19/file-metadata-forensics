"""Read metadata straight out of the ZIP structure of DOCX, XLSX and PPTX files.

These formats are ZIP archives full of XML. Reading that XML directly reaches
fields the format libraries never expose, such as Company, Manager, Hyperlink
base and external links, and gives a second reading of the core properties to
check the libraries against.
"""

import zipfile
from xml.etree import ElementTree

CORE_PART = "docProps/core.xml"
APP_PART = "docProps/app.xml"

HYPERLINK_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
)

# Property files are small. A very large one is more likely an attempt to
# overload the XML parser than a real document.
MAX_PART_SIZE = 1_000_000

# core.xml tag names, without their namespace, to the names used in results.
CORE_NAMES = {
    "title": "title",
    "subject": "subject",
    "creator": "author",
    "keywords": "keywords",
    "description": "comments",
    "category": "category",
    "lastModifiedBy": "last_modified_by",
    "revision": "revision",
    "created": "created",
    "modified": "modified",
    "lastPrinted": "last_printed",
    "contentStatus": "content_status",
    "identifier": "identifier",
    "language": "language",
    "version": "version",
}

# app.xml tag names to the names used in results. These are the fields the
# format libraries do not read.
APP_NAMES = {
    "Application": "application",
    "AppVersion": "app_version",
    "Company": "company",
    "Manager": "manager",
    "HyperlinkBase": "hyperlink_base",
    "Template": "template",
}


def inspect(path):
    """Read the properties, links and archive entries of one file."""
    warnings = []
    with zipfile.ZipFile(path) as package:
        names = package.namelist()
        if CORE_PART not in names:
            warnings.append(f"no {CORE_PART} in the archive")
        details = {
            "core_properties": read_properties(package, CORE_PART, CORE_NAMES, warnings),
            "app_properties": read_properties(package, APP_PART, APP_NAMES, warnings),
            "hyperlinks": read_hyperlinks(package, names, warnings),
            "embedded_objects": [name for name in names if is_embedded_object(name)],
            "macros": [name for name in names if is_macro_part(name)],
        }
    return details, warnings


def read_properties(package, part, names, warnings):
    """Read a property file, keyed by the field names used in results."""
    root = parse_part(package, part, warnings)
    if root is None:
        return {}
    values = {}
    for element in root:
        tag = element.tag.split("}")[-1]
        if tag in names:
            values[names[tag]] = (element.text or "").strip()
    return values


def read_hyperlinks(package, names, warnings):
    """Collect the addresses the document links to, from its relationship files."""
    links = []
    for name in names:
        if not name.endswith(".rels"):
            continue
        root = parse_part(package, name, warnings)
        if root is None:
            continue
        for element in root:
            if element.get("Type") != HYPERLINK_RELATIONSHIP:
                continue
            if element.get("TargetMode") != "External":
                continue
            target = element.get("Target")
            if target and target not in links:
                links.append(target)
    return links


def is_embedded_object(name):
    return "/embeddings/" in name or "oleObject" in name


def is_macro_part(name):
    return name.endswith(("vbaProject.bin", "vbaData.xml"))


def parse_part(package, name, warnings):
    """Parse one XML entry. Oversized XML, and XML declaring entities, is left alone."""
    try:
        info = package.getinfo(name)
    except KeyError:
        return None

    if info.file_size > MAX_PART_SIZE:
        warnings.append(f"{name} is {info.file_size} bytes, too large to parse")
        return None

    data = package.read(name)
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        warnings.append(f"{name} declares a DOCTYPE or entities and was not parsed")
        return None

    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        warnings.append(f"could not parse {name}: {error}")
        return None


def compare_with_library(raw, metadata):
    """Report fields where core.xml and the format library disagree."""
    warnings = []
    for name, raw_value in raw.items():
        value = metadata.get(name)
        if not same_value(raw_value, value):
            warnings.append(
                f"{name} is {raw_value!r} in core.xml but the library read it as {value!r}"
            )
    return warnings


def same_value(raw, value):
    """Compare a raw XML string with a value the library returned."""
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    if value is None:
        return raw == ""
    return raw == str(value)
