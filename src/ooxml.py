"""Read Office documents, which are ZIP archives full of XML.

Everything comes from the two property files and the relationship files, read
straight out of the archive. Python-docx, openpyxl or python-pptx are not used,
on purpose. Reading the XML reaches fields none of them expose, such as Company, 
Manager and Hyperlink base. It reports values as they are written rather than 
as a library interprets them. And it works on macro-enabled files, which those 
libraries refuse to open.
"""

import zipfile
from xml.etree import ElementTree

CORE_PART = "docProps/core.xml"
APP_PART = "docProps/app.xml"

DATE_FIELDS = {"created", "modified", "last_printed"}

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
        hyperlinks, external = read_external_relationships(package, names, warnings)
        properties = read_properties(package, CORE_PART, CORE_NAMES, warnings)
        properties.update(read_properties(package, APP_PART, APP_NAMES, warnings))
        details = {
            "metadata": properties,
            "hyperlinks": hyperlinks,
            "external_relationships": external,
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
            name = names[tag]
            values[name] = as_value(name, (element.text or "").strip())
    return values


def as_value(name, text):
    """An empty element means nothing was set. Values are otherwise left as written."""
    if not text:
        return None
    if name in DATE_FIELDS and text.endswith("Z"):
        return text[:-1] + "+00:00"
    return text


def read_external_relationships(package, names, warnings):
    """Addresses the document points at, split into hyperlinks and everything else.

    A template, image or embedded object can also come from a remote address,
    fetched when the file is opened rather than when a link is clicked.
    """
    hyperlinks = []
    others = []
    for name in names:
        if not name.endswith(".rels"):
            continue
        root = parse_part(package, name, warnings)
        if root is None:
            continue
        for element in root:
            if element.get("TargetMode") != "External":
                continue
            target = element.get("Target")
            if not target:
                continue
            kind = (element.get("Type") or "").rsplit("/", 1)[-1]
            if kind == "hyperlink":
                if target not in hyperlinks:
                    hyperlinks.append(target)
            elif {"type": kind, "target": target} not in others:
                others.append({"type": kind, "target": target})
    return hyperlinks, others


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


