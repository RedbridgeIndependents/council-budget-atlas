"""Publish shared editorial fragments as real, offline-addressable documents."""

import html
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re


class Elements(HTMLParser):
    """Locate balanced elements without rewriting their source HTML."""

    def __init__(self, source, tag, predicate=lambda attrs: True):
        super().__init__(convert_charrefs=False)
        self.source, self.tag, self.predicate = source, tag, predicate
        self.lines = [0]
        self.lines.extend(match.end() for match in re.finditer("\n", source))
        self.stack, self.matches = [], []
        self.feed(source)

    def source_offset(self):
        row, column = self.getpos()
        return self.lines[row - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag == self.tag:
            self.stack.append((self.source_offset(), dict(attrs)))

    def handle_endtag(self, tag):
        if tag == self.tag and self.stack:
            start, attrs = self.stack.pop()
            if self.predicate(attrs):
                end = self.source.index(">", self.source_offset()) + 1
                self.matches.append((start, end, attrs))

    def fragments(self):
        return {attrs.get("id", ""): self.source[start:end] for start, end, attrs in self.matches}


def element(source, tag, identifier):
    matches = Elements(source, tag, lambda attrs: attrs.get("id") == identifier).matches
    if len(matches) != 1:
        raise ValueError(f"Expected one {tag}#{identifier}, got {len(matches)}")
    start, end, _ = matches[0]
    return source[start:end]


def write_documents(root, page, atlas, css):
    esc = html.escape
    sections = Elements(page, "section").fragments()
    services = [f for f in atlas["fields"] if f["kind"] == "service"]
    paths = {f["id"]: f'services/{f["id"]}.html' if f["kind"] == "service" else f'accounting.html#line-{f["id"]}' for f in atlas["fields"]}
    atlas["documents"] = {
        "overview": "index.html", "funding": "funding.html",
        "methodology": "methodology.html", "accounting": "accounting.html",
        "fields": paths,
    }
    original_controls = element(page, "div", "comparison-controls")
    controls = original_controls
    spending_context = element(page, "div", "spending-funding-context")
    theme_button = element(page, "button", "theme-toggle")
    selection = element(page, "p", "selection-status")
    notices = '<p id="navigation-notice" class="note" role="status" hidden></p><noscript><p class="note">JavaScript is off. These documents show the sourced default comparison: Redbridge and Waltham Forest. URL-selected councils and metrics require JavaScript. Every document, service directory, source link and initial data table remains readable offline.</p></noscript>'
    common = f'<section class="wrap document-controls" aria-label="Shared comparison settings">{controls}{selection}{notices}</section>'
    funding = sections["funding"]
    for fragment in (original_controls, element(page, "p", "selection-status")):
        funding = funding.replace(fragment, "")
    funding = re.sub(r"<noscript>.*?</noscript>", "", funding, flags=re.S)
    funding = funding.replace(
        element(funding, "h1", "funding-title"),
        '<h1 id="funding-title">How the budget<br>is funded.</h1>',
    )
    funding = funding.replace("Go straight to Redbridge’s spending differences", "Return to the spending overview")
    directory = []
    for field in services:
        directory.append(f'<li class="directory-entry" data-directory-search="{esc((field["label"]+" "+field["group"]+" "+field["asset"]).lower())}" data-directory-group="{esc(field["group"])}"><a href="{paths[field["id"]]}">{esc(field["label"])}</a><small>{esc(field["group"])} · RA line {esc(field["line"])} · {esc(field["asset"])}</small></li>')
    groups = sorted({f["group"] for f in services})
    directory_html = f'''<section class="chapter wrap" id="services" aria-labelledby="services-title">
<p class="eyebrow">Service directory</p><h2 id="services-title">One service.<br>One document.</h2>
<p class="lede">All 129 detailed services in the canonical 2026–27 return, each with its own comparison, chart, table and denominator audit. Published accounting lines are not literally every operational activity.</p>
<p>The 13 theme totals remain above. The 179 other financing, reserve, HRA and accounting fields, plus the 13 roll-ups, are retained in the <a href="accounting.html">technical accounting appendix</a>, not mislabeled as individual services. <a href="methodology.html#consolidation">How names are consolidated</a>.</p>
<div class="catalog-controls js-only"><label>Find a service<input id="directory-search" type="search" placeholder="Try libraries, roads, waste or safeguarding"></label><label>Service theme<select id="directory-group"><option value="">All themes</option>{"".join(f'<option>{esc(group)}</option>' for group in groups)}</select></label></div>
<p id="directory-count" role="status" class="small">129 service documents.</p><ul class="service-directory">{"".join(directory)}</ul></section>'''
    intro = f'''<section class="hero wrap" id="overview" aria-labelledby="overview-title">
<p class="eyebrow">The local ledger / 2026–27 budget edition</p>
<h1 id="overview-title">Where does<br><span class="council" data-council="E09000026" style="--cp-council:var(--cp-council-E09000026)">Redbridge</span><br>differ?</h1>
<p class="lede">Find the services where Redbridge plans to spend more or less than selected peers, by how much, and what to investigate next. Explore one service at a time; a difference is a question, not proof of waste or underprovision.</p>
<p class="byline">2026–27 budgets · release 11 June 2026 · source snapshot 21 October 2026 · England comparisons; devolved-nation gaps remain explicit.</p>
<p><a href="funding.html">Start with tax, grants and other funding →</a> · <a href="#review">See the investigation shortlist</a> · <a href="#services">Find an individual service</a></p>
<p class="note">Budgets are not actual-versus-budget overspend evidence. Residents are scale, not need or service-user cost. Matched outcomes/quality are not imported. City’s duties differ; Greenwich’s missing values remain absent. <a href="methodology.html">Read the coverage and evidence limits.</a></p></section>'''
    overview = intro + common + "".join(sections[key] for key in ("review", "total", "themes", "story", "london", "roads")) + directory_html
    funding = common + funding
    methods = f'<section class="hero wrap"><h1>Methods &amp;<br>sources.</h1><p class="lede">The definitions, coverage gaps, local reports and provenance behind every comparison.</p></section>' + common + sections["methods"] + sections["reports"] + sections["sources"]
    accounting = '<section class="hero wrap"><h1>The accounting<br>appendix.</h1><p class="lede">Published totals, financing, grants, reserves and HRA lines. These are not 192 separate operational services; overlapping accounting fields must not be added indiscriminately.</p></section>' + common + sections["services"]
    for field in services:
        accounting = accounting.replace(sections["line-" + field["id"]], "")
    accounting = accounting.replace("129 detailed service lines, 13 theme totals, and 179 further accounting and grant lines.", "13 theme totals and 179 further accounting and grant lines. The 129 individual service documents are linked in the overview directory.")
    accounting = accounting.replace("This is the complete numeric catalogue in the three imported workbooks", "Together with the individual service documents, this preserves the complete numeric catalogue in the three imported workbooks")
    accounting = accounting.replace("Every published line.<br>No invented detail.", "The accounting<br>appendix.")
    accounting = accounting.replace("All 321 numeric lines", "All 192 appendix lines")
    accounting = accounting.replace('<option value="service">129 detailed service lines</option>', "")
    accounting = accounting.replace("321 published numeric lines. Each has its own section.", "192 accounting / theme lines. Individual services have separate documents.")
    publications = {
        "index.html": ("overview", "Where does Redbridge differ?", overview, None),
        "funding.html": ("funding", "Funding: tax, grants and other finance", funding, None),
        "methodology.html": ("methods", "Methodology, London reports and sources", methods, None),
        "accounting.html": ("accounting", "Accounting and theme appendix", accounting, None),
    }
    for index, field in enumerate(services):
        identifier, label = field["id"], esc(field["label"])
        previous = services[index - 1] if index else None
        following = services[index + 1] if index + 1 < len(services) else None
        neighbours = "".join(f'<a rel="{relation}" href="{paths[item["id"]]}">{direction}: {esc(item["label"])}</a>' for item, relation, direction in ((previous, "prev", "Previous"), (following, "next", "Next")) if item)
        service = sections["line-" + identifier].replace("<details>", "<details open>", 1)
        service = service.replace('<section class="service"', '<section class="service service-document wrap"', 1)
        body = f'''<section class="hero wrap" aria-labelledby="service-title"><p class="eyebrow">{esc(field["group"])} / 2026–27 planned service spending</p><h1 id="service-title">{label}</h1><p class="lede">Where does Redbridge differ from the selected councils, and what evidence would explain the gap?</p><p class="note">Above/below a selected-peer benchmark is not proof of waste, overspending or underprovision. Need, commissioning, net income, funding constraints and service quality need checking. <a href="funding.html">Funding context</a> · <a href="methodology.html#consolidation">Canonical definitions</a>.</p></section>'''
        body += common + service
        body += '<aside class="wrap service-funding-context" aria-label="Funding context"><h2>Keep funding in view.</h2>' + spending_context + "</aside>"
        body += f'<nav class="wrap document-neighbours" aria-label="Adjacent services">{neighbours}</nav>'
        publications[paths[identifier]] = ("service", field["label"], body, identifier)
    owners = {}
    for path, (_, _, body, _) in publications.items():
        for identifier in re.findall(r'\bid="([^"]+)"', body):
            owners.setdefault(identifier, path)
    owners.update({key: path.split("#")[0] for key, path in ((f"line-{f['id']}", paths[f["id"]]) for f in atlas["fields"])})

    def local_link(current, target):
        path, _, anchor = target.partition("#")
        relative = posixpath.relpath(path, posixpath.dirname(current) or ".")
        return ("" if path == current and anchor else relative) + ("#" + anchor if anchor else "")

    def rewrite_links(current, markup):
        local_ids = set(re.findall(r'\bid="([^"]+)"', markup)) | {"top", "content"}
        def replace(match):
            target = html.unescape(match[1])
            if target.startswith("#") and target[1:] not in local_ids:
                if target[1:] not in owners:
                    raise ValueError(f"Unresolved fragment {target} in {current}")
                target = local_link(current, owners[target[1:]] + target)
            elif target.startswith(("services/", "index.html", "funding.html", "methodology.html", "accounting.html")):
                target = local_link(current, target)
            return f'href="{esc(target, quote=True)}"'
        return re.sub(r'href="([^"]*)"', replace, markup)

    theme_script = re.search(r"<script>.*?</script>", page, re.S)[0]
    output = []
    for path, (kind, title, body, field_id) in publications.items():
        prefix = "../" if "/" in path else ""
        nav = "".join(f'<a href="{target}"{" aria-current=page" if (target == path or kind=="service" and target=="index.html#services") else ""}>{label}</a>' for target, label in (("index.html", "Overview"), ("funding.html", "Funding"), ("index.html#services", "Services"), ("accounting.html", "Accounting"), ("methodology.html", "Methods / sources")))
        crumbs = '<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="index.html">Overview</a>' + ('<a href="index.html#services">Services</a>' if kind == "service" else "") + f'<span aria-current="page">{esc(title)}</span></nav>'
        source_ids = sorted({int(n) for n in re.findall(r'href="#source-(\d+)"', body)} | ({1, 5, 6, 8} if kind == "service" else set()))
        related = "" if kind == "methods" else f'<section class="wrap page-evidence" aria-labelledby="page-sources"><h2 id="page-sources">Evidence for this document</h2><p>2026–27 budget snapshot. Exact authority cells travel with the figures. {", ".join(f"""<a href="methodology.html#source-{n}">Source [{n}]</a>""" for n in source_ids)}. <a href="methodology.html#sources">Full numbered sources and limitations</a>.</p></section>'
        content = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Offline 2026–27 council budget evidence: {esc(title, quote=True)}"><title>{esc(title)} | Council budget atlas</title>{theme_script}<link rel="stylesheet" href="{prefix}assets/atlas.css"></head>
<body id="top" data-document="{kind}" data-root="{prefix}"{f' data-service-id="{field_id}"' if field_id else ""}>
<a class="skip" href="#content">Skip to content</a><header class="masthead"><progress class="progress" id="reading-progress" max="100" value="0" aria-label="Reading progress">0%</progress><div class="wrap masthead-inner"><a class="wordmark" href="index.html">Council<br>budget atlas</a><nav aria-label="Major sections">{nav}</nav>{theme_button}</div></header>
<main id="content" tabindex="-1"><div class="wrap">{crumbs}</div>{body}{related}</main><a class="back-top" href="#top"><span aria-hidden="true">↑</span> Back to top</a>
<footer class="wrap"><p>Council budget atlas · 2026–27 budgets · no council endorsement implied.</p><p>Public source repository. Works offline or on GitHub Pages; no analytics, cookies or runtime APIs.</p></footer>
<script src="{prefix}assets/atlas-data.js" defer></script><script src="{prefix}assets/navigation.js" defer></script><script src="{prefix}assets/benchmark.js" defer></script><script src="{prefix}assets/atlas.js" defer></script></body></html>'''
        content = rewrite_links(path, content)
        destination = root / Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
        output.append({"path": path, "kind": kind, "field": field_id, "bytes": len(content.encode("utf-8"))})
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "atlas.css").write_text(css, encoding="utf-8", newline="\n")
    (assets / "atlas-data.js").write_text("window.atlasData=" + json.dumps(atlas, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c") + ";\n", encoding="utf-8", newline="\n")
    for filename in ("navigation.js", "benchmark.js", "atlas.js"):
        (assets / filename).write_text((root / "src" / filename).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    (root / "data" / "processed" / "documents.json").write_text(json.dumps({"documents": output, "fieldPaths": paths}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f'Built {len(output)} offline documents: {len(services)} individual services; overview {output[0]["bytes"]:,} bytes. Shared data, fonts, styles and arithmetic are stored once in assets.')
