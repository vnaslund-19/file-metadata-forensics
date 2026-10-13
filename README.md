# file-metadata-forensics

Extract metadata from documents, emails and images: who made a file, when,
with what, and what it links to or hides. Files are only read, never
changed, opened or run.

## Install

Requires Python 3.12 or newer.

```bash
pip install git+https://github.com/vnaslund-19/file-metadata-forensics.git
```

## Usage

```bash
extract-metadata report.docx                  # one file
extract-metadata evidence/                    # every supported file in a folder
extract-metadata evidence/ -r                 # include subfolders
extract-metadata evidence/ -r --json -o results.json
```

| Option | |
| --- | --- |
| `-r`, `--recursive` | also scan subfolders |
| `--json`, `--csv` | output JSON or CSV instead of text |
| `-o FILE` | write to a file instead of the screen |
| `--version`, `-h` | version, help |

Unsupported files are listed as skipped, and problems with a file are shown
as warnings, so one bad file never stops a scan.

## What it finds

| Files | Metadata |
| --- | --- |
| Word, Excel, PowerPoint (`.docx .xlsx .pptx`, and `.docm .xlsm .pptm`) | author, last modified by, dates, revision, application, company, manager, template, hyperlinks, external links, embedded objects, macros |
| PDF | author, title, application, producer, dates, XMP IDs, links, attachments, JavaScript |
| Email (`.eml`) | from, to, cc, bcc, subject, date, message ID, delivery path (`Received`), MIME structure, attachments |
| Images (`.jpg .png`) | camera, lens, software, date taken, GPS position and time, size |

Every file also gets its SHA-256 and filesystem dates.

## Development

```bash
git clone https://github.com/vnaslund-19/file-metadata-forensics.git
cd file-metadata-forensics
pip install -e ".[dev]"
python -m unittest discover tests
```
