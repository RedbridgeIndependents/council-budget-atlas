"""Assemble the offline page, including a useful server-rendered/no-JS edition."""

import html
import base64
import json
from pathlib import Path
import re
from documents import write_documents

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
esc = html.escape
SOURCES = [
    ("MHCLG: RA 2026–27, part 1", "https://assets.publishing.service.gov.uk/media/6a2962166d178a6fb7e32089/RA_2026-27_data_Part_1.ods", "11 June 2026. RA_LA_Data_2026-27. £ thousands; asset IDs row 7, lines row 9, labels row 10. Authority source row shown beside data."),
    ("MHCLG: RA 2026–27, part 2", "https://assets.publishing.service.gov.uk/media/6a281185e371d9d2c0052b0a/RA_2026-27_data_Part_2.ods", "11 June 2026. RA_LA_Data_2026-27. £ thousands; asset IDs row 8, lines row 10, labels row 11. Reserves, HRA and memorandum items."),
    ("MHCLG: specific and special grants 2026–27", "https://assets.publishing.service.gov.uk/media/6a28119b6d178a6fb7e31f7f/SG_2026-27.ods", "11 June 2026. SG_LA_Data_2026-27. £ thousands; identifiers row 7, lines row 9, labels row 10. Grants are not additional service expenditure."),
    ("MHCLG: budget release and response rate", "https://www.gov.uk/government/statistics/local-authority-revenue-expenditure-and-financing-england-2026-to-2027-budget/local-authority-revenue-expenditure-and-financing-2026-27-budget-england", "11 June 2026. Introduction lists 406/415 returns and all nine non-returners. National estimates include grossing."),
    ("MHCLG: technical notes and accounting definitions", "https://www.gov.uk/government/statistics/local-authority-revenue-expenditure-and-financing-england-2026-to-2027-budget/local-authority-revenue-expenditure-and-financing-2026-27-budget-england-technical-notes", "11 June 2026. Responsibilities, snapshot basis, imputation, education/academy boundary, NHS transfers, revenue expenditure and HRA."),
    ("MHCLG: RA forms and guidance", "https://www.gov.uk/government/publications/general-fund-revenue-account-budget", "2026–27 form/guidance updated 13 February 2026. Consult for the full accounting inclusions of each line."),
    ("DfT: RDL0102 road length, 2025", "https://assets.publishing.service.gov.uk/media/697b61f5f8f4a746d9572f1c/rdl0102.ods", "Updated 12 February 2026. RDL0102a, ONS code column A; locally managed major roads column M + minor roads column S. Miles, rounded. Not all transport or a matched treated-road denominator. Official portal: https://www.gov.uk/government/statistical-data-sets/road-length-statistics-rdl"),
    ("ONS: mid-2025 population estimates workbook", "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland/mid2025/mye25tablesuk.xlsx", "Published 1 October 2026. MYE2 - Persons, ONS code column A, all-ages persons column D. Exact-code joins only. Source row shown in denominator audit."),
    ("ONS: mid-2025 population methods and uncertainty", "https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/bulletins/annualmidyearpopulationestimates/mid2025", "1 October 2026. Estimates are subject to uncertainty and revision; residents do not measure service use."),
    ("Scottish Government: local-government finance statistics", "https://www.gov.scot/collections/local-government-finance-statistics/", "Separate national collection. Linked for coverage; no Scottish amounts imported."),
    ("Welsh Government: 2026–27 revenue budget and capital forecast", "https://www.gov.wales/local-authority-revenue-budget-and-capital-forecast-april-2026-march-2027", "18 June 2026. Separate national budget publication. Not mapped to English RA service lines in this edition."),
    ("nidirect: local-council responsibilities", "https://www.nidirect.gov.uk/articles/local-councils", "Official description of Northern Ireland council functions, including services councils do not deliver. No Northern Ireland amounts imported."),
    ("Edward Tufte: books and visual evidence", "https://www.edwardtufte.com/books/", "Bibliographic attribution and visualisation principles only; no book text reproduced."),
    ("Stephen Few: Information Dashboard Design", "https://www.perceptualedge.com/library.php", "Bibliographic attribution. Information Dashboard Design is by Stephen Few."),
    ("DfE: explore education statistics", "https://explore-education-statistics.service.gov.uk/", "Prospective source for matched pupil/children’s-service denominators. NOT imported or used to calculate a ratio."),
    ("NHS England: adult social care data", "https://digital.nhs.uk/data-and-information/areas-of-interest/social-care", "Prospective source for matched adult-care users. NOT imported. Intervention-specific public-health units also require separate definitions."),
    ("MHCLG: statutory homelessness collection", "https://www.gov.uk/government/collections/homelessness-statistics", "Prospective household/caseload denominator source. NOT imported."),
    ("Defra: local-authority collected waste", "https://www.gov.uk/government/collections/waste-and-recycling-statistics", "Prospective tonnes/households denominator source. NOT imported."),
    ("MHCLG: planning applications statistics", "https://www.gov.uk/government/collections/planning-applications-statistics", "Prospective planning caseload denominator source. NOT imported."),
    ("City of London: City Fund budget 2026–27", "https://democracy.cityoflondon.gov.uk/documents/s230239/City%20Fund%20Budget%202026-27%20and%20MTFP%20-%20COCO%20FINAL%20v3.pdf", "5 March 2026, Court of Common Council report. City Fund includes local government, police and port health; City's Estate and City Bridge Foundation are separate. PDF p5, recommendation 1.9. Retrieved in the London report ledger."),
    ("MHCLG: national Table 2, 2026–27", "https://assets.publishing.service.gov.uk/media/6a280e823b15d05a7ce31f6c/RA_2026-27_Table_2.ods", "Table_2a, 2026–27 net current expenditure column C, £ million. Cross-checked against RA England theme totals to rounding. Same publisher/underlying return, not independent corroboration."),
    ("Redbridge Independents: overall design source", "https://redbridgeindys.org/", "Inspected 21 October 2026. Inline theme primary #06296D, alternate #FDD300; live headings use Barlow / Barlow Condensed and body declares century-gothic. Source of the overall UI identity, not a council-budget data source or council endorsement."),
    ("Source-site homepage typography and yellow", "https://redbridgeindys.org/wp-content/uploads/elementor/css/post-21162.css?ver=1791596251", "Homepage heading rules specify Barlow Condensed, weight 800, #FDD200. The atlas uses this yellow for rules and dark-mode accents, not low-contrast body text on white."),
    ("Source-site global typography", "https://redbridgeindys.org/wp-content/uploads/elementor/css/post-7.css?ver=1791233516", "Body font declaration century-gothic; primary Barlow Condensed 600; secondary colour #54595F used for accessible muted text. Century Gothic is local-only: redistribution rights were not established."),
    ("Barlow Condensed: SIL Open Font License", "https://raw.githubusercontent.com/google/fonts/main/ofl/barlowcondensed/OFL.txt", "OFL 1.1. Font files at weights 400/600/700/800 are embedded with the licence; offline fallback Arial Narrow/Arial. Not modified."),
    ("Barlow: SIL Open Font License", "https://raw.githubusercontent.com/google/fonts/main/ofl/barlow/OFL.txt", "OFL 1.1. Barlow 400/600/700 is embedded as the offline body fallback when local Century Gothic is unavailable. Barlow also appears in the source site's live main heading. Not modified."),
    ("MHCLG: council-tax statistics and collection measures", "https://www.gov.uk/government/collections/council-tax-statistics", "Separate official tax-base, Band D and collection publications. Actual receipts and collection rates are not imported into the 2026–27 budget financing comparison."),
]


def money(value, exact=False):
    if value is None:
        return "Not available"
    if exact:
        return f"£{value * 1000:,.0f}"
    sign = "−" if value < 0 else ""
    return f"{sign}£{abs(value) / 1000:,.3f}m"


def citation(number, title=None):
    return f'<a class="citation" href="#source-{number}" aria-label="Source {number}"{f" title={chr(34)}{esc(title)}{chr(34)}" if title else ""}>[{number}]</a>'


def column_name(number):
    name = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        name = chr(65 + remainder) + name
    return name


def build():
    atlas = json.loads((DATA / "processed" / "atlas.json").read_text(encoding="utf-8"))
    reports_path = DATA / "processed" / "london_reports.json"
    colours_path = DATA / "processed" / "council_colours.json"
    reports = json.loads(reports_path.read_text(encoding="utf-8")) if reports_path.exists() else []
    colours = json.loads(colours_path.read_text(encoding="utf-8")) if colours_path.exists() else {}
    logos = json.loads((DATA / "processed" / "council_logos.json").read_text(encoding="utf-8"))
    if any(item["permission"] == "permitted" for item in logos.values()):
        raise ValueError("A newly cleared logo requires a reviewed, sanitized embedding implementation; do not silently ignore permitted assets.")
    if isinstance(colours, list):
        colours = {c["ons"]: c for c in colours}
    sources = SOURCES.copy()
    for report in reports:
        report["sourceNumber"] = len(sources) + 1
        sources.append((report["title"], report["url"], f'{report["council"]}. {report.get("date") or "Date not separately established"}. {report.get("note", "")} Retrieved {report.get("retrieved", "2026-10-21")}.'))
    for code, colour in colours.items():
        if colour.get("colour"):
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", colour["colour"]):
                raise ValueError(f"Invalid identity colour: {code}")
            colour["sourceNumber"] = len(sources) + 1
            sources.append((f'{colour.get("name", code)}: official identity colour', colour["source"], f'{colour.get("method", "Logo colour")}. {colour.get("note", "")} Exact swatch {colour["colour"]}; text remains in the accessible UI colour.'))
    authorities = {a["code"]: a for a in atlas["authorities"]}
    fields = {f["id"]: f for f in atlas["fields"]}
    focus, compare = authorities["E09000026"], authorities["E09000031"]
    atlas["reports"], atlas["colours"], atlas["logos"] = reports, colours, logos

    def council(code):
        a, identity = authorities[code], colours.get(code, {})
        known = bool(identity.get("colour"))
        title = f'Official identity colour: {identity["colour"]}' if known else "Official identity colour not yet verified"
        return f'<span class="council{"" if known else " unknown"}" data-council="{code}" data-logo-state="{logos.get(code,{}).get("permission","not-researched")}" style="--cp-council:var(--cp-council-{code},var(--cp-border))" title="{esc(title)}">{esc(a["name"])}</span>'

    def locator(a, f):
        return f'{f["sheet"]}!{column_name(f["column"])}{a["rows"][f["part"]]} · line {f["line"]} · {f["asset"]}'

    def value(a, f):
        return money(a["values"][f["id"]]) + citation(f["source"], locator(a, f))

    def benchmark_rate(a, f):
        n = a["values"][f["id"]]
        return n * 1000 / a["population"]["value"] if n is not None and a["population"] else None

    def benchmark_text(f):
        if f["kind"] not in ("service", "theme") and f["id"] != "ra1_servicetot":
            return "Not benchmarked as a service-spending line: financing, reserves and other accounting items have different meanings."
        own, other = benchmark_rate(focus, f), benchmark_rate(compare, f)
        if own is None or other is None:
            return "Insufficient comparison data. No missing amount or denominator is treated as zero."
        delta = own - other
        percent = f"{delta / other * 100:+.1f}%" if other > 0 else "percentage not reported for a zero or negative benchmark"
        return f'{council(focus["code"])} {value(focus,f)}; £{own:,.0f} per resident versus {council(compare["code"])} £{other:,.0f}. Difference £{delta:+,.0f} per resident ({percent}); 1 valid peer, direct comparison. Residents are scale, not service users or need.{citation(8)} <strong>Investigate, not a verdict.</strong> Matched need/outcomes are not imported; <a href="#funding">funding context</a> is not a demand adjustment.'

    def benchmark_table(items):
        rows = []
        for f in sorted(items, key=lambda f: abs((benchmark_rate(focus,f) or 0) - (benchmark_rate(compare,f) or 0)), reverse=True):
            own, other = benchmark_rate(focus,f), benchmark_rate(compare,f)
            delta = own-other if own is not None and other is not None else None
            rate = lambda n: f"£{n:,.0f}" if n is not None else "Not available"
            pct = f"{delta/other*100:+.1f}%" if delta is not None and other is not None and other>0 else "Not reported: zero/negative/missing base"
            rows.append(f'<tr data-benchmark-row="{f["id"]}"><th scope="row"><a href="#line-{f["id"]}">{esc(f["label"])}</a></th><td class="num">{value(focus,f)}</td><td class="num">{value(compare,f)}</td><td class="num">{rate(own)}{citation(8)}</td><td class="num">{rate(other)}{citation(8)}</td><td class="num">{rate(delta)}</td><td>{pct}</td><td>1 valid peer · direct comparison</td><td>Investigate. {esc(f["denominator"]["preferred"])}: {esc(f["denominator"]["availability"])}. Matched need/outcomes not imported.</td></tr>')
        return '<table><caption>2026–27 planned spending differences · resident scale · default Waltham Forest comparison, not identified overspend/underspend</caption><thead><tr><th scope="col">Published service</th><th scope="col">Redbridge budget £m</th><th scope="col">Peer budget £m</th><th scope="col">Redbridge £ / resident</th><th scope="col">Peer £ / resident</th><th scope="col">Difference £ / resident</th><th scope="col">Difference %</th><th scope="col">Evidence count</th><th scope="col">What to check</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'

    def peer_table():
        rows = []
        for a in atlas["authorities"]:
            if a["class"] != "LB" or a["code"] == "E09000001":
                continue
            pop = a["population"]
            residents = f'{pop["value"]:,}' if pop else "Not joined"
            rows.append(f'<tr><th scope="row">{council(a["code"])}</th><td class="num">{value(a, fields["ra1_servicetot"])}</td><td class="num">{residents}{citation(8)}</td><td>{esc(locator(a,fields["ra1_servicetot"]))}</td></tr>')
        return '<table><caption>London boroughs · 2026–27 budget · net service expenditure</caption><thead><tr><th scope="col">Council</th><th scope="col">Budget (£m)</th><th scope="col">Residents (mid-2025)</th><th scope="col">Source locator [1]</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'

    def theme_table():
        rows = "".join(f'<tr><th scope="row">{esc(name)}</th><td class="num">{value(focus,fields[key])}</td><td class="num">{value(compare,fields[key])}</td></tr>' for name, key in zip(atlas["meta"]["themeNames"], atlas["meta"]["themeIds"]))
        return '<table><caption>2026–27 net service theme budgets · £m</caption><thead><tr><th scope="col">Theme</th><th scope="col">' + council(focus["code"]) + '</th><th scope="col">' + council(compare["code"]) + '</th></tr></thead><tbody>' + rows + '</tbody></table>'

    def government(a):
        values = [a["values"][key] for key in ("ra1_grantinaef", "ra1_grantrsg", "ra1_grantpol")]
        return -sum(values) if all(v is not None for v in values) else None

    def share(value, total):
        return f"{value / total * 100:.1f}%" if value is not None and total else "Not available"

    def resident(value, a):
        return f'£{value * 1000 / a["population"]["value"]:,.0f}' if value is not None and a["population"] else "Not available"

    def funding_table():
        rows = []
        for item in atlas["meta"]["fundingLines"]:
            cells = []
            f = fields[item["id"]]
            for a in (focus, compare):
                n = a["values"][item["id"]]
                contribution = n * item["sign"] if n is not None else None
                cells.append(f'<td class="num">{money(contribution)}{citation(1,locator(a,f))}</td><td class="num">{resident(contribution,a)}{citation(8)}</td><td class="num">{share(contribution,a["values"]["ra1_revenuetot"])}</td>')
            rows.append(f'<tr><th scope="row">{esc(item["label"])} · RA {f["line"]}</th>{"".join(cells)}</tr>')
        rows.append('<tr><th scope="row">Reconciling revenue expenditure · RA 900</th>' + "".join(f'<td class="num">{value(a,fields["ra1_revenuetot"])}</td><td class="num">{resident(a["values"]["ra1_revenuetot"],a)}{citation(8)}</td><td class="num">{share(a["values"]["ra1_revenuetot"],a["values"]["ra1_revenuetot"])}</td>' for a in (focus,compare)) + '</tr>')
        return '<table><caption>Complete signed financing comparison · 2026–27 budget · shares of RA 900 (not RA 799)</caption><thead><tr><th scope="col">Financing line / contribution</th>' + "".join(f'<th scope="col">{council(a["code"])} £m</th><th scope="col">£ / resident</th><th scope="col">Share of total</th>' for a in (focus,compare)) + '</tr></thead><tbody>' + "".join(rows) + '</tbody></table>'

    def funding_peer_table():
        rows = []
        for a in atlas["authorities"]:
            if a["class"] != "LB" or a["code"] == "E09000001":
                continue
            reserves = sum(-a["values"]["ra1_"+key] for key in ("appressch","appresdsg","appresph","appresoth","appresunall")) if a["returned"] else None
            rates = -a["values"]["ra1_retainnndr"] if a["returned"] else None
            rows.append(f'<tr><th scope="row">{council(a["code"])}</th><td class="num">{value(a,fields["ra1_ctrtot"])}</td><td class="num">{money(government(a))}{citation(1)}</td><td class="num">{money(rates)}{citation(1)}</td><td class="num">{money(reserves)}{citation(1)}</td><td class="num">{value(a,fields["ra1_revenuetot"])}</td><td class="num">{resident(a["values"]["ra1_revenuetot"],a)}{citation(8)}</td></tr>')
        return '<table><caption>London borough financing · 2026–27 budget · £m; signed contributions. Collection-fund/transfers/other items remain in the detailed reconciliation.</caption><thead><tr><th scope="col">Authority</th><th scope="col">Own council tax</th><th scope="col">Government grants</th><th scope="col">Retained rates</th><th scope="col">Net reserves use</th><th scope="col">Revenue total</th><th scope="col">Total £ / resident</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'

    def funding_cards():
        return '<div class="stat-grid">' + "".join(f'<div class="stat"><span>{label} · {council(focus["code"])}</span><strong>{money(amount)}{citation(1)}</strong><span>{resident(amount,focus)} per resident · {share(amount,focus["values"]["ra1_revenuetot"])} of RA 900{citation(8)}</span></div>' for label,amount in (("Own council-tax requirement",focus["values"]["ra1_ctrtot"]),("Explicit central-government grants",government(focus)),("Reconciling revenue expenditure",focus["values"]["ra1_revenuetot"]))) + '</div>'

    def capitalisation():
        return f'<strong>Capitalisation is not a government grant.</strong> {council(focus["code"])} reports {value(focus,fields["ra1_netoffexpcap"])} for “netting off expenditure capitalised by a direction under Section 16(2)b)” (RA 868). This is a non-current adjustment on the route to revenue expenditure, not extra grant income in the financing mix. Borrowing, flexible capital receipts, reserve use and Exceptional Financial Support are not interchangeable; the return does not independently identify all EFS arrangements.'

    spending_funding = f'<p><strong>Funding context · 2026–27:</strong> {council(focus["code"])} own council-tax requirement {value(focus,fields["ra1_ctrtot"])}; explicit government grants {money(government(focus))}{citation(1)}. This finances the revenue-expenditure perimeter, not an earmarked allocation to the selected service. <a href="#funding">Read the funding reconciliation</a>.</p>'

    minimum = min(0, *(focus["values"][key] for key in atlas["meta"]["themeIds"]))
    maximum = max(1, *(focus["values"][key] for key in atlas["meta"]["themeIds"]))
    span = maximum - minimum
    bars = "".join(f'<div class="theme-row"><a href="#line-{key}">{esc(name)}</a><div class="track" style="--zero:{-minimum/span*100:.3f}%" aria-hidden="true"><span class="fill" style="--bar:{100*abs(focus["values"][key])/span:.3f}%;left:{(min(0,focus["values"][key])-minimum)/span*100:.3f}%;--cp-council:var(--cp-council-E09000026);background:var(--cp-council,var(--cp-accent))"></span></div><span class="value">{value(focus,fields[key])}</span></div>' for key, name in zip(atlas["meta"]["themeIds"], atlas["meta"]["themeNames"]))

    catalog = []
    for f in atlas["fields"]:
        identifier = f["id"]
        denominator = f["denominator"]
        is_service = f["kind"] == "service"
        if is_service:
            explanation = f'Planned net revenue provision reported for “{f["label"]}” within {f["group"]}. It is net of the service income specified in the return; it is not gross spending or an actual-spend observation.'
        elif f["kind"] == "theme":
            explanation = f'Published theme subtotal for {f["group"]}. Included once in total service expenditure, not added again alongside its detailed components.'
        elif f["part"] == "sg":
            explanation = "A specific or special revenue grant, not an additional service-cost line. AEF means Aggregate External Finance. Grant totals and their components overlap and must not be added together."
        elif f["asset"].startswith("hra") or f["asset"].startswith("reshra"):
            explanation = "A separate Housing Revenue Account item for council-owned housing. Read the label as income, expenditure, reserves or annual surplus/deficit; do not add it to the General Fund service total."
        elif f["asset"].startswith("res"):
            explanation = "A reserve balance or reserve memorandum item at the date in its label, not annual service spending. Components can overlap; High Needs Stability Grant recording differs between authorities."
        else:
            explanation = "An accounting, financing or memorandum item, not necessarily a service cost. Preserve the published sign and date. Subtotals, income, adjustments and components must not be summed indiscriminately."
        status = "Available where an exact road-network join exists; network-scale context only." if denominator["availability"] == "available-where-joined" else ("Not imported — no service-unit ratio is displayed." if is_service else "Not applicable as a service-output ratio.")
        table = f'<table><caption>Selected authorities · 2026–27 budget · £m</caption><thead><tr><th scope="col">Authority</th><th scope="col">Published amount</th></tr></thead><tbody><tr><th scope="row" data-name="focus">{council(focus["code"])}</th><td class="num" data-value="{identifier}" data-authority="focus">{value(focus,f)}</td></tr><tr><th scope="row" data-name="compare">{council(compare["code"])}</th><td class="num" data-value="{identifier}" data-authority="compare">{value(compare,f)}</td></tr></tbody></table>'
        catalog.append(f'''<section class="service" id="line-{identifier}" aria-labelledby="heading-{identifier}" data-kind="{f["kind"]}" data-search="{esc((f["label"]+" "+f["group"]+" "+f["asset"]+" "+f["line"]).lower())}">
<details><summary><h3 id="heading-{identifier}">{esc(f["label"])}</h3><div class="service-summary"><span>{esc(f["group"])} · {esc(f["part"].upper())} line {esc(f["line"])}</span><span class="value" data-summary-value="{identifier}" title="{esc(locator(focus,f))}; linked source inside expanded section">{money(focus["values"][identifier])}</span></div></summary>
<div class="service-body"><div><h4>What this line measures</h4><p>{esc(explanation)}{citation(f["source"])}{citation(6)}</p><p class="note" data-benchmark="{identifier}">{benchmark_text(f)}</p><figure class="ledger-figure js-only"><h4>{esc(f["label"])} · selected-council chart</h4><label>Chart measure<select data-ledger-metric="{identifier}"><option value="absolute">Published amount (£m)</option><option value="resident">£ per resident — scale, not service unit cost</option><option value="roads">{"£ per network mile — maintenance proxy, not audited cost" if denominator.get("key")=="roads" else "Network-mile lens unavailable for this line"}</option></select></label><div class="ledger-chart" data-ledger-chart="{identifier}" tabindex="0" aria-label="{esc(f["label"])} chart"><p>Chart renders when this section opens. The source-linked table below is available without JavaScript.</p></div><figcaption data-ledger-caption="{identifier}">2026–27 return. Read the original accounting label and preferred denominator; no unit cost is inferred.</figcaption></figure><div class="table-scroll">{table}</div><p class="small muted">Source identifiers: {esc(f["sheet"])} · column {column_name(f["column"])} · asset {esc(f["asset"])} · header row {f["headerRow"]}. Exact authority rows travel with each figure.</p><button type="button" class="js-only" data-explore="{identifier}">Compare this line across the peer group</button></div><div><h4>Preferred service denominator</h4><p><strong>{esc(denominator["preferred"])}</strong></p><p>{esc(denominator["definition"])}{citation(denominator["source"])}</p><p class="note">{esc(status)}</p><p class="small">Resident-scale alternative: amount in £ thousands × 1,000 ÷ ONS mid-2025 residents (where joined). This is not demand adjustment. Service-user data year: not imported unless explicitly stated above.</p></div></div></details></section>''')

    road = focus["roads"]
    road_value = focus["values"]["ra1_transrdsmnt"]
    formula = f'{council(focus["code"])}<br>{money(road_value,True)} planned structural maintenance ÷ ({road["major"]} + {road["minor"]}) miles = <strong>£{road_value*1000/road["value"]:,.0f} per network mile</strong>{citation(1,locator(focus,fields["ra1_transrdsmnt"]))}{citation(7)}'
    roads_rows = "".join(f'<tr><th scope="row">{council(a["code"])}</th><td class="num">{value(a,fields["ra1_transrdsmnt"])}</td><td class="num">{a["roads"]["value"] if a["roads"] else "Not joined"}{citation(7)}</td></tr>' for a in (focus,compare))
    roads_table = '<table><caption>RA line 230 (£m) and DfT network miles (2025)</caption><thead><tr><th scope="col">Council</th><th scope="col">Structural maintenance</th><th scope="col">Local miles</th></tr></thead><tbody>' + roads_rows + '</tbody></table>'
    report_rows = []
    for report in sorted(reports, key=lambda r: r["council"]):
        a = authorities[report["ons"]]
        headline = f'£{report["localHeadline"]:,.0f}' if report.get("localHeadline") is not None else "No headline transcribed"
        report_rows.append(f'<tr data-report-search="{esc((report["council"]+" "+str(report.get("localMeasure",""))).lower())}"><th scope="row">{council(a["code"])}</th><td><a href="#source-{report["sourceNumber"]}">{esc(report["title"])}</a>{citation(report["sourceNumber"])}<br><small>{esc(report["status"])} · {esc(report.get("date") or "Date not established")} · {esc(report.get("format",""))}</small></td><td class="num">{value(a,fields["ra1_servicetot"])}</td><td class="num">{value(a,fields["ra1_revenuetot"])}</td><td>{headline}<br><small>{esc(report.get("localMeasure") or "Definition not separately transcribed")}</small><br><small>{esc(report.get("localLocator") or "")}</small></td><td>{esc(report.get("note",""))}</td></tr>')
    report_ledger = '<table><caption>2026–27 London report ledger · common RA figures in £m; local report headlines in £</caption><thead><tr><th scope="col">Council</th><th scope="col">Council report / verification</th><th scope="col">RA service budget</th><th scope="col">RA revenue expenditure</th><th scope="col">Local report headline &amp; scope</th><th scope="col">Comparability note</th></tr></thead><tbody>' + "".join(report_rows) + '</tbody></table>'
    audit_rows = []
    for a in atlas["authorities"]:
        population, roads = a["population"], a["roads"]
        p = f'{population["value"]:,} · MYE2 Persons D{population["row"]}' if population else "Not joined"
        r = f'{roads["major"]} + {roads["minor"]} = {roads["value"]} · RDL0102a M{roads["row"]} + S{roads["row"]}' if roads else "Not joined"
        audit_rows.append(f'<tr><th scope="row">{council(a["code"])}</th><td>{a["code"]} · {esc(a["subclass"])}</td><td>{p}{citation(8)}</td><td>{r}{citation(7)}</td></tr>')
    audit = '<table><caption>Exact-code join audit · residents mid-2025; road miles 2025</caption><thead><tr><th scope="col">Authority</th><th scope="col">ONS code / responsibilities</th><th scope="col">Residents / source cell</th><th scope="col">Road miles / source cells</th></tr></thead><tbody>' + "".join(audit_rows) + '</tbody></table>'
    colour_rows = []
    for a in atlas["authorities"]:
        identity = colours.get(a["code"], {})
        provenance = f'<a href="#source-{identity["sourceNumber"]}">{esc(identity["colour"])}</a>{citation(identity["sourceNumber"])} · {esc(identity.get("method",""))}' if identity.get("colour") else "Unknown — logo colour not verified"
        colour_rows.append(f'<tr><th scope="row">{council(a["code"])}</th><td>{provenance}</td></tr>')
    colour_ledger = '<table><caption>Council identity colours: official-logo provenance; unknowns are not assigned an invented palette</caption><thead><tr><th scope="col">Authority</th><th scope="col">Exact swatch / evidence</th></tr></thead><tbody>' + "".join(colour_rows) + '</tbody></table>'
    logo_rows = "".join(f'<tr><th scope="row">{council(code)}</th><td>{esc(item["permission"])}</td><td>{esc(item["note"])}{f""" <a href="{esc(item["permissionSource"],quote=True)}">Official usage terms</a>""" if item.get("permissionSource") else ""} <a href="{esc(item["source"],quote=True)}">Official asset source</a></td></tr>' for code,item in logos.items())
    logo_ledger = '<table><caption>Official logo reuse audit · no asset is treated as permission-cleared by default</caption><thead><tr><th scope="col">Council</th><th scope="col">Reuse state</th><th scope="col">Permission evidence / named-swatch fallback</th></tr></thead><tbody>' + logo_rows + '</tbody></table>'
    mapping_rows = "".join(f'<tr><th scope="row"><a href="#line-{f["id"]}">{esc(f["id"])}</a></th><td>{esc(f["label"])}</td><td>{esc(", ".join(f["aliases"])) or "No display alias"}</td><td>{esc(f["part"].upper())} · {esc(f["asset"])} · line {esc(f["line"])} · column {column_name(f["column"])}{citation(f["source"])}</td><td>Exact official code; no monetary transformation or name matching</td></tr>' for f in atlas["fields"])
    mapping_table = '<table><caption>All 321 canonical fields · original return labels and display aliases · 2026–27 £ thousands</caption><thead><tr><th scope="col">Canonical ID</th><th scope="col">Original official label</th><th scope="col">Display alias</th><th scope="col">Official definition locator</th><th scope="col">Mapping rationale</th></tr></thead><tbody>' + mapping_rows + '</tbody></table>'
    known = sum(bool(c.get("colour")) for c in colours.values())
    known_london = sum(bool(colours.get(a["code"],{}).get("colour")) for a in atlas["authorities"] if a["class"]=="LB")
    def comparison_option(authority):
        code = authority["code"]
        responsibility = authority["subclass"] if authority["class"] == "O" else {
            "LB": "London borough", "MD": "Metropolitan district", "UA": "Unitary authority",
            "SC": "Shire county", "SD": "Shire district",
        }[authority["class"]]
        notes = [responsibility]
        if code == "E09000001" or authority["class"] != "LB":
            notes.append("Different responsibilities; outside borough benchmark")
        if not authority["returned"]:
            notes.append("Budget not returned")
        search = esc(" ".join([authority["name"], responsibility, authority["subclass"], code]).lower())
        checked = " checked" if authority == compare else ""
        return f'<label class="comparison-option" data-option-search="{search}"><input type="checkbox" name="comparison" value="{code}"{checked}><span>{council(code)}<small>{esc(" · ".join(notes))}</small></span></label>'

    replacements = {
        "REDBRIDGE": '<span data-focus-name>' + council("E09000026") + '</span>', "BARNSLEY": council("E08000038"), "SHEFFIELD": council("E08000039"),
        "CITY": council("E09000001"), "GREENWICH": council("E09000011"),
        "HERO_TOTAL": money(focus["values"]["ra1_servicetot"]),
        "TAX_TOTAL": money(focus["values"]["ra1_ctrtot"]),
        "CURRENT_TOTAL": money(focus["values"]["ra1_netcurrtot"]),
        "REVENUE_TOTAL": money(focus["values"]["ra1_revenuetot"]),
        "COMPARISON_CHECKBOXES": "".join(comparison_option(a) for a in sorted(atlas["authorities"],key=lambda a:(a["class"]!="LB",a["name"])) if a!=focus),
        "SELECTION_LABELS": council(focus["code"])+" <span>vs</span> "+council(compare["code"]),
        "LINE_OPTIONS": "".join(f'<option value="{f["id"]}"{" selected" if f["id"]=="ra1_servicetot" else ""}>{esc(f["label"])} · {esc(f["part"].upper())} {esc(f["line"])}</option>' for f in atlas["fields"]),
        "THEME_BARS": bars, "THEME_TABLE": theme_table(), "STORY_TABLE": theme_table(),
        "PEER_TABLE": peer_table(), "ROADS_FORMULA": formula, "ROADS_TABLE": roads_table,
        "SERVICE_CATALOG": "".join(catalog), "REPORT_LEDGER": report_ledger,
        "REPORT_COVERAGE": f'{sum(r["status"]=="retrieved" for r in reports)} of 33 London council budget reports retrieved. The status, scope and any missing report evidence are shown council by council. Common RA figures remain unavailable for Greenwich.',
        "MISSING_NAMES": ", ".join(council(a["code"]) for a in atlas["authorities"] if not a["returned"]),
        "POPULATION_COVERAGE": f'{atlas["meta"]["populationJoins"]} of 415 authority entries have a population join (including overlapping county/GLA areas; never summed).',
        "ROAD_COVERAGE": f'{atlas["meta"]["roadJoins"]} of 415 authority entries have an exact road-network join.',
        "DENOMINATOR_AUDIT": audit, "COLOUR_LEDGER": colour_ledger,
        "FUNDING_CARDS": funding_cards(), "FUNDING_TABLE": funding_table(),
        "FUNDING_PEER_TABLE": funding_peer_table(), "CAPITALISATION_CONTEXT": capitalisation(),
        "SPENDING_FUNDING_CONTEXT": spending_funding,
        "BENCHMARK_METHOD": council(focus["code"]) + " versus " + council(compare["code"]) + ": one selected London borough peer; direct comparison. Default lens: £ per resident, mid-2025. Change selections above; no outcome or need adjustment is claimed.",
        "BENCHMARK_TABLE": benchmark_table([f for f in atlas["fields"] if f["kind"] == "service"]),
        "HEADLINE_BENCHMARKS": "",
        "THEME_BENCHMARKS": benchmark_table([fields[key] for key in atlas["meta"]["themeIds"]]),
        "TOTAL_BENCHMARK": '<p class="note">' + benchmark_text(fields["ra1_servicetot"]) + "</p>",
        "IDENTITY_COVERAGE": f'Official identity colours verified for {known_london} of 33 London councils and {known} of 415 authority entries overall. Most come from official logos; Redbridge uses the requested dark red #942725, its official primary-palette chestnut, rather than black wordmark pixels. Its current homepage header separately uses mulberry #bc0067, not the selected dark-red palette colour. Every unverified identity is explicitly unknown; the neutral dashed indicator is not a brand claim.',
        "LOGO_COVERAGE": f'{len(logos)} official identity assets researched: 0 reuse permissions established; {sum(item["permission"]=="restricted" for item in logos.values())} explicitly restricted, {sum(item["permission"]=="not-established" for item in logos.values())} not established. No council logo is embedded or hotlinked. Names and verified swatches remain visible everywhere. Redbridge permission is not established; Waltham Forest requires consent. Assets are retained as research evidence, not licensed reusable branding.',
        "LOGO_LEDGER": logo_ledger,
        "CONSOLIDATION_TABLE": mapping_table,
        "SOURCES": "".join(f'<li id="source-{i}"><a href="{esc(url,quote=True)}">{esc(title)}</a><span class="source-meta">{esc(note)}</span></li>' for i,(title,url,note) in enumerate(sources,1)),
    }
    page = (ROOT / "src" / "page.html").read_text(encoding="utf-8")
    for marker, content in replacements.items():
        page = page.replace(f"<!-- {marker} -->", content)
    css = (ROOT / "src" / "atlas.css").read_text(encoding="utf-8")
    design = json.loads((DATA / "provenance" / "design.json").read_text(encoding="utf-8"))
    font_css = []
    for font in design["fonts"]:
        path = ROOT / font["file"]
        font_format = "woff2" if path.suffix == ".woff2" else "truetype"
        mime = "font/woff2" if path.suffix == ".woff2" else "font/ttf"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        font_css.append(f'@font-face{{font-family:"{font["family"]}";font-style:normal;font-weight:{font["weight"]};font-display:swap;src:url(data:{mime};base64,{encoded}) format("{font_format}");}}')
    for licence in ("BarlowCondensed-OFL.txt", "Barlow-OFL.txt"):
        font_css.append("/* Bundled font licence:\n" + (DATA / "raw" / "design" / licence).read_text(encoding="utf-8").replace("*/", "* /") + "\n*/")
    css = "\n".join(font_css) + "\n" + css
    css += "\n:root {\n" + "".join(f'  --cp-council-{code}: {c["colour"]};\n' for code,c in colours.items() if c.get("colour")) + "}\n"
    page = re.sub(
        r'<div class="table-scroll"([^>]*)>',
        lambda match: match[0] if "tabindex=" in match[1] else '<div class="table-scroll" tabindex="0"' + match[1] + ">",
        page,
    )
    assert not re.search(r"<!-- [A-Z_]+ -->", page)
    write_documents(ROOT, page, atlas, css)


if __name__ == "__main__":
    build()
