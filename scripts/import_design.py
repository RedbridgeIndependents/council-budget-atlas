"""Fetch and pin the source site's openly licensed Barlow font families."""

import hashlib
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "data" / "raw" / "design"
PROVENANCE = ROOT / "data" / "provenance" / "design.json"
SOURCES = {
    "redbridgeindys-home.html": "https://redbridgeindys.org/",
    "edublink-main.css": "https://redbridgeindys.org/wp-content/themes/edublink/assets/css/main.css?ver=1.0.5",
    "edublink-style.css": "https://redbridgeindys.org/wp-content/themes/edublink/style.css?ver=6.8.11",
    "elementor-global.css": "https://redbridgeindys.org/wp-content/uploads/elementor/css/post-7.css?ver=1791233516",
    "elementor-home.css": "https://redbridgeindys.org/wp-content/uploads/elementor/css/post-21162.css?ver=1791596251",
    "barlow-fonts.css": "https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&display=swap",
    "barlow-body-fonts.css": "https://fonts.googleapis.com/css2?family=Barlow:wght@400;600;700&display=swap",
    "BarlowCondensed-OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed/OFL.txt",
    "Barlow-OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/barlow/OFL.txt",
}


def fetch(url, path):
    print("Downloading", path.name)
    request = urllib.request.Request(url, headers={"User-Agent": "CouncilBudgetAtlas/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        path.write_bytes(response.read())


def import_design(download=False):
    DESIGN.mkdir(parents=True, exist_ok=True)
    records, fonts = [], []
    for filename, url in SOURCES.items():
        path = DESIGN / filename
        if download or not path.exists():
            fetch(url, path)
        retained = filename.startswith("barlow") or filename.endswith("-OFL.txt")
        records.append({"file": str(path.relative_to(ROOT)) if retained else None, "url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "retained": retained})
    for family, filename in (("Barlow Condensed", "barlow-fonts.css"), ("Barlow", "barlow-body-fonts.css")):
        text = (DESIGN / filename).read_text()
        for block in re.findall(r"@font-face\s*\{([^}]+)\}", text):
            weight = int(re.search(r"font-weight:\s*(\d+)", block).group(1))
            url = re.search(r"src:\s*url\(([^)]+)\)", block).group(1)
            suffix = ".woff2" if ".woff2" in url else ".ttf"
            path = DESIGN / f'{family.replace(" ", "")}-{weight}{suffix}'
            if download or not path.exists():
                fetch(url, path)
            font = {"family": family, "weight": weight, "file": str(path.relative_to(ROOT)), "url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "licence": "SIL Open Font License 1.1"}
            fonts.append(font)
    result = {
        "retrieved": "2026-10-21", "site": "https://redbridgeindys.org/",
        "palette": {"navy": "#06296d", "gold": "#fdd200", "alternateGold": "#fdd300", "heading": "#181818", "white": "#ffffff", "shade": "#f5f5f5", "border": "#e5e5e5", "mutedAccessible": "#54595f"},
        "evidence": "Homepage inline edublink primary #06296D / primary-alt #FDD300; Elementor homepage headings #FDD200, Barlow Condensed weight 800. Live computed homepage heading families include Barlow 700 and Barlow Condensed 700/800; body declares century-gothic. Elementor global secondary #54595F supplies higher-contrast muted text rather than the site's low-contrast #808080 body colour.",
        "typography": {
            "headings": "Barlow Condensed 700/800, bundled under OFL 1.1.",
            "body": "Century Gothic if installed locally; Barlow 400/600/700 is the bundled, openly licensed offline fallback, also used in the source site's main heading.",
            "restriction": "No Century Gothic asset is bundled: redistribution permission for the proprietary font has not been established.",
        },
        "adaptations": "Editorial layout is original. Light mode uses navy text/accent on white with gold rules. Dark mode uses the site's #181818 and white, with gold accents; translucent tints are derived adaptations, not claimed as a source-site dark mode.",
        "sources": records, "fonts": fonts,
    }
    PROVENANCE.parent.mkdir(exist_ok=True)
    PROVENANCE.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for filename in SOURCES:
        if not (filename.startswith("barlow") or filename.endswith("-OFL.txt")):
            (DESIGN / filename).unlink()
    print(f'Pinned {len(fonts)} licensed font faces and source design evidence.')


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    import_design(parser.parse_args().download)
