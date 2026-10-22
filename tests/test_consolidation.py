import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConsolidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data" / "processed" / "atlas.json").read_text())
        cls.mapping = cls.data["consolidation"]
        cls.fields = {f["id"]: f for f in cls.data["fields"]}

    def test_canonical_codes_are_unique_original_columns_not_name_merges(self):
        canonical = self.mapping["canonical"]
        self.assertEqual(len(canonical), 321)
        self.assertEqual(len({row["canonicalId"] for row in canonical}), 321)
        for row in canonical:
            f = self.fields[row["canonicalId"]]
            self.assertEqual(row["officialCode"], f["asset"])
            self.assertEqual(row["originalLabel"], f["label"])
            self.assertEqual(row["sourceColumn"], f["column"])
            self.assertEqual(row["mapping"], "exact-official-return-code")

    def test_aliases_change_display_only_not_codes_or_amounts(self):
        road = next(row for row in self.mapping["canonical"] if row["canonicalId"] == "ra1_transtot")
        self.assertEqual(road["aliases"], ["Roads & transport"])
        self.assertEqual(road["officialCode"], "transtot")
        a = next(a for a in self.data["authorities"] if a["code"] == "E09000026")
        self.assertEqual(a["values"]["ra1_transrdsmnt"], 1718)
        self.assertNotEqual(a["values"]["ra1_transtot"], 1718)

    def test_unlike_scopes_remain_separate_and_local_headlines_are_unmapped(self):
        for first, second in (("ra1_transtot", "ra1_transrdsmnt"), ("ra1_csctot", "ra1_edutot")):
            self.assertNotEqual(self.fields[first]["canonicalId"], self.fields[second]["canonicalId"])
        hra = [f for f in self.fields.values() if f["asset"].startswith("hra")]
        self.assertTrue(hra)
        self.assertTrue(all(f["id"] != "ra1_housgfcftot" for f in hra))
        self.assertEqual(len(self.mapping["localReportMappings"]), 33)
        self.assertEqual(self.mapping["verifiedLocalEquivalences"], 0)
        for row in self.mapping["localReportMappings"]:
            self.assertIsNone(row["canonicalId"])
            self.assertFalse(row["benchmarkEligible"])
            self.assertIn(row["mapping"], ("unmapped-scope-not-reconciled", "not-transcribed"))
            self.assertEqual(row["year"], "2026-27")
            self.assertTrue(row["source"].startswith("https://"))

    def test_only_nonoverlapping_theme_children_reconcile_never_parent_plus_children(self):
        group = self.mapping["nonAdditiveGroups"][0]
        self.assertEqual(len(group["children"]), len(set(group["children"])))
        self.assertNotIn(group["parent"], group["children"])
        self.assertEqual(len(group["children"]), 13)
        for a in self.data["authorities"]:
            if a["returned"]:
                self.assertEqual(sum(a["values"][key] for key in group["children"]), a["values"][group["parent"]])

    def test_mapping_never_collapses_statuses_or_claims_uk_crosswalk(self):
        missing = next(a for a in self.data["authorities"] if a["code"] == "E09000011")
        self.assertIsNone(missing["values"]["ra1_servicetot"])
        self.assertEqual(missing["statuses"]["ra1_servicetot"], "not-returned")
        self.assertIn("No Scotland/Wales/Northern Ireland", self.mapping["devolved"])
        saved = json.loads((ROOT / "data" / "provenance" / "service_consolidation.json").read_text())
        self.assertEqual(saved, self.mapping)


if __name__ == "__main__":
    unittest.main()
