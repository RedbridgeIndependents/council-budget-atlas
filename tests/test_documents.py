"""Exhaustive document coverage, offline links and static source-led fallbacks."""

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.ids, self.links, self.scripts, self.services, self.directory = [], [], [], [], []
        self.h1s = 0
        self.source = path.read_text(encoding="utf-8")
        self.feed(self.source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "h1":
            self.h1s += 1
        for key in ("href", "src"):
            if key in attrs:
                self.links.append((tag, key, attrs[key]))
        if tag == "script" and "src" in attrs:
            self.scripts.append(attrs["src"])
        if tag == "section" and "service" in attrs.get("class", "").split():
            self.services.append(attrs["id"].removeprefix("line-"))
        if "directory-entry" in attrs.get("class", "").split():
            self.directory.append(attrs["data-directory-search"])


class DocumentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "data" / "processed" / "documents.json").read_text())
        cls.atlas = json.loads((ROOT / "data" / "processed" / "atlas.json").read_text())
        cls.fields = {f["id"]: f for f in cls.atlas["fields"]}
        cls.pages = {d["path"]: Page(ROOT / d["path"]) for d in cls.manifest["documents"]}

    def test_exact_service_coverage_and_unique_real_paths(self):
        expected = {f["id"] for f in self.fields.values() if f["kind"] == "service"}
        service_docs = [d for d in self.manifest["documents"] if d["kind"] == "service"]
        self.assertEqual(len(expected), 129)
        self.assertEqual({d["field"] for d in service_docs}, expected)
        paths = [d["path"] for d in self.manifest["documents"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(len(paths), 133)
        self.assertEqual({p.relative_to(ROOT).as_posix() for p in (ROOT / "services").glob("*.html")}, {d["path"] for d in service_docs})
        for doc in service_docs:
            self.assertEqual(self.pages[doc["path"]].services, [doc["field"]])
            self.assertEqual(doc["path"], self.manifest["fieldPaths"][doc["field"]])
            self.assertEqual(self.pages[doc["path"]].source.count("data-ledger-chart="), 1)

    def test_all_321_fields_retained_once_without_accounting_as_services(self):
        occurrences = [field for page in self.pages.values() for field in page.services]
        self.assertEqual(len(occurrences), 321)
        self.assertEqual(set(occurrences), self.fields.keys())
        appendix = self.pages["accounting.html"]
        self.assertEqual(len(appendix.services), 192)
        self.assertTrue(all(self.fields[key]["kind"] != "service" for key in appendix.services))
        overview = self.pages["index.html"]
        self.assertFalse(overview.services)
        self.assertEqual(len(overview.directory), 129)
        self.assertIn('id="theme-benchmarks"', overview.source)
        self.assertLess(len(overview.source.encode("utf-8")), 500_000)

    def test_every_relative_link_asset_anchor_and_citation_resolves(self):
        checked = 0
        for name, page in self.pages.items():
            self.assertEqual(len(page.ids), len(set(page.ids)), name)
            self.assertEqual(page.h1s, 1, name)
            for tag, attribute, href in page.links:
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc:
                    self.assertNotIn(tag, ("script", "link", "img"), (name, href))
                    continue
                target = ((ROOT / name).parent / unquote(parsed.path)).resolve() if parsed.path else ROOT / name
                self.assertTrue(target.is_relative_to(ROOT), (name, href))
                self.assertTrue(target.is_file(), (name, href))
                if parsed.fragment:
                    target_name = target.relative_to(ROOT).as_posix()
                    self.assertIn(unquote(parsed.fragment), self.pages[target_name].ids, (name, href))
                checked += 1
            self.assertIn("assets/atlas.css", page.source)
            self.assertEqual(len(page.scripts), 4)
        self.assertGreater(checked, 8_000)

    def test_all_service_fallback_values_definitions_and_provenance_match(self):
        focus = next(a for a in self.atlas["authorities"] if a["code"] == "E09000026")
        peer = next(a for a in self.atlas["authorities"] if a["code"] == "E09000031")
        from html import unescape
        for doc in self.manifest["documents"]:
            if doc["kind"] != "service":
                continue
            field, page = self.fields[doc["field"]], self.pages[doc["path"]]
            source = page.source
            self.assertIn("<details open>", source)
            self.assertIn(unescape(field["label"]), unescape(re.sub("<[^>]+>", "", source)))
            self.assertIn(field["sheet"], source)
            self.assertIn("Preferred service denominator", source)
            self.assertIn("not proof of waste", source)
            self.assertIn("spending-funding-context", page.ids)
            for authority in (focus, peer):
                number = authority["values"][field["id"]]
                expected = "Not available" if number is None else ("−" if number < 0 else "") + f"£{abs(number) / 1000:,.3f}m"
                self.assertIn(expected, source, (doc["path"], authority["name"]))
            citations = re.findall(r'href="\.\./methodology.html#source-(\d+)"', source)
            self.assertIn(str(field["source"]), citations)
            self.assertIn(str(field["denominator"]["source"]), citations)
            self.assertIn('href="../index.html#services"', source)

    def test_shared_assets_use_the_canonical_data_and_calculation_source(self):
        published = (ROOT / "assets" / "atlas-data.js").read_text(encoding="utf-8")
        loaded = json.loads(published.removeprefix("window.atlasData=").strip().removesuffix(";"))
        self.assertEqual(loaded["fields"], self.atlas["fields"])
        self.assertEqual(loaded["authorities"], self.atlas["authorities"])
        self.assertEqual(loaded["documents"]["fields"], self.manifest["fieldPaths"])
        for filename in ("benchmark.js", "navigation.js", "atlas.js"):
            self.assertEqual((ROOT / "src" / filename).read_text(encoding="utf-8"), (ROOT / "assets" / filename).read_text(encoding="utf-8"))
        self.assertNotIn("fetch(", (ROOT / "assets" / "atlas.js").read_text())
        self.assertNotIn("localStorage", (ROOT / "assets" / "atlas.js").read_text())
        for page in self.pages.values():
            self.assertIn("URL-selected councils and metrics require JavaScript", page.source)

    def test_all_133_documents_share_one_accessible_icon_only_theme_button(self):
        expected = None
        for name, page in self.pages.items():
            buttons = re.findall(r'<button\b[^>]*id="theme-toggle"[^>]*>.*?</button>', page.source, re.S)
            self.assertEqual(len(buttons), 1, name)
            button = buttons[0]
            expected = button if expected is None else expected
            self.assertEqual(button, expected, name)
            self.assertIn('type="button"', button)
            self.assertIn('aria-label="Use dark theme"', button)
            self.assertIn('title="Use dark theme"', button)
            self.assertEqual(button.count('data-theme-icon="moon"'), 1)
            self.assertEqual(button.count('data-theme-icon="sun"'), 1)
            self.assertEqual(button.count('aria-hidden="true"'), 2)
            self.assertEqual(button.count('focusable="false"'), 2)
            self.assertEqual(re.sub(r"<[^>]+>", "", button).strip(), "")

    def test_every_document_has_visible_native_comparison_controls_and_one_shared_measure(self):
        expected = {a["code"] for a in self.atlas["authorities"]} - {"E09000026"}
        for name, page in self.pages.items():
            source = page.source
            for identifier in ("comparison-controls", "comparison-search", "comparison-options",
                               "comparison-no-results", "comparison-result-count", "selected-count",
                               "selected-comparisons", "shared-metric", "london-preset-status"):
                self.assertEqual(page.ids.count(identifier), 1, (name, identifier))
            self.assertIn('<label for="comparison-search">Compare with</label>', source)
            self.assertIn('name="comparison-search" autocomplete="off"', source)
            self.assertNotIn('<details id="comparison-picker"', source)
            self.assertNotIn('id="focus-council"', source)
            self.assertNotIn('id="benchmark-metric"', source)
            self.assertNotIn('id="display-metric"', source)
            choices = re.findall(r'<input type="checkbox" name="comparison" value="([^"]+)"([^>]*)>', source)
            self.assertEqual(len(choices), len(expected), name)
            self.assertEqual({code for code, _ in choices}, expected, name)
            self.assertEqual([code for code, attrs in choices if "checked" in attrs], ["E09000031"], name)
            self.assertEqual(page.ids.count("peer-group"), 1 if name == "index.html" else 0, name)
        self.assertIn('aria-describedby="peer-group-help"', self.pages["index.html"].source)
        self.assertIn("not your selected comparison councils or their benchmark", self.pages["index.html"].source)

    def test_regeneration_is_offline_and_byte_identical(self):
        files = [ROOT / name for name in self.pages] + list((ROOT / "assets").iterdir()) + [ROOT / "data" / "processed" / "documents.json"]
        before = {path: path.read_bytes() for path in files}
        result = subprocess.run([sys.executable, "-S", str(ROOT / "scripts" / "build.py")], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("133 offline documents", result.stdout)
        self.assertTrue(all(path.read_bytes() == content for path, content in before.items()))


if __name__ == "__main__":
    unittest.main()
