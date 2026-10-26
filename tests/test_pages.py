"""Keep non-website sources out of the GitHub Pages artifact."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import unquote, urljoin, urlsplit

from test_documents import Page

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from package_site import ASSETS, PAGES, package_site


class PagesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.paths = [*PAGES, "services/example.html"]
        for name in self.paths + [f"assets/{name}" for name in ASSETS]:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name, encoding="utf-8")
        self.manifest = self.root / "data" / "processed" / "documents.json"
        self.manifest.parent.mkdir(parents=True)
        self.write_manifest(self.paths)

    def write_manifest(self, paths):
        self.manifest.write_text(json.dumps({"documents": [{"path": path} for path in paths]}), encoding="utf-8")

    def test_only_manifest_documents_and_explicit_assets_are_published(self):
        private_paths = [
            ".git/config", ".github/workflows/pages.yml", "README.md",
            "src/page.html", "data/raw/reports/research.pdf",
            "assets/research.html", "services/unlisted.html",
        ]
        for name in private_paths:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("private", encoding="utf-8")
        destination = package_site(self.root)
        expected = {*self.paths, *(f"assets/{name}" for name in ASSETS), ".nojekyll"}
        actual = {path.relative_to(destination).as_posix() for path in destination.rglob("*") if path.is_file()}
        self.assertEqual(actual, expected)
        for name in expected - {".nojekyll"}:
            self.assertEqual((destination / name).read_bytes(), (self.root / name).read_bytes())

    def test_repackaging_removes_stale_public_files(self):
        destination = package_site(self.root)
        (destination / "stale.html").write_text("stale", encoding="utf-8")
        package_site(self.root)
        self.assertFalse((destination / "stale.html").exists())

    def test_non_document_manifest_paths_are_rejected(self):
        for name in ("../secret.html", "/secret.html", "data/private.html", "README.md", "services/../secret.html"):
            with self.subTest(name=name):
                self.write_manifest([*self.paths, name])
                with self.assertRaisesRegex(ValueError, "Not a public website document"):
                    package_site(self.root)
                self.assertFalse((self.root / "_site").exists())

    def test_missing_pages_or_assets_fail_before_replacing_the_artifact(self):
        destination = package_site(self.root)
        self.write_manifest(self.paths[1:])
        with self.assertRaisesRegex(ValueError, "missing a required website page"):
            package_site(self.root)
        self.write_manifest(self.paths)
        (self.root / "assets" / "atlas.js").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "Missing generated website file"):
            package_site(self.root)
        self.assertTrue((destination / "index.html").is_file())

    def test_real_artifact_links_resolve_under_the_github_pages_project_prefix(self):
        destination = package_site(ROOT)
        base = "https://redbridgeindependents.github.io/council-budget-atlas/"
        manifest = json.loads((ROOT / "data" / "processed" / "documents.json").read_text())
        checked = 0
        for document in manifest["documents"]:
            for _, _, href in Page(destination / document["path"]).links:
                if urlsplit(href).scheme or urlsplit(href).netloc:
                    continue
                target = urlsplit(urljoin(base + document["path"], href))
                self.assertTrue(target.path.startswith("/council-budget-atlas/"), href)
                relative = unquote(target.path.removeprefix("/council-budget-atlas/"))
                self.assertTrue((destination / relative).is_file(), (document["path"], href))
                checked += 1
        self.assertGreater(checked, 8_000)


if __name__ == "__main__":
    unittest.main()
