"""Offline checks for the directly retrieved official London budget publications."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch
from datetime import date
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import retrieve_reports  # noqa: E402
from retrieve_reports import YEAR, check_type, verify_headlines  # noqa: E402


class LondonReportsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = json.loads(
            (ROOT / "data" / "processed" / "london_reports.json").read_text(encoding="utf-8")
        )
        cls.provenance = json.loads(
            (ROOT / "data" / "provenance" / "london_reports_verification.json").read_text(
                encoding="utf-8"
            )
        )["reports"]

    def test_exact_roster_and_schema(self):
        self.assertEqual(len(self.reports), 33)
        self.assertEqual(
            [report["ons"] for report in self.reports],
            [f"E090000{i:02d}" for i in range(1, 34)],
        )
        self.assertEqual(len({report["council"] for report in self.reports}), 33)
        fields = {
            "ons", "council", "url", "title", "date", "year", "format", "file",
            "status", "note", "localHeadline", "localMeasure", "localLocator",
            "sha256", "retrieved",
        }
        for report in self.reports:
            with self.subTest(council=report["council"]):
                self.assertEqual(set(report), fields)
                self.assertEqual(report["year"], "2026-27")
                self.assertEqual(report["retrieved"], "2026-10-21")
                self.assertIn(report["format"], ("PDF", "HTML"))
                self.assertIn(report["status"], ("retrieved", "unavailable"))
                self.assertTrue(report["title"])
                self.assertTrue(report["note"])
                if report["date"] is not None:
                    date.fromisoformat(report["date"])
                parsed = urlsplit(report["url"])
                self.assertEqual(parsed.scheme, "https")
                self.assertTrue(
                    parsed.hostname.endswith(".gov.uk")
                    or parsed.hostname.endswith(".moderngov.co.uk")
                )
                if report["localHeadline"] is None:
                    self.assertIsNone(report["localMeasure"])
                    self.assertIsNone(report["localLocator"])
                else:
                    self.assertIs(type(report["localHeadline"]), int)
                    self.assertGreater(report["localHeadline"], 0)
                    self.assertTrue(report["localMeasure"])
                    self.assertTrue(report["localLocator"])

    def test_downloaded_type_and_hash(self):
        for report in self.reports:
            with self.subTest(council=report["council"]):
                if report["status"] == "unavailable":
                    self.assertIsNone(report["file"])
                    self.assertIsNone(report["sha256"])
                    continue
                path = (ROOT / report["file"]).resolve()
                path.relative_to(ROOT / "data" / "raw" / "reports")
                data = path.read_bytes()
                self.assertGreater(len(data), 1000)
                check_type(data, report["format"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), report["sha256"])

    def test_document_content_evidence(self):
        """The preserved extraction is tied to the exact checked source bytes."""
        self.assertEqual(set(self.provenance), {report["ons"] for report in self.reports})
        for report in self.reports:
            with self.subTest(council=report["council"]):
                evidence = self.provenance[report["ons"]]
                self.assertEqual(evidence["documentSha256"], report["sha256"])
                text_bytes = (ROOT / evidence["textFile"]).read_bytes()
                self.assertEqual(hashlib.sha256(text_bytes).hexdigest(), evidence["textSha256"])
                text = text_bytes.decode("utf-8").replace("\r\n", "\n")
                self.assertTrue(YEAR.search(text), "No 2026/27 content in the checked extraction")
                self.assertTrue(evidence["yearExcerpt"] in text, "Year excerpt differs from extraction")
                self.assertRegex(evidence["yearExcerpt"], YEAR)
                self.assertEqual(
                    evidence["pdfPages"], len(re.findall(r"=== PDF PAGE \d+ ===", text))
                )
                self.assertGreater(evidence["pdfPages"], 0)
                if report["localHeadline"] is not None:
                    page = re.search(r"PDF p(\d+)", report["localLocator"]).group(1)
                    page_text = re.search(
                        rf"=== PDF PAGE {page} ===(.*?)(?==== PDF PAGE |\Z)", text, re.S
                    ).group(1)
                    compact = re.sub(r"[,\s]", "", page_text)
                    amount = report["localHeadline"]
                    representations = {
                        str(amount),
                        f"{amount / 1000:.3f}".rstrip("0").rstrip("."),
                        f"{amount / 1000000:.6f}".rstrip("0").rstrip("."),
                    }
                    self.assertTrue(
                        any(value in compact for value in representations),
                        f"Headline not present on stated page: {report['localLocator']}",
                    )
                for context in evidence["contexts"]:
                    data = (ROOT / context["file"]).read_bytes()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), context["sha256"])

    def test_scope_caveats_are_not_hidden(self):
        city = self.reports[0]
        self.assertIn("Police", city["note"])
        self.assertIn("Port Health", city["note"])
        self.assertIn("separate", city["note"])
        bromley = next(report for report in self.reports if report["ons"] == "E09000006")
        self.assertIn("NOT the full", bromley["note"])
        self.assertIsNone(bromley["localHeadline"])
        greenwich = next(report for report in self.reports if report["ons"] == "E09000011")
        self.assertIn("no RA values imputed", greenwich["note"])

    def test_all_original_headlines_pass_literal_evidence_gate(self):
        """All 24 original claims are accounted for, including Harrow's exclusion."""
        self.assertEqual(verify_headlines(self.reports), (23, 1))

    def test_each_supported_headline_rejects_unit_conversion_error(self):
        for report in self.reports:
            if report["localHeadline"] is None:
                continue
            with self.subTest(council=report["council"]):
                changed = deepcopy(self.reports)
                row = next(row for row in changed if row["ons"] == report["ons"])
                row["localHeadline"] *= 1000
                with self.assertRaisesRegex(ValueError, "localHeadline differs"):
                    verify_headlines(changed)

    def test_changed_definition_locator_or_year_fails_gate(self):
        for key, value, message in (
            ("localMeasure", "MHCLG net service expenditure", "accounting definition changed"),
            ("localLocator", "PDF p1, invented total", "page/locator changed"),
            ("year", "2025-26", "budget year changed"),
            ("note", "Directly comparable with all other councils", "accounting caveat changed"),
        ):
            with self.subTest(field=key):
                changed = deepcopy(self.reports)
                changed[0][key] = value
                with self.assertRaisesRegex(ValueError, message):
                    verify_headlines(changed)

    def test_wrong_year_harrow_headline_cannot_be_restored(self):
        changed = deepcopy(self.reports)
        harrow = next(row for row in changed if row["ons"] == "E09000015")
        self.assertIsNone(harrow["localHeadline"])
        self.assertIn("2025/26, NOT 2026/27", harrow["note"])
        harrow["localHeadline"] = 215000000
        with self.assertRaisesRegex(ValueError, "withheld wrong-year headline restored"):
            verify_headlines(changed)

    def test_evidence_mismatches_fail_gate(self):
        audit = json.loads(retrieve_reports.HEADLINE_AUDIT.read_text(encoding="utf-8"))
        mutations = (
            ("unit scale", "City of London", "sourceScale", 1000),
            ("precision", "City of London", "sourcePrecisionPounds", 1),
            ("source year", "City of London", "sourceYear", "2025-26"),
        )
        for label, council, field, value in mutations:
            with self.subTest(mutation=label):
                changed = deepcopy(audit)
                next(row for row in changed["claims"] if row["council"] == council)[field] = value
                with patch.object(retrieve_reports, "HEADLINE_AUDIT") as path:
                    path.read_text.return_value = json.dumps(changed)
                    with self.assertRaises(ValueError):
                        verify_headlines(self.reports)
        for mutation in ("table year column", "literal extract"):
            with self.subTest(mutation=mutation):
                changed = deepcopy(audit)
                barnet = next(row for row in changed["claims"] if row["ons"] == "E09000003")
                if mutation == "table year column":
                    barnet["table"]["selectedIndex"] = 0
                else:
                    barnet["evidence"][0]["quote"] = "Budget Requirement 999,999,999"
                with patch.object(retrieve_reports, "HEADLINE_AUDIT") as path:
                    path.read_text.return_value = json.dumps(changed)
                    with self.assertRaises(ValueError):
                        verify_headlines(self.reports)

    def test_non_pdf_error_page_is_rejected(self):
        with self.assertRaises(ValueError):
            check_type(b"<!DOCTYPE html><html>Access denied</html>", "PDF")
        with self.assertRaises(ValueError):
            check_type(b"<!DOCTYPE html><html>Pardon Our Interruption</html>", "HTML")


if __name__ == "__main__":
    unittest.main()
