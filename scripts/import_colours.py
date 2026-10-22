"""Reproduce council identity swatches from retained, official identity evidence.

The catalogue deliberately leaves unresearched authorities unknown. Colours are
normally selected from logos. Redbridge uses its official primary brand-palette
dark-red token rather than the monochrome icon, following a user correction.
Neither council names nor unrelated UI accents generate identity colours.
Run --discover to inspect official home-page logo candidates; --build verifies
the retained evidence before writing the complete return-authority catalogue.
Pillow is required for raster investigation (--collect/--icons), but not for
offline rebuilding: hashes and the retained exact-pixel counts are checked.
"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from workbooks import ods

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LOGOS = DATA / "raw" / "logos"
PROVENANCE = DATA / "provenance" / "council_colour_sources.json"
PERMISSIONS = DATA / "provenance" / "council_logo_permissions.json"
RETRIEVED = "2026-10-21"
DIRECTORY_URL = (
    "https://raw.githubusercontent.com/alphagov/local-links-manager/"
    "e0044d06811681acc2ed14acbd83cfdaa4177714/data/local-authorities.csv"
)
HOME_PAGES = {
    "E09000001": "https://www.cityoflondon.gov.uk/",
    "E09000002": "https://www.lbbd.gov.uk/",
    "E09000003": "https://www.barnet.gov.uk/",
    "E09000004": "https://www.bexley.gov.uk/",
    "E09000005": "https://www.brent.gov.uk/",
    "E09000006": "https://www.bromley.gov.uk/",
    "E09000007": "https://www.camden.gov.uk/",
    "E09000008": "https://www.croydon.gov.uk/",
    "E09000009": "https://www.ealing.gov.uk/",
    "E09000010": "https://www.enfield.gov.uk/",
    "E09000011": "https://www.royalgreenwich.gov.uk/",
    "E09000012": "https://hackney.gov.uk/",
    "E09000013": "https://www.lbhf.gov.uk/",
    "E09000014": "https://www.haringey.gov.uk/",
    "E09000015": "https://www.harrow.gov.uk/",
    "E09000016": "https://www.havering.gov.uk/",
    "E09000017": "https://www.hillingdon.gov.uk/",
    "E09000018": "https://www.hounslow.gov.uk/",
    "E09000019": "https://www.islington.gov.uk/",
    "E09000020": "https://www.rbkc.gov.uk/",
    "E09000021": "https://www.kingston.gov.uk/",
    "E09000022": "https://www.lambeth.gov.uk/",
    "E09000023": "https://www.lewisham.gov.uk/",
    "E09000024": "https://www.merton.gov.uk/",
    "E09000025": "https://www.newham.gov.uk/",
    "E09000026": "https://www.redbridge.gov.uk/",
    "E09000027": "https://www.richmond.gov.uk/",
    "E09000028": "https://www.southwark.gov.uk/",
    "E09000029": "https://www.sutton.gov.uk/",
    "E09000030": "https://www.towerhamlets.gov.uk/",
    "E09000031": "https://www.walthamforest.gov.uk/",
    "E09000032": "https://www.wandsworth.gov.uk/",
    "E09000033": "https://www.westminster.gov.uk/",
}
LOGO_OVERRIDES = {
    "E09000003": "https://publicaccess.barnet.gov.uk/online-applications-skin/images/barnet/favicon.ico",
    "E09000007": "https://www.camden.gov.uk/documents/20142/608164825/Camden+logo+favicon/2d1708ea-873a-ccd0-f823-8670707d595b",
    "E09000008": "https://www.croydon.gov.uk/themes/contrib/localgov_base_croydon/assets/images/favicons/apple-touch-icon.png",
    "E09000010": "https://s3-eu-west-1.amazonaws.com/ehq-production-europe/76469c72e67246d56100d5a4e79d063bf42d89ee/original/1667802879/35caa90eaf2a0fa876edd53eec97d25d_footer-logo.png?1667802879",
    "E09000011": "https://www.royalgreenwich.gov.uk/themes/contrib/greenwich/assets/images/favicons/favicon.svg",
    "E09000014": "https://haringey.gov.uk/themes/custom/lgd/assets/images/favicons/apple-touch-icon.png",
    "E09000015": "https://www.harrow.gov.uk/site/dist/icons/png/logo.png",
    "E09000013": "https://s3-eu-west-1.amazonaws.com/ehq-production-europe/5a5820d5fb4cad9d5701c86add2ef8d54a53aa31/original/1642611092/04231c39c0cdaf9fce0a928de383b430_hf_logo_2016_rgb_hires.jpg?1642611092",
    "E09000016": "https://consultation.havering.gov.uk/os-custom-logos/havering-logo-white-rgb.png",
    "E09000017": "https://www.hillingdon.gov.uk/image/83/Hillingdon-favicon/appletouchiconlarge.png?m=1550742133147",
    "E09000018": "https://s3-eu-west-1.amazonaws.com/ehq-production-europe/7e6eba8bd19783762e7782a31ed66aac20c910f0/original/1687876558/a30e707714bdd02180eb311f44f4f57a_LBH.jpg?1687876558",
    "E09000021": "https://www.kingston.gov.uk/themes/custom/bbd_localgov/images/logo-kingston-dark.png",
    "E09000022": "https://www.lambeth.gov.uk/apple-touch-icon.png?v=XBy3YnR4m4",
    "E09000023": "https://councilmeetings.lewisham.gov.uk/sitespecific/assets/static/img/logo.png",
    "E09000024": "https://democracy.merton.gov.uk/SiteSpecific/mertonlogotagline-blue.gif",
    "E09000025": "https://www.newham.gov.uk/logo.gif",
    "E09000026": "https://www.redbridge.gov.uk/assets/images/lbr-apple-touch-icon-180x180.png",
    "E09000027": "https://www.richmond.gov.uk/lbr180x180.png",
    "E09000031": "https://democracy.walthamforest.gov.uk/SiteSpecific/backup_site/index_files/Logo.png",
    "E09000032": "https://www.wandsworth.gov.uk/Assets/Wandsworth-Council-logo-400x400.png",
}
SOURCE_PAGES = {
    "E09000003": "https://publicaccess.barnet.gov.uk/online-applications/",
    "E09000010": "https://letstalk.enfield.gov.uk/",
    "E09000013": "https://haveyoursay.lbhf.gov.uk/",
    "E09000016": "https://consultation.havering.gov.uk/",
    "E09000018": "https://talk.hounslow.gov.uk/",
    "E09000023": "https://councilmeetings.lewisham.gov.uk/uuCoverPage.aspx",
    "E09000024": "https://democracy.merton.gov.uk/uuCoverPage.aspx",
    "E09000031": "https://democracy.walthamforest.gov.uk/uuCoverPage.aspx",
}
INLINE_LOGOS = {"E09000001": 0, "E09000012": 0}


def fetch(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "CouncilBudgetAtlas/1.0 (official logo research)"}
    )
    with urllib.request.urlopen(request, timeout=35) as response:
        content = response.read()
        if content.startswith(b"\x1f\x8b"):
            content = gzip.decompress(content)
        return content, response.url, response.headers.get_content_type()


class LogoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.styles = []
        self.icons = []
        self.inline = []
        self.svg = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img":
            text = " ".join(str(value) for value in attrs.values())
            if "logo" in text.lower():
                self.images.append(attrs)
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.styles.append(attrs.get("href"))
        if tag == "link" and "icon" in attrs.get("rel", ""):
            self.icons.append(attrs)
        if tag == "svg":
            self.svg = self.get_starttag_text()
        elif self.svg is not None:
            self.svg += self.get_starttag_text()

    def handle_endtag(self, tag):
        if self.svg is not None:
            self.svg += f"</{tag}>"
            if tag == "svg":
                self.inline.append(self.svg)
                self.svg = None

    def handle_startendtag(self, tag, attrs):
        if self.svg is not None:
            self.svg += self.get_starttag_text()
        else:
            self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        if self.svg is not None:
            self.svg += data


def discover_one(item):
    code, url = item
    try:
        content, page, _ = fetch(url)
        parser = LogoParser()
        parser.feed(content.decode("utf-8", "replace"))
        return code, {
            "page": page,
            "images": parser.images,
            "styles": parser.styles,
            "inline": parser.inline,
        }
    except Exception as error:
        return code, {"page": url, "error": str(error)}


def discover():
    LOGOS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        result = dict(pool.map(discover_one, HOME_PAGES.items()))
    (LOGOS / "discovery.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    for code, item in sorted(result.items()):
        print(code, item["page"], item.get("error", ""))
        for image in item.get("images", []):
            print(" ", json.dumps(image)[:900])
        for index, svg in enumerate(item.get("inline", [])):
            print(" inline", index, svg[:120], Counter(re.findall(r"#[0-9a-fA-F]{3,8}\b", svg)))


def discover_nation():
    """Use a pinned GOV.UK team's directory, joined by exact ONS identifiers."""
    content, _, _ = fetch(DIRECTORY_URL)
    (LOGOS / "local-authorities.csv").write_bytes(content)
    directory = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    names = authority_names()
    sites = {}
    historical_codes = {
        "E08000016": "E08000038",  # Barnsley boundary identifier changed.
        "E08000019": "E08000039",  # Sheffield boundary identifier changed.
        "E08000020": "E08000037",  # Gateshead boundary identifier changed.
    }
    for row in directory:
        code = historical_codes.get(row["gss"], row["gss"])
        if code in names and not code.startswith("E090"):
            url = row["homepage_url"].replace("http://", "https://", 1)
            sites[code] = url
    # Bound this research batch to counties, metropolitan and unitary councils.
    sites = {code: url for code, url in sites.items() if code.startswith(("E080", "E060", "E100"))}
    existing = json.loads((LOGOS / "discovery.json").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=10) as pool:
        existing.update(pool.map(discover_one, sites.items()))
    (LOGOS / "discovery.json").write_text(json.dumps(existing, indent=2), encoding="utf-8")
    for code in sites:
        item = existing[code]
        print(code, names[code], item.get("error", ""), [
            image.get("src", "")[:150] for image in item.get("images", [])[:2]
        ])


def palette(content, suffix):
    if suffix == ".svg":
        return svg_palette(content)
    # Pillow is only needed when investigating raster evidence, not to rebuild
    # the catalogue or verify its hashes.
    from PIL import Image

    image = Image.open(io.BytesIO(content)).convert("RGBA")
    return Counter(
        "#{:02x}{:02x}{:02x}".format(*pixel[:3])
        for pixel in (image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata())
        if pixel[3] == 255
    )


def normalise_hex(value):
    value = value.lower()
    return "#" + "".join(char * 2 for char in value[1:]) if len(value) == 4 else value


def svg_palette(content):
    root = ET.fromstring(content)
    values = []
    for element in root.iter():
        values.extend(element.get(key, "") for key in ("fill", "stroke", "stop-color"))
        css = element.get("style", "")
        if element.tag.rsplit("}", 1)[-1] == "style":
            css += element.text or ""
        values.extend(re.findall(r"(?:fill|stroke|stop-color)\s*:\s*([^;}]+)", css))
    result = Counter()
    for value in values:
        value = value.strip().lower()
        if re.fullmatch(r"#[0-9a-f]{3}(?:[0-9a-f]{3})?", value):
            result[normalise_hex(value)] += 1
        elif value in ("white", "black"):
            result["#ffffff" if value == "white" else "#000000"] += 1
        elif re.fullmatch(r"rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)", value):
            result["#{:02x}{:02x}{:02x}".format(*map(int, re.findall(r"\d+", value)))] += 1
    return result


def css_brand_colour(content, token, selector, property_name):
    """Resolve a retained official palette token only when a paint rule uses it."""
    text = re.sub(r"/\*.*?\*/", "", content.decode("utf-8"), flags=re.S)
    rules = [(match[0].strip(), match[1]) for match in re.findall(r"([^{}]+)\{([^{}]*)\}", text)]
    roots = [declarations for rule, declarations in rules if rule == ":root"]
    values = [
        value
        for declarations in roots
        for value in re.findall(
            r"(?:^|;)\s*" + re.escape(token) + r"\s*:\s*(#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?)\s*(?=;|$)",
            declarations,
        )
    ]
    paint = r"(?:^|;)\s*" + re.escape(property_name) + r"\s*:\s*var\(\s*" + re.escape(token) + r"\s*\)\s*(?=;|$)"
    if len(values) != 1 or not any(
        rule == selector and re.search(paint, declarations) for rule, declarations in rules
    ):
        raise ValueError("Official CSS palette token or its paint selector is missing/ambiguous")
    return normalise_hex(values[0])


def authority_names():
    rows = ods(DATA / "raw" / "budgets" / "RA_2026-27_part1.ods")["RA_LA_Data_2026-27"]
    header = next(index for index, row in enumerate(rows) if row and row[0] == "E-code")
    end = next(index for index, row in enumerate(rows) if row and row[0] == "Eng")
    return {row[1]: row[2] for row in rows[header + 1:end]}


def collect(codes=None):
    """Retain official images for manual colour selection; never auto-verify."""
    discovery = json.loads((LOGOS / "discovery.json").read_text(encoding="utf-8"))

    def download(item):
        code, info = item
        if code in INLINE_LOGOS:
            url = info["page"]
            content = info["inline"][INLINE_LOGOS[code]].encode("utf-8")
            suffix = ".svg"
            method = "Inline SVG fill"
        else:
            candidates = info.get("images", [])
            url = LOGO_OVERRIDES.get(code)
            if url is None and candidates:
                url = urllib.parse.urljoin(info["page"], candidates[0]["src"])
            if url is None:
                return code, {"error": info.get("error", "Logo asset requires further research")}
            try:
                url = urllib.parse.quote(url, safe=":/?=&%#@+;,")
                content, url, content_type = fetch(url)
                suffix = {
                    "image/svg+xml": ".svg", "image/png": ".png",
                    "image/jpeg": ".jpg", "image/webp": ".webp",
                    "image/gif": ".gif", "image/x-icon": ".ico",
                    "image/vnd.microsoft.icon": ".ico",
                }.get(content_type, Path(urllib.parse.urlsplit(url).path).suffix)
                if suffix not in (".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"):
                    return code, {"error": f"Unexpected logo type {content_type}: {url}"}
                method = "SVG fill" if suffix == ".svg" else "Exact opaque logo pixel"
            except Exception as error:
                return code, {"error": str(error), "source": url}
        target = LOGOS / (code + suffix)
        try:
            colours = palette(content, suffix)
        except Exception as error:
            return code, {"error": str(error), "source": url}
        target.write_bytes(content)
        return code, {
            "source": url, "sourcePage": SOURCE_PAGES.get(code, info["page"]), "method": method,
            "evidence": str(target.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(content).hexdigest(),
            "palette": colours.most_common(15),
        }

    items = [(code, item) for code, item in discovery.items() if not codes or code in codes]
    with ThreadPoolExecutor(max_workers=8) as pool:
        additions = dict(pool.map(download, items))
    previous = LOGOS / "review.json"
    result = json.loads(previous.read_text(encoding="utf-8")) if codes and previous.exists() else {}
    result.update(additions)
    (LOGOS / "review.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for code, item in sorted(additions.items()):
        print(code, item.get("error", item.get("palette", [])[:5]))


def collect_icons():
    """Investigate coloured council emblems where the header is reversed white."""
    review = json.loads((LOGOS / "review.json").read_text(encoding="utf-8"))
    discovery = json.loads((LOGOS / "discovery.json").read_text(encoding="utf-8"))
    candidates = {}
    for code, entry in review.items():
        if code.startswith("E090") or "error" in entry:
            continue
        path = ROOT / entry["evidence"]
        colours = palette(path.read_bytes(), path.suffix)
        if any(colour not in ("#ffffff", "#fefefe", "#000000") for colour in colours):
            continue
        candidates[code] = discovery[code]["page"]

    def download(item):
        code, page = item
        try:
            content, page, _ = fetch(page)
            parser = LogoParser()
            parser.feed(content.decode("utf-8", "replace"))
            icons = [icon for icon in parser.icons if not any(
                marker in icon.get("href", "") for marker in ("/core/misc/", "mask-icon", "pinned-tab")
            )]
            icons.sort(key=lambda icon: (
                "apple-touch" not in icon.get("rel", ""),
                not icon.get("href", "").split("?")[0].endswith(".png"),
            ))
            if not icons:
                return code, {"error": "No council-specific icon linked"}
            url = urllib.parse.urljoin(page, icons[0]["href"])
            content, url, content_type = fetch(url)
            suffix = ".svg" if "svg" in content_type else ".png" if "png" in content_type else ".ico"
            colours = palette(content, suffix)
            path = LOGOS / (code + "-icon" + suffix)
            path.write_bytes(content)
            return code, {
                "source": url, "sourcePage": page, "method": "Exact opaque logo-icon pixel" if suffix != ".svg" else "SVG logo-icon fill",
                "evidence": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": hashlib.sha256(content).hexdigest(),
                "palette": colours.most_common(15),
            }
        except Exception as error:
            return code, {"error": str(error)}

    with ThreadPoolExecutor(max_workers=8) as pool:
        result = dict(pool.map(download, candidates.items()))
    (LOGOS / "icons.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for code, item in result.items():
        print(code, item.get("source", ""), item.get("error", item.get("palette", [])[:4]))


def build():
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    directory = provenance["directory"]
    if hashlib.sha256((ROOT / directory["evidence"]).read_bytes()).hexdigest() != directory["sha256"]:
        raise ValueError("Council website directory evidence hash mismatch")
    selections = provenance["authorities"]
    research = provenance.get("research", {})
    result = {}
    for code, name in authority_names().items():
        record = {
            "name": name,
            "colour": None,
            "source": None,
            "sourcePage": research.get(code, {}).get("sourcePage", HOME_PAGES.get(code)),
            "method": None,
            "retrieved": RETRIEVED,
            "status": "unknown",
            "note": research.get(code, {}).get("note", "Official logo colour not yet verified; no identity colour is assigned."),
        }
        if code in selections:
            chosen = selections[code]
            evidence = ROOT / chosen["evidence"]
            content = evidence.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if digest != chosen["sha256"]:
                raise ValueError(f"{code}: evidence hash mismatch")
            colour = chosen["colour"]
            if not re.fullmatch(r"#[0-9a-f]{6}", colour):
                raise ValueError(f"{code}: invalid identity colour")
            if evidence.suffix == ".css":
                actual = css_brand_colour(
                    content, chosen["cssToken"], chosen["cssSelector"], chosen["cssProperty"]
                )
                if actual != colour:
                    raise ValueError(f"{code}: colour differs from official CSS brand token")
            elif evidence.suffix == ".svg":
                # XML well-formedness and an exact literal are both required.
                if svg_palette(content)[colour] < 1:
                    raise ValueError(f"{code}: colour absent from SVG evidence")
            else:
                if chosen.get("sampleCount", 0) < 1:
                    raise ValueError(f"{code}: no retained exact-pixel count")
                try:
                    count = palette(content, evidence.suffix)[colour]
                except ModuleNotFoundError:
                    count = chosen["sampleCount"]  # The immutable file hash was checked above.
                if count != chosen["sampleCount"]:
                    raise ValueError(f"{code}: selected raster pixel count mismatch")
            if chosen.get("pageEvidence"):
                page = ROOT / chosen["pageEvidence"]
                page_content = page.read_bytes()
                if hashlib.sha256(page_content).hexdigest() != chosen["pageSha256"]:
                    raise ValueError(f"{code}: source-page evidence hash mismatch")
                reference = chosen.get("sourceReference", chosen["source"])
                if reference not in page_content.decode("utf-8", "replace") or urllib.parse.urljoin(
                    chosen["sourcePage"], reference
                ) != chosen["source"]:
                    raise ValueError(f"{code}: identity asset absent from official source-page evidence")
            record.update(chosen)
            record.update(status="verified-logo", retrieved=RETRIEVED)
        result[code] = record
    extra = selections.keys() - result.keys()
    if extra:
        raise ValueError(f"Unrecognised codes: {extra}")
    (DATA / "processed").mkdir(parents=True, exist_ok=True)
    target = DATA / "processed" / "council_colours.json"
    pending = target.with_suffix(".json.new")
    pending.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pending.replace(target)
    verified = sum(record["status"] == "verified-logo" for record in result.values())
    london = sum(record["status"] == "verified-logo" for code, record in result.items() if code.startswith("E090"))
    print(f"Verified {verified}/{len(result)} return authorities; London {london}/33.")


def build_logos():
    """Publish a rights ledger, not an assertion that downloaded logos are licensed."""
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    permissions = json.loads(PERMISSIONS.read_text(encoding="utf-8"))
    decisions = permissions["decisions"]
    names = authority_names()
    result = {}
    for code, asset in provenance["authorities"].items():
        decision = decisions.get(code, {
            "permission": "not-established",
            "permissionSource": None,
            "note": "No applicable logo-specific editorial permission established. Retained for research provenance only; do not embed or bundle as approved branding. Use the readable council name and verified colour swatch instead.",
        })
        status = decision["permission"]
        if status not in ("permitted", "restricted", "not-established"):
            raise ValueError(f"{code}: unrecognised logo permission state")
        if status == "permitted" and not decision.get("permissionSource"):
            raise ValueError(f"{code}: explicit official permission evidence required")
        if decision.get("permissionSource"):
            policy = permissions["policies"].get(code, {})
            if policy.get("source") != decision["permissionSource"]:
                raise ValueError(f"{code}: permission decision has no matching policy evidence")
        logo_file = asset.get("logoEvidence", asset["evidence"])
        logo_hash = asset.get("logoSha256", asset["sha256"])
        path = ROOT / logo_file
        if hashlib.sha256(path.read_bytes()).hexdigest() != logo_hash:
            raise ValueError(f"{code}: logo evidence hash mismatch")
        result[code] = {
            "name": names[code],
            "file": logo_file,
            "source": asset.get("logoSource", asset["source"]),
            "permission": status,
            "permissionSource": decision["permissionSource"],
            "note": decision["note"],
            "retrieved": permissions["retrieved"],
            "sha256": logo_hash,
        }
    target = DATA / "processed" / "council_logos.json"
    pending = target.with_suffix(".json.new")
    pending.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pending.replace(target)
    counts = Counter(item["permission"] for item in result.values())
    print(f"Logo ledger {len(result)} assets: {counts['permitted']} permitted, "
          f"{counts['restricted']} restricted, {counts['not-established']} not-established.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--discover-nation", action="store_true")
    parser.add_argument("--icons", action="store_true")
    parser.add_argument("--codes", nargs="*", help="Restrict --collect to these ONS codes")
    parser.add_argument("--build-logos", action="store_true", help="Build the permission/provenance ledger without changing council colours")
    args = parser.parse_args()
    if args.discover:
        discover()
    if args.discover_nation:
        discover_nation()
    if args.collect:
        collect(args.codes)
    if args.icons:
        collect_icons()
    if args.build:
        build()
    if args.build_logos:
        build_logos()
