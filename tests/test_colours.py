"""Offline integrity checks for the source-led council identity catalogue."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import import_colours as colours


class CouncilColourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "data" / "processed" / "council_colours.json"
        cls.mapping = json.loads(cls.path.read_text(encoding="utf-8"))
        cls.provenance = json.loads(colours.PROVENANCE.read_text(encoding="utf-8"))

    def test_exact_return_authority_roster_and_names(self):
        expected = colours.authority_names()
        self.assertEqual(len(expected), 415)
        self.assertEqual(self.mapping.keys(), expected.keys())
        for code, name in expected.items():
            with self.subTest(code=code):
                self.assertEqual(self.mapping[code]["name"], name)

    def test_schema_and_honest_unknowns(self):
        required = {"name", "colour", "source", "sourcePage", "method", "retrieved", "status", "note"}
        for code, record in self.mapping.items():
            with self.subTest(code=code):
                self.assertTrue(required <= record.keys())
                self.assertEqual(record["retrieved"], "2026-10-21")
                self.assertIn(record["status"], ("verified-logo", "unknown"))
                self.assertTrue(record["note"])
                if record["status"] == "unknown":
                    self.assertIsNone(record["colour"])
                    self.assertIsNone(record["source"])
                    self.assertIsNone(record["method"])
                else:
                    self.assertRegex(record["colour"], r"^#[0-9a-f]{6}$")
                    self.assertTrue(record["source"])
                    self.assertTrue(record["method"])

    def test_coverage_matches_explicit_provenance(self):
        verified = {code for code, record in self.mapping.items() if record["status"] == "verified-logo"}
        self.assertEqual(verified, self.provenance["authorities"].keys())
        self.assertEqual(len(verified), 91)
        self.assertEqual(sum(code.startswith("E090") for code in verified), 33)
        self.assertEqual(self.mapping["E09000003"]["status"], "verified-logo")
        self.assertEqual(self.mapping["E09000003"]["colour"], "#006a6c")
        self.assertIn("publicaccess.barnet.gov.uk/online-applications/", self.mapping["E09000003"]["sourcePage"])
        # Do not silently replace an honestly recorded reversed variant with a
        # guessed corporate hue.
        self.assertEqual(self.mapping["E09000016"]["colour"], "#ffffff")
        self.assertIn("reversed white", self.mapping["E09000016"]["note"])

    def test_official_source_pages_and_https_assets(self):
        for code, record in self.provenance["authorities"].items():
            with self.subTest(code=code):
                self.assertEqual(urlsplit(record["source"]).scheme, "https")
                page = urlsplit(record["sourcePage"])
                self.assertEqual(page.scheme, "https")
                self.assertTrue(page.hostname.endswith(".gov.uk"), record["sourcePage"])
                if not urlsplit(record["source"]).hostname.endswith(".gov.uk"):
                    self.assertIn("pageEvidence", record)

    def test_retained_logo_hashes_and_exact_colours(self):
        for code, record in self.provenance["authorities"].items():
            with self.subTest(code=code):
                evidence = (ROOT / record["evidence"]).resolve()
                self.assertTrue(evidence.is_relative_to(colours.LOGOS.resolve()))
                content = evidence.read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(), record["sha256"])
                if evidence.suffix == ".css":
                    self.assertEqual(
                        colours.css_brand_colour(content, record["cssToken"], record["cssSelector"], record["cssProperty"]),
                        record["colour"],
                    )
                elif evidence.suffix == ".svg":
                    self.assertGreater(record["sampleCount"], 0)
                    self.assertEqual(
                        colours.svg_palette(content)[record["colour"]], record["sampleCount"]
                    )
                else:
                    self.assertGreater(record["sampleCount"], 0)
                    try:
                        palette = colours.palette(content, evidence.suffix)
                    except ModuleNotFoundError:
                        continue  # Raster investigation is optional; hashes still enforce integrity.
                    self.assertEqual(palette[record["colour"]], record["sampleCount"])

    def test_external_cdn_uploads_are_linked_by_retained_official_pages(self):
        for record in self.provenance["authorities"].values():
            if "pageEvidence" not in record:
                continue
            content = (ROOT / record["pageEvidence"]).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), record["pageSha256"])
            reference = record.get("sourceReference", record["source"])
            self.assertIn(reference, content.decode("utf-8"))
            self.assertEqual(colours.urllib.parse.urljoin(record["sourcePage"], reference), record["source"])
            self.assertRegex(record["sourcePageSha256"], r"^[a-f0-9]{64}$")

    def test_directory_snapshot_integrity(self):
        directory = self.provenance["directory"]
        content = (ROOT / directory["evidence"]).read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(), directory["sha256"])
        self.assertIn("/e0044d06811681acc2ed14acbd83cfdaa4177714/", directory["source"])

    def test_redbridge_uses_official_dark_red_not_monochrome_icon(self):
        record = self.mapping["E09000026"]
        self.assertEqual(record["colour"], "#942725")
        self.assertEqual(record["cssToken"], "--chestnut")
        self.assertEqual(record["cssSelector"], ".chestnut")
        self.assertEqual(record["cssProperty"], "background-color")
        self.assertIn("/css/redbridge-overrides.css", record["source"])
        content = (ROOT / record["evidence"]).read_bytes()
        self.assertEqual(
            colours.css_brand_colour(content, "--chestnut", ".chestnut", "background-color"),
            "#942725",
        )
        # The homepage currently uses a different palette token in its header;
        # the dark-red selection must not be misrepresented as that header paint.
        self.assertEqual(
            colours.css_brand_colour(content, "--mulberry", ".header-bg", "background-color"),
            record["homepageHeaderColour"],
        )
        self.assertEqual(record["homepageHeaderColour"], "#bc0067")
        self.assertNotEqual(record["colour"], record["homepageHeaderColour"])
        self.assertIn("dark-red", record["note"])
        with self.assertRaises(ValueError):
            colours.css_brand_colour(content, "--chestnut", ".header-bg", "background-color")

    def test_rebuild_is_idempotent_without_optional_packages(self):
        previous = self.path.read_bytes()
        result = subprocess.run(
            [sys.executable, "-S", str(ROOT / "scripts" / "import_colours.py"), "--build"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertIn("91/415", result.stdout)
        self.assertIn("London 33/33", result.stdout)


class CouncilLogoPermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "data" / "processed" / "council_logos.json"
        cls.ledger = json.loads(cls.path.read_text(encoding="utf-8"))
        cls.colour_sources = json.loads(colours.PROVENANCE.read_text(encoding="utf-8"))
        cls.permissions = json.loads(colours.PERMISSIONS.read_text(encoding="utf-8"))

    def test_every_source_asset_has_an_existing_file_and_matching_hash(self):
        self.assertEqual(self.ledger.keys(), self.colour_sources["authorities"].keys())
        self.assertEqual(len(self.ledger), 91)
        for code, record in self.ledger.items():
            with self.subTest(code=code):
                source = self.colour_sources["authorities"][code]
                self.assertEqual(record["file"], source.get("logoEvidence", source["evidence"]))
                self.assertEqual(record["source"], source.get("logoSource", source["source"]))
                path = (ROOT / record["file"]).resolve()
                self.assertTrue(path.is_relative_to(colours.LOGOS.resolve()))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])

    def test_no_permission_is_inferred_from_a_logo_download(self):
        counts = {"permitted": 0, "restricted": 0, "not-established": 0}
        for code, record in self.ledger.items():
            with self.subTest(code=code):
                self.assertIn(record["permission"], counts)
                counts[record["permission"]] += 1
                if record["permission"] in ("permitted", "restricted"):
                    self.assertTrue(record["permissionSource"])
                if record["permissionSource"]:
                    self.assertEqual(record["permissionSource"], self.permissions["policies"][code]["source"])
                    self.assertTrue(urlsplit(record["permissionSource"]).hostname.endswith(".gov.uk"))
                self.assertIn("swatch", record["note"])
        self.assertEqual(counts, {"permitted": 0, "restricted": 5, "not-established": 86})

    def test_focal_councils_require_fallbacks(self):
        redbridge = self.ledger["E09000026"]
        self.assertEqual(redbridge["permission"], "not-established")
        self.assertEqual(redbridge["permissionSource"], "https://www.redbridge.gov.uk/terms-of-use/")
        forest = self.ledger["E09000031"]
        self.assertEqual(forest["permission"], "restricted")
        self.assertIn("without consent is not permitted", forest["note"])

    def test_data_licences_do_not_override_logo_restrictions(self):
        hackney = self.ledger["E09000012"]
        self.assertEqual(hackney["permission"], "restricted")
        self.assertIn("OGL", hackney["note"])
        self.assertIn("nationalarchives.gov.uk", self.permissions["openGovernmentLicence"]["source"])

    def test_ledger_rebuild_is_offline_idempotent_and_does_not_change_colours(self):
        previous = self.path.read_bytes()
        colour_path = ROOT / "data" / "processed" / "council_colours.json"
        previous_colours = colour_path.read_bytes()
        result = subprocess.run(
            [sys.executable, "-S", str(ROOT / "scripts" / "import_colours.py"), "--build-logos"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(colour_path.read_bytes(), previous_colours)
        self.assertIn("0 permitted", result.stdout)


if __name__ == "__main__":
    unittest.main()
