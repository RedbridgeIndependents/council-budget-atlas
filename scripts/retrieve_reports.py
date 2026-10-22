"""Re-download checked public London budget publications using the local ledger.

Run ``python scripts/retrieve_reports.py`` from the repository root. Only entries
already marked retrieved are downloaded; discovery is deliberately not repeated.
The SHA-256 check protects against a council replacing a document at the same URL.

``--verify-headlines`` checks every reviewed local amount against literal PDF
extracts, units, year columns and reviewed definitions. Add ``--pdf-reader-path``
pointing to an installed pypdf source/package directory to re-extract the original
PDF pages as well. The normal offline gate needs only the standard library.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import importlib
import json
from pathlib import Path
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "processed" / "london_reports.json"
PROVENANCE = ROOT / "data" / "provenance"
HEADERS = {"User-Agent": "CouncilBudgetAtlas/1.0 (public budget research)"}
YEAR = re.compile(r"2026\s*[/–-]\s*(?:20)?27")
ANY_YEAR = re.compile(r"\b(20\d{2})\s*[/–-]\s*(?:20)?(\d{2})\b")
HEADLINE_AUDIT = PROVENANCE / "london_headlines_verification.json"


def normalize_space(text: str) -> str:
    return " ".join(text.split())


def verify_headlines(
    reports: list[dict] | None = None, pdf_reader_path: Path | None = None
) -> tuple[int, int]:
    """Fail closed on changed amounts, definitions, locators, source bytes or evidence."""
    if reports is None:
        reports = json.loads(LEDGER.read_text(encoding="utf-8"))
    audit = json.loads(HEADLINE_AUDIT.read_text(encoding="utf-8"))
    provenance = json.loads(
        (PROVENANCE / "london_reports_verification.json").read_text(encoding="utf-8")
    )["reports"]
    by_ons = {report["ons"]: report for report in reports}
    cases = audit["claims"]
    if len(cases) != 24 or len({case["ons"] for case in cases}) != 24:
        raise ValueError("Expected all 24 originally transcribed headlines in the release gate")
    covered = {case["ons"] for case in cases}
    if any(report["localHeadline"] is not None and report["ons"] not in covered for report in reports):
        raise ValueError("Unreviewed local headline")
    reader_type = None
    if pdf_reader_path is not None:
        sys.path.insert(0, str(pdf_reader_path.resolve()))
        reader_type = importlib.import_module("pypdf").PdfReader
    verified = withheld = 0
    for case in cases:
        label = case["council"]

        def require(condition: bool, detail: str) -> None:
            if not condition:
                raise ValueError(f"{label}: {detail}")

        report = by_ons[case["ons"]]
        require(report["council"] == label, "council changed")
        require(report["year"] == audit["targetYear"] == "2026-27", "budget year changed")
        require(report["file"] == case["file"], "document path changed")
        require(report["sha256"] == case["documentSha256"], "document reference hash changed")
        require(sha256(ROOT / report["file"]) == case["documentSha256"], "PDF bytes changed")
        evidence = provenance[case["ons"]]
        text_path = ROOT / evidence["textFile"]
        require(sha256(text_path) == evidence["textSha256"], "preserved extraction changed")
        text = text_path.read_text(encoding="utf-8")
        pages = dict(re.findall(r"=== PDF PAGE (\d+) ===(.*?)(?==== PDF PAGE |\Z)", text, re.S))
        reader = reader_type(ROOT / report["file"]) if reader_type else None
        direct_pages = {}
        for item in case["evidence"]:
            require(str(item["page"]) in pages, "physical PDF page missing")
            page_text = normalize_space(pages[str(item["page"])])
            require(
                hashlib.sha256(page_text.encode("utf-8")).hexdigest() == item["pageTextSha256"],
                f"page {item['page']} extraction hash changed",
            )
            require(
                normalize_space(item["quote"]) in page_text,
                f"literal extract absent from physical PDF page {item['page']}",
            )
            if reader is not None:
                if item["page"] not in direct_pages:
                    direct_pages[item["page"]] = normalize_space(
                        reader.pages[item["page"] - 1].extract_text()
                    )
                require(
                    direct_pages[item["page"]] == page_text,
                    f"direct PDF extraction differs on page {item['page']}",
                )
        items = {item["role"]: item for item in case["evidence"]}
        require(len(items) == len(case["evidence"]), "duplicate evidence roles")
        require({"amount", "units", "year"} <= items.keys(), "amount/units/year proof missing")
        value = Decimal(case["sourceValue"].replace(",", ""))
        scale = case["sourceScale"]
        require(scale in (1, 1000, 1000000), "unsupported pounds conversion")
        scaled = value * scale
        require(scaled == scaled.to_integral_value(), "non-integer pounds conversion")
        require(int(scaled) == case["checkedHeadlinePounds"], "source-to-pounds conversion differs")
        precision = Decimal(scale).scaleb(value.as_tuple().exponent)
        require(precision == case["sourcePrecisionPounds"], "displayed precision differs")
        amount_quote = normalize_space(items["amount"]["quote"])
        require(case["sourceValue"] in amount_quote, "source numeral absent from amount extract")
        unit_quote = normalize_space(items["units"]["quote"])
        inline = re.escape(case["sourceValue"])
        if case.get("table"):
            unit_pattern = {
                1: r"£",
                1000: r"£\s*['’]?\s*000s?",
                1000000: r"£\s*['’]?\s*m\b",
            }[scale]
            require(bool(re.search(unit_pattern, unit_quote)), "table currency/unit label differs")
            table = case["table"]
            require(
                len(table["columnYears"]) == len(table["sourceValues"]),
                "table column count differs",
            )
            selected = table["selectedIndex"]
            require(table["columnYears"][selected] == case["sourceYear"], "wrong table year column")
            require(table["sourceValues"][selected] == case["sourceValue"], "wrong table value column")
            literal_row = normalize_space(table["rowLabel"] + " " + " ".join(table["sourceValues"]))
            require(literal_row in amount_quote, "labelled table row differs")
            quoted_years = [
                f"{match[0]}-{match[1]}" for match in ANY_YEAR.findall(items["year"]["quote"])
            ]
            require(
                quoted_years == [year for year in table["columnYears"] if year],
                "table header years differ",
            )
        else:
            unit_pattern = rf"£\s*{inline}\s*m(?:illion)?\b" if scale == 1000000 else rf"£\s*{inline}"
            require(bool(re.search(unit_pattern, unit_quote)), "inline currency/unit differs")
        source_years = {
            f"{match[0]}-{match[1]}" for match in ANY_YEAR.findall(items["year"]["quote"])
        }
        require(case["sourceYear"] in source_years, "claimed source year absent from literal proof")
        if case["status"] == "verified":
            require(case["sourceYear"] == report["year"], "headline refers to another financial year")
            require(report["localHeadline"] == int(scaled), "localHeadline differs from reviewed pounds")
            require(report["localMeasure"] == case["localMeasure"], "reviewed accounting definition changed")
            require(report["localLocator"] == case["localLocator"], "reviewed page/locator changed")
            require(report["note"] == case["localNote"], "reviewed accounting caveat changed")
            page = re.search(r"PDF p(\d+)", report["localLocator"])
            require(page is not None and int(page.group(1)) == items["amount"]["page"], "primary locator differs")
            verified += 1
        elif case["status"] == "withheld":
            require(case["sourceYear"] != report["year"], "wrong-year exclusion no longer supported")
            require(
                all(report[key] is None for key in ("localHeadline", "localMeasure", "localLocator")),
                "withheld wrong-year headline restored",
            )
            require(bool(case["reason"]), "withholding explanation missing")
            withheld += 1
        else:
            raise ValueError(f"{label}: unknown review status")
    return verified, withheld


def retrieve(url: str) -> tuple[bytes, str, str]:
    url = urllib.parse.quote(url, safe=":/?&=%+#")
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.read(), response.headers.get_content_type(), response.url
    except urllib.error.URLError as error:
        if not isinstance(error.reason, ssl.SSLCertVerificationError):
            raise
        # Windows curl uses the system trust store, unlike this Python build.
        # Certificate verification remains enabled; never use --insecure.
        result = subprocess.run(
            ["curl", "--fail", "--location", "--silent", "--show-error",
             "--proto", "=https", "--proto-redir", "=https", "--max-time", "90", url],
            capture_output=True, check=True,
        )
        content_type = "application/pdf" if result.stdout.startswith(b"%PDF-") else "text/html"
        return result.stdout, content_type, url


def check_type(data: bytes, format_: str) -> None:
    if format_ == "PDF":
        if not data.startswith(b"%PDF-"):
            raise ValueError("Expected a PDF signature, not an error or challenge page")
    elif format_ == "HTML":
        beginning = data[:4096].lower()
        if b"<html" not in beginning and b"<!doctype html" not in beginning:
            raise ValueError("Expected an HTML document")
        text = data.decode("utf-8", errors="replace").lower()
        if any(term in text for term in ("pardon our interruption", "verify you are human")):
            raise ValueError("Received a bot challenge, not a budget publication")
    else:
        raise ValueError(f"Unsupported format: {format_}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_ledger() -> None:
    checks = json.loads((PROVENANCE / "london_reports_checks.json").read_text(encoding="utf-8"))
    research = json.loads((PROVENANCE / "reports_research.json").read_text(encoding="utf-8"))
    reports, verification = [], {}
    for checked in checks["checks"]:
        source = research[checked["source"]]
        path = ROOT / source["file"].replace("\\", "/")
        data = path.read_bytes()
        format_ = "PDF" if data.startswith(b"%PDF-") else "HTML"
        check_type(data, format_)
        text_path = PROVENANCE / "reports_text" / f"{path.stem}.txt"
        text = text_path.read_text(encoding="utf-8")
        year_match = YEAR.search(text)
        if not year_match:
            raise ValueError(f"Budget-year content not verified: {checked['council']}")
        report = {key: checked[key] for key in
                  ("ons", "council", "title", "date", "localHeadline", "localMeasure",
                   "localLocator", "note")}
        report.update(
            url=source.get("final_url", source["url"]),
            year="2026-27", format=format_, file=path.relative_to(ROOT).as_posix(),
            status="retrieved", sha256=hashlib.sha256(data).hexdigest(),
            retrieved=checks["retrieved"],
        )
        reports.append(report)
        contexts = []
        for key in checked["contexts"]:
            context = research[key]
            context_path = ROOT / context["file"].replace("\\", "/")
            contexts.append({
                "url": context.get("final_url", context["url"]),
                "file": context_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(context_path),
            })
        verification[checked["ons"]] = {
            "documentSha256": report["sha256"],
            "textFile": text_path.relative_to(ROOT).as_posix(),
            "textSha256": sha256(text_path),
            "pdfPages": len(re.findall(r"=== PDF PAGE \d+ ===", text)),
            "yearExcerpt": text[max(0, year_match.start() - 80):year_match.end() + 160],
            "contexts": contexts,
        }
    if sorted(report["ons"] for report in reports) != [f"E090000{i:02d}" for i in range(1, 34)]:
        raise ValueError("Expected precisely the 33 London authorities")
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PROVENANCE / "london_reports_verification.json").write_text(
        json.dumps({"methodology": checks["methodology"], "reports": verification},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(f"Built {len(reports)} checked report records")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--council", help="Retrieve only this council (case-insensitive substring)")
    parser.add_argument("--verify", action="store_true", help="Check local files without network access")
    parser.add_argument("--build-ledger", action="store_true", help="Rebuild the ledger from checked provenance")
    parser.add_argument("--verify-headlines", action="store_true", help="Check all reviewed local headline evidence")
    parser.add_argument("--pdf-reader-path", type=Path, help="Optional pypdf import path for direct PDF re-extraction")
    args = parser.parse_args()
    if args.build_ledger:
        build_ledger()
        return
    if args.verify_headlines:
        verified, withheld = verify_headlines(pdf_reader_path=args.pdf_reader_path)
        print(f"Headline gate: {verified} verified; {withheld} withheld (all 24 checked)")
        return
    reports = json.loads(LEDGER.read_text(encoding="utf-8"))
    failures = []
    for report in reports:
        if args.council and args.council.casefold() not in report["council"].casefold():
            continue
        if report["status"] != "retrieved":
            print(f"SKIP {report['council']}: unavailable in checked retrieval")
            continue
        path = (ROOT / report["file"]).resolve()
        path.relative_to(ROOT / "data" / "raw" / "reports")
        try:
            if args.verify:
                data = path.read_bytes()
            else:
                data, _, final_url = retrieve(report["url"])
                if urllib.parse.urlsplit(final_url).scheme != "https":
                    raise ValueError("Non-HTTPS redirect")
            check_type(data, report["format"])
            digest = hashlib.sha256(data).hexdigest()
            if digest != report["sha256"]:
                raise ValueError("Source changed; review before replacing")
            if not args.verify:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            print(f"OK {report['council']}: {len(data):,} bytes")
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            failures.append(report["council"])
            print(f"FAIL {report['council']}: {error}")
    if failures:
        raise SystemExit(f"{len(failures)} report(s) failed: {', '.join(failures)}")


if __name__ == "__main__":
    main()
