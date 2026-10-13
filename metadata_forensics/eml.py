"""Read an email saved as an .eml file.

Everything comes from the headers and the MIME structure. Attachments are
listed by name and content type, never decoded, saved or opened.

Dates keep the offset they were written with. In an email the offset in the
Date header is usually the sender's own timezone, which is worth keeping.
"""

import email
from email import policy

# Header names to the names used in results.
ADDRESS_HEADERS = {
    "From": "from",
    "To": "to",
    "Cc": "cc",
    "Bcc": "bcc",
}


def inspect(path):
    """Read the headers, delivery path and MIME structure of one email."""
    warnings = []
    with open(path, "rb") as handle:
        message = email.message_from_binary_file(handle, policy=policy.default)

    metadata = {
        "subject": read_header(message, "Subject", warnings),
        "sent": read_date(message, warnings),
        "message_id": read_header(message, "Message-ID", warnings),
    }
    for header, name in ADDRESS_HEADERS.items():
        metadata[name] = read_header(message, header, warnings)

    parts, attachments = read_structure(message, warnings)
    details = {
        "metadata": metadata,
        "received": [unfold(value) for value in message.get_all("Received", [])],
        "mime_parts": parts,
        "embedded_objects": attachments,
    }
    return details, warnings


def read_header(message, name, warnings):
    """One header as text, decoded. A header that won't parse is kept as written."""
    try:
        value = message[name]
    except Exception as error:
        warnings.append(f"could not parse the {name} header: {error}")
        value = message.get_all(name, failobj=[None])[0]
    if value is None:
        return None
    return unfold(str(value)) or None


def read_date(message, warnings):
    """The Date header in ISO format, or as written if it won't parse."""
    try:
        header = message["Date"]
    except Exception as error:
        warnings.append(f"could not parse the Date header: {error}")
        return None
    if header is None:
        return None
    moment = getattr(header, "datetime", None)
    if moment is None:
        warnings.append(f"could not parse the Date header: {str(header)!r}")
        return str(header)
    return moment.isoformat()


def read_structure(message, warnings):
    """Each MIME part as a line indented by depth, and the attachments by name."""
    parts = []
    attachments = []

    def walk(part, depth):
        for defect in part.defects:
            warnings.append(f"MIME defect: {type(defect).__name__}")
        line = "  " * depth + part.get_content_type()
        filename = part.get_filename()
        if filename:
            line += f"  {part.get_content_disposition() or 'inline'}: {filename}"
            attachments.append(f"{filename} ({part.get_content_type()})")
        parts.append(line)
        if part.is_multipart():
            for child in part.iter_parts():
                walk(child, depth + 1)

    walk(message, 0)
    return parts, attachments


def unfold(text):
    """Join a header that was wrapped over several lines."""
    return " ".join(text.split())
