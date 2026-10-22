"""Check the real imported cells, units, totals, joins and generated fallback."""

from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from import_data import number, state
from workbooks import ods, xlsx


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data" / "processed" / "atlas.json").read_text())
        cls.by_code = {a["code"]: a for a in cls.data["authorities"]}
        cls.fields = {f["id"]: f for f in cls.data["fields"]}
        cls.books = {
            "ra1": ods(ROOT / "data" / "raw" / "budgets" / "RA_2026-27_part1.ods"),
            "ra2": ods(ROOT / "data" / "raw" / "budgets" / "RA_2026-27_part2.ods"),
            "sg": ods(ROOT / "data" / "raw" / "budgets" / "SG_2026-27.ods"),
        }

    def test_roster_and_complete_field_catalogue(self):
        self.assertEqual(len(self.by_code), 415)
        self.assertEqual(len(self.fields), 321)
        self.assertEqual(Counter(f["kind"] for f in self.fields.values()), {"service": 129, "theme": 13, "accounting": 179})
        self.assertEqual(sum(a["class"] == "LB" for a in self.by_code.values()), 33)
        self.assertEqual(sum(a["class"] != "O" for a in self.by_code.values()), 317)
        self.assertEqual(sum(a["returned"] for a in self.by_code.values()), 406)
        self.assertEqual(set(self.data["meta"]["missing"]), {"Castle Point", "Coventry", "Cumberland", "Dudley", "Epping Forest", "Greenwich", "Guildford", "South Gloucestershire", "Warwick"})

    def test_every_imported_cell_against_original(self):
        for a in self.by_code.values():
            for f in self.fields.values():
                row = self.books[f["part"]][f["sheet"]][a["rows"][f["part"]] - 1]
                cell = row[f["column"] - 1] if len(row) >= f["column"] else ""
                self.assertEqual(a["values"][f["id"]], number(cell), (a["code"], f["id"]))
                self.assertEqual(a["statuses"].get(f["id"], "reported"), state(cell), (a["code"], f["id"]))

    def test_theme_reconciliation_every_return(self):
        for a in self.by_code.values():
            if a["returned"]:
                self.assertEqual(sum(a["values"][i] for i in self.data["meta"]["themeIds"]), a["values"]["ra1_servicetot"], a["name"])

    def test_sg_transfer_signs_every_return(self):
        for a in self.by_code.values():
            if a["returned"]:
                self.assertEqual(a["values"]["ra1_grantinaef"], -a["values"]["sg_grantintot"], a["name"])
                self.assertEqual(a["values"]["ra1_grantoutaef"], -a["values"]["sg_grantouttot"], a["name"])

    def test_funding_reconciliation_and_signs_every_return(self):
        for a in self.by_code.values():
            if a["returned"]:
                total = sum(a["values"][item["id"]] * item["sign"] for item in self.data["meta"]["fundingLines"])
                self.assertEqual(total, a["values"]["ra1_revenuetot"], a["name"])
        a = self.by_code["E09000026"]
        government = -sum(a["values"][key] for key in ("ra1_grantinaef", "ra1_grantrsg", "ra1_grantpol"))
        self.assertEqual(government, 477529)
        self.assertEqual(a["values"]["ra1_ctrtot"], 167968)
        self.assertAlmostEqual(167968 / 731321 * 100, 22.96775420915, places=5)
        self.assertEqual(a["values"]["sg_grantindsg"], 349074)
        self.assertEqual(a["values"]["ra1_appresunall"], 20000)
        self.assertEqual(a["values"]["ra1_netoffexpcap"], -70001)

    def test_design_fonts_licences_and_source_provenance(self):
        design = json.loads((ROOT / "data" / "provenance" / "design.json").read_text())
        self.assertEqual(design["palette"]["navy"], "#06296d")
        self.assertEqual(design["palette"]["gold"], "#fdd200")
        self.assertEqual(len(design["fonts"]), 7)
        for font in design["fonts"]:
            path = ROOT / font["file"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), font["sha256"])
            self.assertEqual(font["licence"], "SIL Open Font License 1.1")
        for name in ("BarlowCondensed-OFL.txt", "Barlow-OFL.txt"):
            self.assertIn("SIL OPEN FONT LICENSE Version 1.1", (ROOT / "data" / "raw" / "design" / name).read_text())

    def test_national_crosscheck_against_separate_table(self):
        table = ods(ROOT / "data" / "raw" / "budgets" / "national_table2.ods")["Table_2a"]
        mapping = {
            "Education services": "edutot", "Highways and transport services": "transtot",
            "Children's Social Care services": "csctot", "Adult Social Care services": "asctot",
            "Public Health services": "phtot", "Housing services (excluding Housing Revenue Account)": "housgfcftot",
            "of which: Cultural services": "cultot", "Environmental services": "envtot",
            "Planning and development services": "plantot", "Police services": "poltot",
            "Fire and rescue services": "frstot", "Central services": "centot",
            "Other Services": "othtot", "Total Service Expenditure": "servicetot",
        }
        for name, asset in mapping.items():
            row = next(r for r in table if r and r[0] == name)
            self.assertAlmostEqual(self.data["national"]["ra1_" + asset] / 1000, row[2], delta=.001, msg=asset)

    def test_redbridge_original_figures_and_roads_formula(self):
        a = self.by_code["E09000026"]
        self.assertEqual(a["values"]["ra1_servicetot"], 787766)
        self.assertEqual(a["values"]["ra1_revenuetot"], 731321)
        self.assertEqual(a["values"]["ra1_transrdsmnt"], 1718)
        self.assertEqual(a["population"]["value"], 321829)
        self.assertEqual((a["roads"]["major"], a["roads"]["minor"], a["roads"]["value"]), (36, 295, 331))
        self.assertAlmostEqual(1718 * 1000 / 331, 5190.332326283988)
        self.assertAlmostEqual(787766 * 1000 / 321829, 2447.778167909045, places=5)
        self.assertIsNone(self.by_code["E09000011"]["values"]["ra1_servicetot"])

    def test_all_denominator_joins_exact_source_cells(self):
        populations = xlsx(ROOT / "data" / "raw" / "denominators" / "population_2025.xlsx")["MYE2 - Persons"]
        roads = ods(ROOT / "data" / "raw" / "denominators" / "rdl0102.ods")["RDL0102a"]
        for a in self.by_code.values():
            if a["population"]:
                row = populations[a["population"]["row"] - 1]
                self.assertEqual(row[0], a["code"])
                self.assertEqual(row[3], a["population"]["value"])
            if a["roads"]:
                row = roads[a["roads"]["row"] - 1]
                self.assertEqual(row[0], a["code"])
                self.assertEqual(row[12] + row[18], a["roads"]["value"])
        self.assertEqual([a["name"] for a in self.by_code.values() if a["class"] != "O" and not a["population"]], ["Barnsley", "Sheffield"])
        self.assertEqual({f["asset"] for f in self.fields.values() if f["denominator"].get("key") == "roads"}, {"transrdsmnt", "transrdsenv", "transrdswnt"})

    def test_missing_zero_suppression_and_nonapplicable_distinct(self):
        self.assertEqual(number(0), 0)
        self.assertIsNone(number("[x]"))
        self.assertIsNone(number("[c]"))
        self.assertIsNone(number("-"))
        self.assertEqual([state(x) for x in [0, "[x]", "[c]", "-", ""]], ["reported", "not-returned", "suppressed", "not-applicable", "missing"])

    def test_source_hashes_and_categorised_paths(self):
        for item in self.data["downloads"]:
            path = ROOT / item["file"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
            self.assertGreater(len(path.relative_to(ROOT / "data").parts), 1)
        self.assertFalse([p for p in (ROOT / "data").iterdir() if p.is_file()])

    def test_generated_offline_fallback(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(page.count('data-ledger-chart="'), 0)
        self.assertEqual(page.count('class="directory-entry"'), 129)
        self.assertIn("£787.766m", page)
        self.assertIn('href="#content"', page)
        self.assertIn('href="methodology.html#source-1"', page)
        self.assertIn("prefers-reduced-motion", (ROOT / "assets" / "atlas.css").read_text(encoding="utf-8"))
        self.assertFalse(re.search(r'<(?:script|link|img)[^>]+(?:src|href)="https?://', page))
        markup = re.sub(r"<script\b[^>]*>.*?</script>", "", page, flags=re.S)
        ids = re.findall(r'\bid="([^"]+)"', markup)
        self.assertEqual(len(ids), len(set(ids)))
        targets = re.findall(r'href="#([^"]+)"', markup)
        self.assertTrue(set(targets).issubset(set(ids)), set(targets) - set(ids))


if __name__ == "__main__":
    unittest.main()
