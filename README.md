# Council budget atlas

An offline editorial investigation of **where Redbridge's 2026–27 planned spending differs from selected peers**, initially Waltham Forest. Open **`index.html` directly in a browser**. No server, build step, externally loaded font, runtime API, analytics or public hosting is required. Keep the checkout's `assets/` and `services/` folders alongside the overview: this is now a collection of real HTML documents, not one self-contained file. The repository is private; do not enable GitHub Pages or change its visibility.

## Document layout and navigation

| Document | Contents |
|---|---|
| `index.html` | Overview, investigation shortlist, total spending, grouped themes, scroll story, England explorer, road example and searchable directory of all 129 services. No hidden full ledger. |
| `funding.html` | Own council-tax requirement, explicit government grants, retained rates, reserves and complete selected-council financing reconciliations. |
| `services/<canonical-id>.html` | **129 separate individual-service documents**, one for each official detailed-service field. Each has its own chart, source-linked table, benchmark, accounting definition, denominator gaps and selected-council funding context. |
| `methodology.html` | Methods, consolidation and denominator audits, UK coverage gaps, London report ledger, branding/permission evidence and full numbered sources. |
| `accounting.html` | Technical appendix retaining the other **192 fields: 13 theme totals and 179 accounting/grant/HRA/reserve lines**. These are not relabelled as operational services or added to their components. |

There are **133 HTML documents**. Major navigation is shared; individual services have breadcrumbs and previous/next links in canonical source order. The directory is searchable by official label, theme and asset code, and remains a full linked list without JavaScript. Figures cite the relevant numbered references in the methodology/sources document.

**Selections travel in the URL**, including when opening a link in a new tab, reloading, using breadcrumbs or returning with browser back/forward. `peers` is a comma-separated list of exact authority codes (Redbridge is always the reference); `peers=` explicitly means no comparisons, whereas an absent parameter defaults to Waltham Forest. `metric` is `absolute`, `resident` (default) or `roads`. The peer-explorer `group`/`line`, overview `filter`/`sort`, story step and `scoutTheme` are also preserved. Controls update the current history entry and relative document links; document navigation remains normal browser navigation. Invalid settings are reported visibly and rejected.

For example, `services/ra1_cullib.html?peers=E09000027,E09000029&metric=resident&scoutTheme=dark` opens the library comparison with Richmond and Sutton. A carried road-mile lens remains explicitly **unavailable** on ineligible services instead of silently switching measure. Funding keeps its explicitly labelled £m, resident context and RA 900 shares rather than reinterpreting them as a service-unit ratio.

All documents work directly under **`file://`**. Shared data are a local classic script, not a fetched JSON dependency; calculations, styles and licensed offline fonts are stored once in `assets/`. There is no router, server or local-storage dependency. Without JavaScript, every page states that its real static figures use the initial Redbridge/Waltham Forest comparison; query-selected values and charts require JavaScript. Source links and readable default tables still work.

## What is included

- All **415 English return authorities** in the MHCLG 11 June 2026 individual-authority release: **317 councils and 98 other authorities**, with **406 submitted returns** and nine explicitly missing.
- All **321 numeric fields** from RA parts 1 and 2 and the specific/special grants return: **129 detailed service documents**, **13 theme totals**, and **179 other accounting, financing, HRA, reserve and grant lines** retained in the technical appendix. Every field keeps its source locator and denominator catalogue entry.
- Funding first: own council-tax requirement, explicit central-government grants, retained rates, reserves and every other signed financing line, reconciling exactly to RA 900 for all 406 returns. Shares use that perimeter only. Actual tax receipts, collection rates, tax bases and Band D bills are **not** imported or confused with this budget requirement.
- Accessible multi-council checkboxes, selected-count/removal/clear/reset, and a one-action **All London councils** shortcut selecting all 33 entries, including City and missing Greenwich without duplicating Redbridge. The set follows funding, themes, detailed service/road tables and the scroll story.
- A prioritised, sortable/filterable shortlist of **129 detailed service lines**, with Redbridge's budget, selected-peer budget median, resident-scale/eligible road measure, benchmark difference, percentage where meaningful, valid count/range and linked service details. Redbridge remains the reference. Only selected London boroughs with an available matching measure enter the benchmark: no City, Redbridge itself, other authority class or missing value. One peer is a direct comparison; multiple peers use an unweighted median. Zero/negative benchmarks keep signed differences but do not receive misleading percentage comparisons.
- London-first peer exploration, absolute and resident-scale metrics, a restricted road-network-scale maintenance comparison, CSV export, accessible tables and source citations. Broader England groups remain available for context but do not silently populate selected benchmarks.
- Scroll-driven shared SVG charts on the overview, plus a comparison chart in **every service document and each technical-appendix line**, reading progress, cross-page navigation, keyboard/touch alternatives, light/dark themes, reduced-motion support and real initial data without JavaScript. Service charts open immediately; appendix charts render when expanded and release their SVG when collapsed. Each preserves negative/zero values, selected names/colours and a valid-peer benchmark where supported, with synchronized absolute/resident/eligible-road lenses and complete tables.
- **33 official London PDFs**, plus eight supporting files: 32 technical budget reports and Bromley's adopted-year council-tax/budget booklet. Bromley's full technical report remains inaccessible. **All 24 candidate local headlines were rechecked against the PDFs: 23 supported, Harrow withheld because £215m described 2025–26, not 2026–27.** The verification ledger retains 95 literal extracts for amounts, units, years, precision, scope and locators. No local headline is substituted into or asserted equivalent to RA service totals. Adoption/decision-evidence limitations remain explicit.
- Official logo/brand identity colours for **all 33 London councils**, **91 of 317 councils** overall (91/415 return authorities). Redbridge uses the user-requested official primary-palette chestnut **#942725**, not black wordmark pixels; its current header's different mulberry **#bc0067** is explicitly distinguished. Exact CSS provenance is retained. Other identities remain visibly unknown, never assigned arbitrary colours.
- A logo reuse audit for those 91 assets: **zero permission-cleared, five restricted, 86 not established**. Redbridge permission is not established and Waltham Forest requires consent. Accordingly, the page uses the requested readable name/swatch fallback rather than embedding or hotlinking unlicensed logos. Research assets are not licensed reusable branding.

**These are budgets, not actual spending.** The page distinguishes service expenditure (RA 799), net current expenditure (849), revenue expenditure (900), grants, HRA accounts and capital-related accounting items. Council reports can use different “net budget” definitions: their headlines are not substituted into the standard-return comparison.

**Above/below peer spending is not a verdict of over/underspending, waste or underprovision.** No same-scope actual-versus-budget analysis or matched needs/outcomes/quality data is imported. The output identifies investigation questions, not savings targets. Resident counts are scale, not users or service demand; funding mix is not a causal or efficiency adjustment. Benchmark differences must not be summed across parent/component lines.

## How service names are consolidated

The canonical taxonomy is the **published England RA/SG asset code and return part**, not a new fuzzy-matched council-directorate taxonomy. Every field retains its official label, code, source column/line, year and unit, with the council-specific workbook row kept separately. Editorial theme names are explicit display aliases only. `data/provenance/service_consolidation.json` and the in-page mapping table expose all 321 definitions.

All 33 supplementary report records keep their original local label, scope, year, amount and page locator where transcribed. **Zero local headlines have a verified equivalent service breakdown**: all remain unmapped/not-transcribed and excluded from benchmarks. No transport total is allocated to road maintenance, no General Fund/HRA combination is inferred, and no similarly worded directorates are merged. The only monetary roll-up is the 13 published non-overlapping themes to RA 799, reconciled against every returned council. No devolved-nation service crosswalk is claimed.

## Data, coverage and denominators

The checked snapshot is **21 October 2026**. The raw official files are pinned locally with SHA-256 hashes:

| Category | Location | Vintage |
|---|---|---|
| Revenue Account and grants | `data/raw/budgets/` | Financial year 2026–27; published 11 June 2026 |
| Residents | `data/raw/denominators/population_2025.xlsx` | ONS mid-2025; published 1 October 2026; MYE2 Persons, all ages |
| Roads | `data/raw/denominators/rdl0102.ods` | DfT 2025; updated 12 February 2026; RDL0102a |
| Council budget documents | `data/raw/reports/` | Official London council reports; see report ledger |
| Logo evidence | `data/raw/logos/` | Official identity assets; see colour ledger |
| Design and licensed fonts | `data/raw/design/` | Redbridge Independents design evidence, Barlow font faces and OFL licences |
| Download metadata | `data/raw/metadata/` | Original release context |
| Derived datasets | `data/processed/` | `atlas.json`, London report, colour and logo-permission ledgers |
| Source integrity | `data/provenance/` | Source URLs, retrieval records and hashes |

**Do not put files directly in `data/`: categorise all data into these subfolders.**
Git preserves snapshot bytes through `.gitattributes`, including textual evidence, so Windows line-ending conversion cannot invalidate recorded hashes.

Population joins use exact ONS codes, never names: 316 of 415 authority entries join, including overlapping county/GLA geographies that must not be summed. The RA codes for Barnsley and Sheffield have no exact match in this ONS workbook, so their resident-scale ratios remain unavailable.

Roads join to 153 authority entries. The denominator is **major locally managed road miles + all minor road miles**, using source-rounded miles, not all roads including centrally managed motorways. Only structural maintenance, environmental/routine maintenance and winter service expose this ratio. It is **network-scale context, not an audited maintenance unit cost**: the network and revenue numerator are not matched road-by-road, London responsibilities can overlap TfL, capital works are excluded, and condition/traffic/treatment area differ.

Other preferred service denominators are documented but **not imported**: matched pupil/place counts, care users/hours, assisted households, waste tonnes, planning cases and similar units. Per resident is scale context, **not demand adjustment or efficiency**. Zero, missing, suppressed and not-applicable states remain distinct.

The City of London is available separately but excluded from default borough comparisons. Greenwich did not return an RA budget: the default London group has 31 available observations out of 32 boroughs. County/district and special-authority responsibilities differ. Scotland, Wales and Northern Ireland are linked and explained, **not silently harmonised with England**.

The 13 themes reconcile exactly for every submitted return. National Table 2 corroborates the England theme totals to rounding, but is the same publisher/underlying return, not an independent source. Council reports provide additional primary context; this project does **not** claim three independent confirmations of every cell or full reconciliation of local report headlines.

## Reproduce and update

Python 3.11+ is sufficient for importing and building; the ODS/XLSX readers use only the standard library.

```powershell
python scripts\import_data.py
python scripts\build.py
```

To re-download the **pinned** official files, use `python scripts\import_data.py --download`. This is not an automatic upgrade to a new release: when changing financial year, update URLs, metadata, definitions, report/identity evidence, expected values and coverage checks together. Audit boundary changes before adding a crosswalk. Do not convert missing returns to zero or impute a council from a national estimate.

Edit the editorial source `src/page.html`, shared `src/atlas.css`, `src/atlas.js`, `src/navigation.js`, `src/benchmark.js`, and the generators `scripts/build.py` / `scripts/documents.py`; then regenerate all documents together. The fragment publisher preserves the existing sourced explanations and fallback calculations, writes real relative links and fails on unresolved fragment targets. `data/processed/documents.json` records every generated path, field and document size. **Do not manually edit generated HTML or `assets/`**. All pages use the same canonical data and benchmark implementation; there is no manually copied per-page calculation logic.

Base UI colours use site-derived `--cp-*` variables. Verified council colours are separate `--cp-council-<ONS code>` tokens, displayed as exact-brand swatches/bars beside readable names; unknown identities use a dashed neutral indicator.

The **latest user-directed design source is [redbridgeindys.org](https://redbridgeindys.org/)**, replacing the initial Clawpilot default palette/typefaces while retaining the `--cp-*` token architecture. Actual inline theme values supply navy `#06296D`; homepage heading CSS supplies yellow `#FDD200`, Barlow Condensed weight 800; global CSS declares Century Gothic. Light/dark adaptations retain accessible contrast rather than copying the site’s low-contrast muted text.

Barlow Condensed 400/600/700/800 and Barlow 400/600/700 are embedded under **SIL Open Font License 1.1**, with licences in the repository and generated shared stylesheet. Century Gothic is **not redistributed**: it is used only when locally installed, otherwise the bundled Barlow supplies an offline fallback. Source URLs, hashes, inspected rules and adaptations are in `data/provenance/design.json`. The source site’s complete theme CSS/HTML are not redistributed. To refresh the design/font evidence, run `python scripts\import_design.py --download` before rebuilding.

## Tests

```powershell
npm ci
npm test
```

`npm run test:data` checks all 133,215 imported numeric cells against the raw workbooks, missing states, source hashes, theme and grant-transfer reconciliation, the separate national table, denominator joins/coordinates, units, the worked road example and generated fallback structure.

It also checks all financing reconciliations and Redbridge grant/tax/capitalisation definitions; source-derived font licences/hashes; all report/identity evidence; canonical aliases, incompatible scopes, unmapped local reports and duplicate/subtotal handling. `npm run test:benchmarks` checks median math, focal/City/responsibility exclusions, missing and zero, negative bases, exact per-unit conversion, duplicate peers and unavailable denominators.

The exhaustive arithmetic gate independently recomputes **399,645 authority/field/metric combinations**, all **143 service/theme/total fields × 3 lenses × 4 selection cohorts** (1,716 benchmark combinations), every returned financing share, and all-lens missing states. The document gate checks **all 133 paths**, unique per-page IDs, every relative link/asset/anchor/citation, one-to-one service coverage, all 321 retained fields, every service's default source values and definitions, shared-data identity, and byte-identical offline regeneration. Source extraction is checked separately against the preserved original workbooks. Official source data may still contain errors; this verifies faithful extraction and arithmetic, not official infallibility.

The real-browser chart gate opens **all 129 individual-service files and the accounting appendix**, checks every retained field in absolute and resident lenses plus all three supported road lenses (**645 chart/lens cases / 21,285 selected-authority observations**), and verifies matching table values, benchmark medians, exact Redbridge dark red, zero-width zero bars, negative values, absent returns and released collapsed SVGs. It checks **258 overview-to-service differences** (all 129 services in both lenses) and **429 financing contributions/shares**. Additional missing/suppressed/non-applicable and zero-financing fixtures verify explicit unavailable states, not fabricated numbers.

To repeat the direct-PDF headline release gate, use `python scripts\retrieve_reports.py --verify-headlines`; add `--pdf-reader-path <installed-pypdf-directory>` to re-extract the original PDF pages rather than validating their preserved literal extraction. Normal builds/tests require no extra Python packages.

`npm run test:browser` uses actual **file://** documents in headless Microsoft Edge: offline/no-JS behaviour, one/multiple/All London selections, empty-state reload, new-tab links, previous/next, citations, funding navigation, browser back/forward, synchronized funding/service/benchmark changes, filter/order/detail consistency, financing signs/shares, identities, permission fallbacks, licensed fonts, mobile keyboard/touch, negative/zero/missing values, restricted denominators, directory, raw CSV, scroll story, progress/back-to-top, reduced motion and theme switching. Axe WCAG 2.2 A/AA audits cover every document type, open charts, light/dark and mobile. No application HTTP requests are permitted.

The default browser is installed Edge. For a system with Playwright Chromium instead:

```powershell
npx playwright install chromium
$env:ATLAS_BROWSER = "chromium"
npm run test:browser
```

These automated checks and visual inspection are evidence, not a claim of universal accessibility or independent fiscal audit. Council reports and identity sources have their own provenance checks in `tests/`.

**Split-document release validation:** `npm test` passed **84 tests: 47 Python source/document/provenance tests, 18 arithmetic/URL-state tests and 19 real-browser tests**, with no failures or skips. Coverage includes all 133 generated HTML files and **8,798 relative link/asset/anchor references**, 645 chart/lens cases, 21,285 selected-authority observations, 258 overview/detail differences and 429 funding contributions/shares. **Seven axe audits reported zero WCAG 2.2 A/AA violations**, covering every document type, both themes, mobile and open charts. Explicit contrast checks protect breadcrumbs/previous-next links; non-reduced-motion checks ensure long service documents cannot remain hidden by a whole-section reveal threshold. Desktop/mobile outputs were visually inspected. The preserved direct-PDF audit remains **23 supported headlines and one wrong-year claim withheld, all 24 checked**. These results apply to the pinned snapshot, not automatically to later source revisions.


## Attribution

Official data remain attributed to MHCLG, ONS, DfT and the linked councils in the numbered source notes. Government data are supplied under the applicable Open Government Licence; council documents and identity assets retain their owners’ rights and do not imply endorsement. No book text is reproduced. Visualisation influences are Edward Tufte’s *The Visual Display of Quantitative Information* and *Beautiful Evidence*, and **Stephen Few’s** *Information Dashboard Design*.
