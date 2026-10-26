"""Stage only the generated website, never the complete checkout."""

import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ("atlas.css", "atlas-data.js", "navigation.js", "benchmark.js", "atlas.js")
PAGES = ("index.html", "funding.html", "methodology.html", "accounting.html")


def package_site(root=ROOT):
    manifest = json.loads((root / "data" / "processed" / "documents.json").read_text(encoding="utf-8"))
    documents = [Path(document["path"]) for document in manifest["documents"]]
    if not set(map(Path, PAGES)).issubset(documents):
        raise ValueError("The document manifest is missing a required website page.")
    for path in documents:
        if path.as_posix() not in PAGES and not (
            len(path.parts) == 2 and path.parts[0] == "services" and path.suffix == ".html"
        ):
            raise ValueError(f"Not a public website document: {path}")
    files = documents + [Path("assets") / name for name in ASSETS]
    for path in files:
        source = root / path
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Website files must stay inside the checkout: {path}")
        if not source.is_file():
            raise FileNotFoundError(f"Missing generated website file: {path}")
    destination = root / "_site"
    if destination.is_symlink():
        raise ValueError("The website output directory must not be a symbolic link.")
    if destination.exists():
        shutil.rmtree(destination)
    for path in files:
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / path, target)
    (destination / ".nojekyll").touch()
    print(f"Packaged {len(documents)} documents and {len(ASSETS)} shared assets in _site.")
    return destination


if __name__ == "__main__":
    package_site()
