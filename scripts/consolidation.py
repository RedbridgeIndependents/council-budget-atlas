"""Auditable canonical service definitions; no name-based monetary merging."""

def catalogue(fields, reports):
    canonical = []
    for field in fields:
        canonical.append({
            "canonicalId": field["id"],
            "officialCode": field["asset"],
            "returnPart": field["part"],
            "originalLabel": field["label"],
            "aliases": field.get("aliases", []),
            "sourceSheet": field["sheet"],
            "sourceColumn": field["column"],
            "sourceLine": field["line"],
            "year": "2026-27",
            "unit": field["unit"],
            "mapping": "exact-official-return-code",
            "rationale": "Every authority uses this same published return column and definition; authority-specific source rows remain in atlas.json. Display aliases never change amounts.",
            "aggregation": "published-rollup-not-additive-with-components" if field["kind"] == "theme" else "retain-published-line; no inferred split or allocation",
        })
    local = [{
        "authority": report["ons"],
        "originalLabel": report.get("localMeasure"),
        "amount": report.get("localHeadline"),
        "unit": "GBP",
        "year": report["year"],
        "source": report["url"],
        "sourceLocation": report.get("localLocator"),
        "canonicalId": None,
        "mapping": "unmapped-scope-not-reconciled" if report.get("localHeadline") is not None else "not-transcribed",
        "benchmarkEligible": False,
        "rationale": "Local headline scope is retained verbatim. No verified equivalent RA breakdown is established; no string matching, allocation, aggregation or substitution is performed.",
    } for report in reports]
    return {
        "method": "Official England RA/SG codes, not similarly named council directorates, are canonical.",
        "canonical": canonical,
        "localReportMappings": local,
        "verifiedLocalEquivalences": 0,
        "nonAdditiveGroups": [
            {"parent": "ra1_servicetot", "children": ["ra1_"+asset for asset in ("edutot","transtot","csctot","asctot","phtot","housgfcftot","cultot","envtot","plantot","poltot","frstot","centot","othtot")], "rule": "Use parent OR children, never both. Verified reconciliation for all 406 submitted returns."},
        ],
        "devolved": "No Scotland/Wales/Northern Ireland service mapping or monetary consolidation established.",
    }
