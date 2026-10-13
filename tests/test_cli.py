"""Tests for the command line. Run with: python -m unittest discover tests"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from metadata_forensics import cli

SAMPLES = Path(__file__).parent.parent / "samples"


def run(*args):
    """Run the CLI and return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main([str(arg) for arg in args] + ["--json"])
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def test_unsupported_file_is_skipped_not_scanned(self):
        path = self.folder / "notes.txt"
        path.write_text("hello")
        code, out, _ = run(path)
        [result] = json.loads(out)
        self.assertEqual(code, 0)
        self.assertIsNone(result["sha256"])
        self.assertEqual(result["warnings"], ["unsupported file type"])

    def test_missing_path_is_an_error(self):
        code, out, err = run(self.folder / "nope.pdf")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("no such file or folder", err)

    def test_missing_path_does_not_stop_the_others(self):
        code, out, _ = run(self.folder / "nope.pdf", SAMPLES / "sample.docx")
        self.assertEqual(code, 1)
        self.assertEqual(len(json.loads(out)), 1)

    def test_output_file(self):
        target = self.folder / "results.json"
        code, out, err = run(SAMPLES / "sample.docx", "-o", target)
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertEqual(json.loads(target.read_text())[0]["metadata"]["title"], "DocuTestTitle")
        self.assertIn("written to", err)

    def test_unwritable_output_fails_before_scanning(self):
        code, _, err = run(SAMPLES / "sample.docx", "-o", self.folder / "missing" / "x.json")
        self.assertEqual(code, 1)
        self.assertIn("cannot write", err)


if __name__ == "__main__":
    unittest.main()
