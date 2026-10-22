# Council budget atlas

An offline editorial investigation of **where Redbridge's 2026–27 planned spending differs from selected peers**, initially Waltham Forest. Open **`index.html` directly in a browser**. No server, build step, externally loaded font, runtime API, analytics or public hosting is required. The repository is private; do not enable GitHub Pages or change its visibility.

## What is included

- All **415 English return authorities** in the MHCLG 11 June 2026 individual-authority release: **317 councils and 98 other authorities**, with **406 submitted returns** and nine explicitly missing.
- All **321 numeric fields** from RA parts 1 and 2 and the specific/special grants return: **129 detailed service lines**, **13 theme totals**, and **179 other accounting, financing, HRA, reserve and grant lines**. Each has a distinct accessible section, source locator and denominator catalogue entry.
- Funding first: own council-tax requirement, explicit central-government grants, retained rates, reserves and every other signed financing line, reconciling exactly to RA 900 for all 406 returns. Shares use that perimeter only. Actual tax receipts, collection rates, tax bases and Band D bills are **not** imported or confused with this budget requirement.
- Accessible multi-council checkboxes, selected-count/removal/clear/reset, and a one-action **All London councils** shortcut selecting all 33 entries, including City and missing Greenwich without duplicating Redbridge. The set follows funding, themes, detailed service/road tables and the scroll story.
- A prioritised, sortable/filterable shortlist of **129 detailed service lines**, with Redbridge's budget, selected-peer budget median, resident-scale/eligible road measure, benchmark difference, percentage where meaningful, valid count/range and linked service details. Redbridge remains the reference. Only selected London boroughs with an available matching measure enter the benchmark: no City, Redbridge itself, other authority class or missing value. One peer is a direct comparison; multiple peers use an unweighted median. Zero/negative benchmarks keep signed differences but do not receive misleading percentage comparisons.
- London-first peer exploration, absolute and resident-scale metrics, a restricted road-network-scale maintenance comparison, CSV export, accessible tables and source citations. Broader England groups remain available for context but do not silently populate selected benchmarks.
- Scroll-driven shared SVG charts, plus a **lazy-rendered comparison chart in every one of the 321 ledger sections**, a reading-progress indicator, section navigation, keyboard/touch alternatives, light/dark themes, reduced-motion support and real initial data without JavaScript. Each ledger plot preserves negative/zero values, selected names/colours and a valid-peer benchmark where supported; its toggle exposes absolute/resident scale and the three eligible road-network ratios with matching complete tables.
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

Edit `src/page.html`, `src/atlas.css`, `src/atlas.js`, `src/benchmark.js` and `scripts/build.py`, then rebuild `index.html`. Do not manually edit the generated HTML. Base UI colours use site-derived `--cp-*` variables. Verified council colours are separate `--cp-council-<ONS code>` tokens, displayed as exact-brand swatches/bars beside readable names; unknown identities use a dashed neutral indicator.

The **latest user-directed design source is [redbridgeindys.org](https://redbridgeindys.org/)**, replacing the initial Clawpilot default palette/typefaces while retaining the `--cp-*` token architecture. Actual inline theme values supply navy `#06296D`; homepage heading CSS supplies yellow `#FDD200`, Barlow Condensed weight 800; global CSS declares Century Gothic. Light/dark adaptations retain accessible contrast rather than copying the site’s low-contrast muted text.

Barlow Condensed 400/600/700/800 and Barlow 400/600/700 are embedded under **SIL Open Font License 1.1**, with licences in the repository and generated HTML. Century Gothic is **not redistributed**: it is used only when locally installed, otherwise the bundled Barlow supplies an offline fallback. Source URLs, hashes, inspected rules and adaptations are in `data/provenance/design.json`. The source site’s complete theme CSS/HTML are not redistributed. To refresh the design/font evidence, run `python scripts\import_design.py --download` before rebuilding.

## Tests

```powershell
npm ci
npm test
```

`npm run test:data` checks all 133,215 imported numeric cells against the raw workbooks, missing states, source hashes, theme and grant-transfer reconciliation, the separate national table, denominator joins/coordinates, units, the worked road example and generated fallback structure.

It also checks all financing reconciliations and Redbridge grant/tax/capitalisation definitions; source-derived font licences/hashes; all report/identity evidence; canonical aliases, incompatible scopes, unmapped local reports and duplicate/subtotal handling. `npm run test:benchmarks` checks median math, focal/City/responsibility exclusions, missing and zero, negative bases, exact per-unit conversion, duplicate peers and unavailable denominators.

The exhaustive arithmetic gate independently recomputes **399,645 authority/field/metric combinations**, all **143 service/theme/total fields × 3 lenses × 4 selection cohorts** (1,716 benchmark combinations), every returned financing share, and all-lens missing states. The real-browser exhaustive check compares **10,593 displayed All London service cells**, **429 financing contributions/shares** and **129 summary/detail differences**, plus raw road-ratio/absent-return CSV output, against the embedded source data. Source extraction itself is checked separately against the preserved original workbooks. Official source data may still contain errors; this verifies faithful extraction and arithmetic, not official infallibility.

The ledger-chart coverage gate opens **every one of the 321 sections**, checks both absolute and resident lenses plus all three supported road lenses (**645 charts / 21,285 selected-authority observations**), verifies matching table values, benchmark medians, exact Redbridge dark red, zero-width zero bars, negative values and absent returns, then confirms collapsed SVGs are released. Additional mobile and missing/suppressed/non-applicable fixture checks cover keyboard lens changes, selection updates and explicit unavailable states. Open ledger charts are included in the axe audit, not only the collapsed page.

To repeat the direct-PDF headline release gate, use `python scripts\retrieve_reports.py --verify-headlines`; add `--pdf-reader-path <installed-pypdf-directory>` to re-extract the original PDF pages rather than validating their preserved literal extraction. Normal builds/tests require no extra Python packages.

`npm run test:browser` opens the actual **file://** page in headless Microsoft Edge: offline/no-JS behaviour, one/multiple/All London selections, deselection/reset, synchronized funding/service/benchmark changes, filter/order/detail consistency, financing signs/shares, exact identity tokens, permission fallbacks, licensed fonts, mobile keyboard/touch, negative/zero/missing values, restricted denominators, catalogue, CSV export, sticky story, anchors/progress/back-to-top, reduced motion, theme switching and axe WCAG 2.2 AA checks in both themes and mobile. It makes no application network requests.

The default browser is installed Edge. For a system with Playwright Chromium instead:

```powershell
npx playwright install chromium
$env:ATLAS_BROWSER = "chromium"
npm run test:browser
```

These automated checks and visual inspection are evidence, not a claim of universal accessibility or independent fiscal audit. Council reports and identity sources have their own provenance checks in `tests/`.

**Release validation:** 41 Python source/provenance/mapping tests, 13 arithmetic/benchmark tests and 16 real-browser tests passed (**70 total**). Axe reported no WCAG 2.2 A/AA violations in the tested desktop light/dark and mobile views, including opened ledger charts. Desktop/mobile previews were visually inspected. The separate original-PDF headline gate reported **23 verified, one wrong-year claim withheld, all 24 checked**. These results apply to the pinned snapshot, not automatically to later source revisions.

## Attribution

Official data remain attributed to MHCLG, ONS, DfT and the linked councils in the numbered source notes. Government data are supplied under the applicable Open Government Licence; council documents and identity assets retain their owners’ rights and do not imply endorsement. No book text is reproduced. Visualisation influences are Edward Tufte’s *The Visual Display of Quantitative Information* and *Beautiful Evidence*, and **Stephen Few’s** *Information Dashboard Design*.
