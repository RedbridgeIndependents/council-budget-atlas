"""Import the pinned official returns. No inference, fuzzy joins or imputation."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import urllib.request

from workbooks import ods, xlsx
from consolidation import catalogue

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOWNLOADS = {
    "RA_2026-27_part1.ods": "https://assets.publishing.service.gov.uk/media/6a2962166d178a6fb7e32089/RA_2026-27_data_Part_1.ods",
    "RA_2026-27_part2.ods": "https://assets.publishing.service.gov.uk/media/6a281185e371d9d2c0052b0a/RA_2026-27_data_Part_2.ods",
    "SG_2026-27.ods": "https://assets.publishing.service.gov.uk/media/6a28119b6d178a6fb7e31f7f/SG_2026-27.ods",
    "rdl0102.ods": "https://assets.publishing.service.gov.uk/media/697b61f5f8f4a746d9572f1c/rdl0102.ods",
    "population_2025.xlsx": "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland/mid2025/mye25tablesuk.xlsx",
    "national_table2.ods": "https://assets.publishing.service.gov.uk/media/6a280e823b15d05a7ce31f6c/RA_2026-27_Table_2.ods",
}


def raw_path(filename):
    category = "denominators" if filename in ("rdl0102.ods", "population_2025.xlsx") else "budgets"
    return DATA / "raw" / category / filename
THEME_TOTALS = [
    "edutot", "transtot", "csctot", "asctot", "phtot", "housgfcftot",
    "cultot", "envtot", "plantot", "poltot", "frstot", "centot", "othtot",
]
THEME_NAMES = [
    "Education", "Roads & transport", "Children & families", "Adult social care",
    "Public health", "Housing (General Fund)", "Culture & leisure", "Environment & waste",
    "Planning & development", "Police", "Fire & rescue", "Central services", "Other services",
]
FUNDING_LINES = [
    ("Own council-tax requirement", "ctrtot", 1),
    ("Specific and special grants inside AEF", "grantinaef", -1),
    ("Revenue Support Grant", "grantrsg", -1),
    ("Police grant", "grantpol", -1),
    ("Retained business rates", "retainnndr", -1),
    ("Council-tax collection-fund adjustment", "colfunct", -1),
    ("Reorganisation transfers", "trnsreorg", -1),
    ("Schools reserves: net use (+) / addition (−)", "appressch", -1),
    ("DSG reserves: net use (+) / addition (−)", "appresdsg", -1),
    ("Public-health reserves: net use (+) / addition (−)", "appresph", -1),
    ("Other earmarked reserves: net use (+) / addition (−)", "appresoth", -1),
    ("Unallocated reserves: net use (+) / addition (−)", "appresunall", -1),
    ("Other financing items", "othinc", -1),
]


def number(value):
    """Keep missing, suppressed, not applicable and zero distinct."""
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return value
    return None


def at(row, column):
    return row[column] if column < len(row) else ""


def state(value):
    if number(value) is not None:
        return "reported"
    return {
        "[x]": "not-returned", "[c]": "suppressed", "[z]": "not-applicable",
        "-": "not-applicable", "": "missing",
    }.get(value, "text")


def denominator(asset, group, kind):
    """Preferred service unit is metadata, not a fabricated measurement."""
    if kind != "service":
        return {
            "preferred": "Not a service-output measure",
            "definition": "Accounting balance, grant, financing flow or memorandum item; no output ratio is calculated.",
            "availability": "not-applicable", "source": 5,
        }
    if asset in ("transrdsmnt", "transrdsenv", "transrdswnt"):
        return {
            "preferred": "Miles of locally managed road",
            "definition": "DfT RDL0102a: major locally managed roads + all minor roads, 2025. Rounded miles as published; matched by exact ONS code. London A roads can include TfL responsibilities, so this is network-scale context, not a matched maintenance unit cost.",
            "availability": "available-where-joined", "source": 7, "key": "roads",
        }
    if "Education" in group:
        unit, definition, source = (
            "Pupils / funded child places for the relevant provision",
            "A matched count of the pupils or places covered by this council-funded provision, excluding centrally funded academies where appropriate.",
            15,
        )
    elif "Children" in group:
        unit, definition, source = (
            "Children receiving this service / placement-days",
            "A financial-year matched service-user count or placement duration. Children looked after, safeguarding and early help have different populations.",
            15,
        )
    elif "Adult" in group:
        unit, definition, source = (
            "Supported adults / care-hours in the relevant client group",
            "A financial-year matched supported-client count or care volume for this specific age and support category; residents are not a substitute.",
            16,
        )
    elif "Health" in group:
        unit, definition, source = (
            "Eligible population / treatment episodes for this intervention",
            "The population eligible for this prescribed function or a deduplicated service-specific treatment count, not all residents.",
            16,
        )
    elif "Housing" in group:
        unit, definition, source = (
            "Households assisted / accommodation household-nights",
            "A matched count of assisted households, benefit cases or temporary-accommodation nights for the line concerned.",
            17,
        )
    elif asset in ("envcll", "envdsp", "envtrd", "envrcy", "envmin"):
        unit, definition, source = (
            "Households served / tonnes handled",
            "Households covered by collection or tonnes handled by the specific collection, disposal or recycling function; do not combine the two tiers.",
            18,
        )
    elif asset.startswith("plan"):
        unit, definition, source = (
            "Applications determined / relevant caseload",
            "Matched planning or building-control applications for casework; policy and economic development require a different output definition.",
            19,
        )
    elif asset == "cullib":
        unit, definition, source = "Library visits / active borrowers", "Visits or active borrowers for council-supported libraries in the budget year.", 5
    elif asset == "culpksopn":
        unit, definition, source = "Hectares of maintained public space", "Area actually maintained under the council's service contracts in the budget year.", 5
    elif asset == "transrdslgh":
        unit, definition, source = "Lighting columns maintained", "Street-lighting assets for which the council, not another highway authority, pays.", 7
    elif asset.startswith("trans"):
        unit, definition, source = "Service-specific journeys / assets / eligible users", "Transport policy, parking, concessionary fares and operator support need different denominators; total road miles would misstate their output.", 7
    else:
        unit, definition, source = "Service-specific assets / cases / users", "A matched count of assets maintained, cases handled or people served by this particular activity. No common verified unit is imported.", 5
    return {
        "preferred": unit, "definition": definition,
        "availability": "not-imported", "source": source,
    }


def import_data():
    authorities, fields, national = {}, [], {}
    originals = {}
    for part, filename, sheet, source in (
        ("ra1", "RA_2026-27_part1.ods", "RA_LA_Data_2026-27", 1),
        ("ra2", "RA_2026-27_part2.ods", "RA_LA_Data_2026-27", 2),
        ("sg", "SG_2026-27.ods", "SG_LA_Data_2026-27", 3),
    ):
        rows = ods(raw_path(filename))[sheet]
        header = next(i for i, row in enumerate(rows) if row and row[0] == "E-code")
        end = next(i for i, row in enumerate(rows) if row and row[0] == "Eng")
        group = ""
        columns = []
        for column in range(6, len(rows[header])):
            asset = at(rows[header - 3], column)
            if not asset:
                raise ValueError(f"Missing asset identifier: {filename} column {column}")
            if asset == "invprp_confirm":
                continue  # Textual ownership declaration is kept on authority, not treated as money.
            group = at(rows[header - 2], column) or group
            label = rows[header][column]
            kind = "service" if part == "ra1" and column < 148 else "accounting"
            subtotal = asset in THEME_TOTALS
            if subtotal:
                kind = "theme"
            field = {
                "id": f"{part}_{asset}", "asset": asset, "label": label,
                "group": group, "line": str(at(rows[header - 1], column)),
                "column": column + 1, "headerRow": header + 1, "sheet": sheet,
                "part": part, "source": source, "kind": kind,
                "unit": "GBP thousands", "denominator": denominator(asset, group, kind),
            }
            fields.append(field)
            columns.append((column, field["id"]))
            national[field["id"]] = number(at(rows[end], column))
        roster = rows[header + 1:end]
        assert len(roster) == 415
        originals[part] = {row[1]: row for row in roster}
        for row_number, row in enumerate(roster, header + 2):
            code = row[1]
            if code not in authorities:
                authorities[code] = {
                    "code": code, "ecode": row[0], "name": row[2],
                    "class": row[3], "subclass": row[4], "notes": row[5],
                    "returned": row[5] != "M", "values": {}, "statuses": {},
                    "rows": {}, "population": None, "roads": None,
                }
            authority = authorities[code]
            assert authority["name"] == row[2]
            authority["rows"][part] = row_number
            for column, identifier in columns:
                value = at(row, column)
                authority["values"][identifier] = number(value)
                if state(value) != "reported":
                    authority["statuses"][identifier] = state(value)
            if part == "ra2":
                authority["investmentDeclaration"] = at(row, len(rows[header]) - 1)

    population = xlsx(raw_path("population_2025.xlsx"))["MYE2 - Persons"]
    for row_number, row in enumerate(population, 1):
        if row and row[0] in authorities:
            assert number(row[3]) is not None and row[3] > 0
            authorities[row[0]]["population"] = {"value": row[3], "row": row_number, "year": 2025}

    road_rows = ods(raw_path("rdl0102.ods"))["RDL0102a"]
    assert road_rows[7][12] == "Major locally managed roads"
    assert road_rows[7][18] == "All minor roads"
    for row_number, row in enumerate(road_rows[8:], 9):
        if row and row[0] in authorities:
            major, minor = number(at(row, 12)), number(at(row, 18))
            if major is not None and minor is not None:
                authorities[row[0]]["roads"] = {
                    "value": major + minor, "major": major, "minor": minor,
                    "all": number(at(row, 19)), "row": row_number, "year": 2025,
                    "notes": at(row, 20),
                }

    # Exact source identities, not assumptions about total names.
    totals = ["ra1_" + asset for asset in THEME_TOTALS]
    residuals = {}
    for authority in authorities.values():
        values = authority["values"]
        if authority["returned"]:
            residual = values["ra1_servicetot"] - sum(values[key] for key in totals)
            residuals[authority["code"]] = residual
    assert max(abs(value) for value in residuals.values()) <= 1, residuals
    funding_residuals = {
        a["code"]: sum(a["values"]["ra1_" + asset] * sign for _, asset, sign in FUNDING_LINES) - a["values"]["ra1_revenuetot"]
        for a in authorities.values() if a["returned"]
    }
    assert all(value == 0 for value in funding_residuals.values()), funding_residuals

    manifest = [
        {"file": str(raw_path(filename).relative_to(ROOT)), "url": url, "sha256": hashlib.sha256(raw_path(filename).read_bytes()).hexdigest()}
        for filename, url in DOWNLOADS.items()
    ]
    for field in fields:
        if field["asset"] in THEME_TOTALS and field["part"] == "ra1":
            field["aliases"] = [THEME_NAMES[THEME_TOTALS.index(field["asset"])]]
        else:
            field["aliases"] = []
        field["canonicalId"] = field["id"]
    reports_file = DATA / "processed" / "london_reports.json"
    consolidation = catalogue(fields, json.loads(reports_file.read_text(encoding="utf-8")) if reports_file.exists() else [])
    result = {
        "meta": {
            "year": "2026-27", "published": "2026-06-11", "retrieved": "2026-10-21",
            "populationYear": 2025, "populationPublished": "2026-10-01",
            "roadYear": 2025, "roadPublished": "2026-02-12",
            "expectedAuthorities": 415, "returnedAuthorities": 406,
            "themeIds": totals, "themeNames": THEME_NAMES,
            "missing": [a["name"] for a in authorities.values() if not a["returned"]],
            "classes": dict(Counter(a["class"] for a in authorities.values())),
            "populationJoins": sum(a["population"] is not None for a in authorities.values()),
            "roadJoins": sum(a["roads"] is not None for a in authorities.values()),
            "maxThemeResidualThousands": max(abs(v) for v in residuals.values()),
            "maxFundingResidualThousands": max(abs(v) for v in funding_residuals.values()),
            "fundingLines": [{"label": label, "id": "ra1_" + asset, "sign": sign} for label, asset, sign in FUNDING_LINES],
        },
        "fields": fields, "authorities": list(authorities.values()), "consolidation": consolidation,
        "national": national, "downloads": manifest,
        "notes": {
            "ra1": {row[0]: row[1] for row in ods(raw_path("RA_2026-27_part1.ods"))["Notes"][3:] if len(row) > 1},
            "ra2": {row[0]: row[1] for row in ods(raw_path("RA_2026-27_part2.ods"))["Notes"][3:] if len(row) > 1},
            "sg": {row[0]: row[1] for row in ods(raw_path("SG_2026-27.ods"))["Notes"][3:] if len(row) > 1},
        },
    }
    (DATA / "processed").mkdir(parents=True, exist_ok=True)
    (DATA / "provenance").mkdir(parents=True, exist_ok=True)
    (DATA / "processed" / "atlas.json").write_text(json.dumps(result, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    (DATA / "provenance" / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (DATA / "provenance" / "service_consolidation.json").write_text(json.dumps(consolidation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["meta"], indent=2))
    print(f"Imported {len(fields)} numeric fields; {len([f for f in fields if f['kind'] == 'service'])} detailed service lines.")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Re-download pinned official files before importing")
    arguments = parser.parse_args()
    if arguments.download:
        DATA.mkdir(exist_ok=True)
        for filename, url in DOWNLOADS.items():
            print("Downloading", filename)
            request = urllib.request.Request(url, headers={"User-Agent": "CouncilBudgetAtlas/1.0"})
            with urllib.request.urlopen(request, timeout=90) as response:
                raw_path(filename).parent.mkdir(parents=True, exist_ok=True)
                raw_path(filename).write_bytes(response.read())
    import_data()
