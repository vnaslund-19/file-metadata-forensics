"""Read the metadata of a JPEG or PNG image.

The camera, dates and GPS position come from the EXIF block, which JPEGs and
some PNGs carry. PNGs can also hold text chunks, such as Software or Creation
Time. Only the file's header and metadata are read, never the pixels.

EXIF dates are local time. The timezone offset is a separate tag
(OffsetTimeOriginal), so a date with no offset is given without one rather
than assumed to be UTC.
"""

from PIL import ExifTags, Image

ORIENTATIONS = {
    1: "normal",
    2: "mirrored",
    3: "rotated 180",
    4: "mirrored, rotated 180",
    5: "mirrored, rotated 90 counter-clockwise",
    6: "rotated 90 clockwise",
    7: "mirrored, rotated 90 clockwise",
    8: "rotated 90 counter-clockwise",
}

# PNG text chunk keywords to the names used in results.
PNG_TEXT_NAMES = {
    "Title": "title",
    "Author": "author",
    "Description": "subject",
    "Comment": "comments",
    "Software": "application",
    "Creation Time": "created",
}

TAGS = ExifTags.Base
GPS = ExifTags.GPS


def inspect(path):
    """Read the size, EXIF and text metadata of one image."""
    warnings = []
    with Image.open(path) as image:
        metadata = {"width": image.width, "height": image.height}
        metadata.update(read_exif(image.getexif(), warnings))
        if image.format == "PNG":
            metadata.update(read_png_text(image, metadata))
        metadata["has_xmp_metadata"] = "xmp" in image.info
    return {"metadata": metadata}, warnings


def read_exif(exif, warnings):
    """Camera, software, dates and GPS position from the EXIF block."""
    if not exif:
        return {}
    details = exif.get_ifd(ExifTags.IFD.Exif)
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    orientation = exif.get(TAGS.Orientation)
    return {
        "camera_make": text(exif.get(TAGS.Make)),
        "camera_model": text(exif.get(TAGS.Model)),
        "lens": text(details.get(TAGS.LensModel)),
        "application": text(exif.get(TAGS.Software)),
        "author": text(exif.get(TAGS.Artist)),
        "comments": read_user_comment(details.get(TAGS.UserComment), warnings),
        "created": exif_date(details.get(TAGS.DateTimeOriginal),
                             details.get(TAGS.OffsetTimeOriginal)),
        "modified": exif_date(exif.get(TAGS.DateTime), details.get(TAGS.OffsetTime)),
        "orientation": ORIENTATIONS.get(orientation, orientation),
        "gps_latitude": coordinate(gps.get(GPS.GPSLatitude), gps.get(GPS.GPSLatitudeRef), "S"),
        "gps_longitude": coordinate(gps.get(GPS.GPSLongitude), gps.get(GPS.GPSLongitudeRef), "W"),
        "gps_altitude": altitude(gps.get(GPS.GPSAltitude), gps.get(GPS.GPSAltitudeRef)),
        "gps_time": gps_time(gps.get(GPS.GPSDateStamp), gps.get(GPS.GPSTimeStamp)),
    }


def read_png_text(image, found):
    """Known PNG text chunks, without overwriting what EXIF already gave."""
    values = {}
    for keyword, name in PNG_TEXT_NAMES.items():
        value = text(image.text.get(keyword))
        if value and not found.get(name):
            values[name] = value
    return values


def exif_date(value, offset):
    """'2026:10:13 19:07:46' and '+11:00' as '2026-10-13T19:07:46+11:00'."""
    value = text(value)
    if not value:
        return None
    date, _, time = value.partition(" ")
    result = f"{date.replace(':', '-')}T{time}" if time else value
    return result + (text(offset) or "")


def coordinate(parts, reference, negative):
    """Degrees, minutes and seconds as decimal degrees. South and west are negative."""
    if not parts:
        return None
    degrees, minutes, seconds = (float(part) for part in parts)
    value = degrees + minutes / 60 + seconds / 3600
    return -value if text(reference) == negative else value


def altitude(value, reference):
    """Metres above sea level. A reference of 1 means below."""
    if value is None:
        return None
    below = reference in (1, b"\x01")
    return -float(value) if below else float(value)


def gps_time(date, time):
    """GPS date and time, which are always UTC."""
    if not date or not time:
        return None
    hours, minutes, seconds = (float(part) for part in time)
    stamp = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    if seconds % 1:
        stamp += f"{seconds % 1:.3f}"[1:]
    return f"{text(date).replace(':', '-')}T{stamp}Z"


def read_user_comment(value, warnings):
    """EXIF UserComment starts with 8 bytes naming its character set."""
    if value is None:
        return None
    if isinstance(value, str):
        return text(value)
    charset, body = value[:8].rstrip(b"\x00 "), value[8:]
    encoding = "utf-16" if charset == b"UNICODE" else "latin-1"
    try:
        return text(body.decode(encoding))
    except UnicodeDecodeError:
        warnings.append("could not decode the EXIF UserComment")
        return None


def text(value):
    """A tag value as clean text. Empty and padded values become None."""
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("latin-1")
    value = str(value).strip("\x00 ").strip()
    return value or None
