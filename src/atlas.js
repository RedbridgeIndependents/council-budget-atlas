(() => {
  "use strict";
  const data = window.atlasData;
  const authorities = new Map(data.authorities.map(a => [a.code, a]));
  const fields = new Map(data.fields.map(f => [f.id, f]));
  const $ = id => document.getElementById(id);
  const navigation = window.AtlasNavigation;
  const initial = navigation.parse(location.search,data.authorities,data.fields);
  const state = { focus: initial.focus, comparisons: new Set(initial.peers), peer: initial.group, field: initial.field, metric: initial.metric, story: initial.story };
  const londonComparisons=data.authorities.filter(a=>a.class==="LB" && a.code!==state.focus).map(a=>a.code);
  let previousComparisonCount=null;
  const selectedCodes = () => [state.focus, ...state.comparisons].filter((code, index, all) => all.indexOf(code) === index);
  const selectedAuthorities = () => selectedCodes().map(code => authorities.get(code));
  const nf = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
  const decimal = new Intl.NumberFormat("en-GB", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const benchmarkState = { metric: initial.metric, filter: initial.filter, sort: initial.sort };
  const stats = window.BudgetBenchmarks;
  const root = document.body.dataset.root;
  function query() {
    return navigation.serialize({...state,filter:benchmarkState.filter,sort:benchmarkState.sort,theme:document.documentElement.dataset.theme});
  }
  function syncLinks(scope=document) {
    const currentQuery=query();
    scope.querySelectorAll("a[href]").forEach(link=>{
      let base=link.dataset.documentHref || link.getAttribute("href");
      if (base.startsWith("#") && !$(base.slice(1))) {
        const identifier=base.slice(1);
        if (identifier.startsWith("line-")) base=root+data.documents.fields[identifier.slice(5)];
        else if (identifier.startsWith("source-")) base=root+"methodology.html"+base;
        else if (identifier==="funding") base=root+"funding.html#funding";
        else throw new Error(`Unresolved generated document link: ${identifier}`);
      }
      const target=new URL(base,location.href);
      const local=target.protocol==="file:" || target.origin===location.origin && /^https?:$/.test(target.protocol);
      if (!local || !target.pathname.endsWith(".html") || link.hasAttribute("download")) return;
      link.dataset.documentHref=base;
      link.setAttribute("href",navigation.href(base,currentQuery));
    });
  }
  function updateContext() {
    const url=new URL(location.href);
    url.search=query();
    if (url.href!==location.href) history.replaceState(null,"",url.href);
    syncLinks();
  }
  function updateThemeButton() {
    const action=document.documentElement.dataset.theme==="dark" ? "Use light theme" : "Use dark theme";
    $("theme-toggle").setAttribute("aria-label",action);
    $("theme-toggle").title=action;
  }
  function setControls() {
    updateThemeButton();
    $("shared-metric").value=state.metric;
    if ($("peer-group")) $("peer-group").value=state.peer;
    if ($("budget-line")) $("budget-line").value=state.field;
    for (const key of ["filter","sort"]) if ($("benchmark-"+key)) $("benchmark-"+key).value=benchmarkState[key];
    document.querySelectorAll("[data-current-metric]").forEach(el=>{ el.textContent=$("shared-metric").selectedOptions[0].textContent; });
    const explanations={
      resident:"ONS mid-2025 population scale, not service-user cost or need adjustment.",
      absolute:"Published amounts in £m. No adjustment for council size or need.",
      roads:"DfT 2025 network miles; eligible maintenance lines only, not audited unit cost."
    };
    const current=fields.get(document.body.dataset.serviceId);
    $("shared-metric-help").textContent=(current && state.metric==="roads" && current.denominator.key!=="roads" ? "Unavailable for this service. " : "")+explanations[state.metric]+" Shared with the service chart controls.";
  }
  function setMetric(metric) {
    state.metric=metric; benchmarkState.metric=metric;
    ledgerMetrics.clear(); setControls();
    updateExplorer(); updateBenchmarks(); refreshOpenLedgers(); updateContext();
  }
  document.documentElement.dataset.theme=initial.theme || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  if (initial.issues.length) {
    $("navigation-notice").hidden=false;
    $("navigation-notice").textContent=initial.issues.join(" ");
  }
  const escape = text => String(text).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const isNumber = n => typeof n === "number" && Number.isFinite(n);
  const monetary = n => isNumber(n) ? `${n < 0 ? "−" : ""}£${decimal.format(Math.abs(n) / 1000)}m` : "Not available";
  const pounds = n => isNumber(n) ? `${n < 0 ? "−" : ""}£${nf.format(Math.abs(n))}` : "Not available";
  const cite = (n, title = "") => `<a class="citation" href="#source-${n}" aria-label="Source ${n}"${title ? ` title="${escape(title)}"` : ""}>[${n}]</a>`;
  const cssIdentity = code => `--cp-council:var(--cp-council-${code},var(--cp-border))`;
  const identity = code => {
    const a = authorities.get(code);
    const colour = data.colours[code];
    const known = colour && colour.colour;
    return `<span class="council${known ? "" : " unknown"}" data-council="${code}" data-logo-state="${data.logos[code]?.permission || "not-researched"}" style="${cssIdentity(code)}" title="${known ? `Official identity colour: ${escape(colour.colour)}` : "Official identity colour not yet verified"}">${escape(a.name)}</span>`;
  };
  function columnName(n) {
    let text = "";
    while (n) { n--; text = String.fromCharCode(65 + n % 26) + text; n = Math.floor(n / 26); }
    return text;
  }
  const locator = (a, f) => `${f.sheet}!${columnName(f.column)}${a.rows[f.part]} · line ${f.line} · ${f.asset}`;
  const raw = (a, f) => a.values[f.id];
  const sourceValue = (a, f) => `${monetary(raw(a, f))}${cite(f.source, locator(a, f))}`;
  function returnFlags(a) {
    if (!a.notes || a.notes === "M") return "";
    const explanations = [...a.notes.matchAll(/\[note \d+\]/g)].map(match => data.notes.ra1[match[0]]).filter(Boolean);
    return explanations.length ? `<span class="return-flags"> Source flag for ${identity(a.code)}: ${explanations.map(escape).join(" ")}${cite(1)}</span>` : "";
  }
  function unavailable(a, f, metric) {
    const status = a.statuses[f.id];
    if (status) return ({ "not-returned": "Not returned [x]", "not-applicable": "Not applicable", suppressed: "Suppressed", missing: "Missing" }[status] || "Not numeric");
    if (metric === "resident" && !a.population) return "Population not joined";
    if (metric === "roads" && f.denominator.key !== "roads") return "Not an eligible road-maintenance line";
    if (metric === "roads" && (!a.roads || a.roads.value <= 0)) return "Road network not joined / zero";
    return "Not available";
  }
  function metricValue(a, f, metric = state.metric) {
    return stats.value(a,f,metric);
  }
  const formatMetric = (n, metric = state.metric) => !isNumber(n) ? "Not available" : metric === "absolute" ? `${n < 0 ? "−" : ""}£${decimal.format(Math.abs(n))}m` : pounds(n);
  const unit = metric => metric === "absolute" ? "£m" : metric === "resident" ? "£ per resident (mid-2025)" : "£ per local network mile (2025)";
  function peerAuthorities() {
    const focus = authorities.get(state.focus);
    return data.authorities.filter(a => {
      if (state.peer === "london") return a.class === "LB" && a.code !== "E09000001";
      if (state.peer === "single") return ["UA", "MD", "LB"].includes(a.class) && a.code !== "E09000001";
      if (state.peer === "same") return a.class === focus.class && (focus.class !== "O" || a.subclass === focus.subclass) && (a.code !== "E09000001" || state.focus === "E09000001");
      if (state.peer === "councils") return a.class !== "O";
      return true;
    });
  }
  function pairTable(ids, metric = "absolute", caption = "2026–27 budget") {
    const pair = selectedAuthorities();
    if (pair.length > 3) {
      return `<table><caption>${escape(caption)} · ${escape(unit(metric))} · all ${pair.length} selected authorities</caption><thead><tr><th scope="col">Authority</th>${ids.map(id => `<th scope="col">${escape(shortLabels[id] || fields.get(id).label)}</th>`).join("")}</tr></thead><tbody>${pair.map(a => `<tr${a.code === state.focus ? ' class="selected"' : ""}><th scope="row">${identity(a.code)}</th>${ids.map(id => {
        const f = fields.get(id);
        return `<td class="num">${formatMetric(metricValue(a,f,metric),metric)}${cite(f.source,locator(a,f))}${metric === "resident" ? cite(8) : ""}</td>`;
      }).join("")}</tr>`).join("")}</tbody></table>`;
    }
    return `<table><caption>${escape(caption)} · ${escape(unit(metric))}</caption><thead><tr><th scope="col">Published line</th>${pair.map(a => `<th scope="col">${identity(a.code)}</th>`).join("")}</tr></thead><tbody>${ids.map(id => {
      const f = fields.get(id);
      return `<tr><th scope="row">${escape(f.label)}</th>${pair.map(x => `<td class="num">${formatMetric(metricValue(x, f, metric), metric)}${cite(f.source, locator(x, f))}${metric === "resident" ? cite(8) : ""}</td>`).join("")}</tr>`;
    }).join("")}</tbody></table>`;
  }
  function updateComposition() {
    if (!$("theme-bars")) return;
    const a = authorities.get(state.focus);
    const ids = data.meta.themeIds;
    const lo = Math.min(0, ...ids.map(id => a.values[id] || 0));
    const hi = Math.max(1, ...ids.map(id => a.values[id] || 0));
    const range = hi - lo;
    $("theme-bars").innerHTML = ids.map((id, i) => {
      const f = fields.get(id), value = raw(a, f);
      return `<div class="theme-row"><a href="#line-${id}">${escape(data.meta.themeNames[i])}</a><div class="track" style="--zero:${-lo/range*100}%" aria-hidden="true"><span class="fill" style="--bar:${isNumber(value) ? Math.abs(value) / range * 100 : 0}%;left:${(Math.min(0,value || 0)-lo)/range*100}%;${cssIdentity(a.code)};background:var(--cp-council,var(--cp-accent))"></span></div><span class="value">${sourceValue(a, f)}</span></div>`;
    }).join("");
    $("themes-caption").innerHTML = `${identity(a.code)} · 2026–27 budget · £m. All 13 published theme totals, counted once, on a common scale with an explicit zero. ${a.returned ? "They reconcile exactly to RA line 799." : "No return: absent bars are not zero budgets."}${cite(1)} Negative totals extend left of zero and represent net income.`;
    $("theme-table").innerHTML = pairTable(ids, "absolute", "All 13 service themes · 2026–27 budget");
  }
  function benchmark(f,metric=benchmarkState.metric) {
    return stats.compare(authorities.get("E09000026"),selectedAuthorities(),f,metric);
  }
  function benchmarkParagraph(f,metric=benchmarkState.metric) {
    const b=benchmark(f,metric);
    if (!b.service) return "Not benchmarked as service spending: financing, reserve balances and accounting adjustments answer different questions.";
    if (!b.count || !isNumber(b.own)) return `Insufficient comparison data for ${escape(unit(metric))}. ${b.count} valid selected borough peers; ${b.excludedResponsibility} excluded for responsibility class; ${b.missing} missing measures. No value or denominator is imputed.${cite(f.source)}`;
    const percent=isNumber(b.percent) ? `${b.percent>=0 ? "+" : "−"}${Math.abs(b.percent).toFixed(1)}%` : "percentage not reported: benchmark is zero or net income";
    return `${identity("E09000026")}: ${sourceValue(authorities.get("E09000026"),f)}; ${formatMetric(b.own,metric)} versus ${b.count===1 ? "direct peer" : "selected-peer median"} ${formatMetric(b.benchmark,metric)}. <strong>Difference: ${formatMetric(b.delta,metric)} (${percent})</strong>. ${b.count} valid peers; range ${formatMetric(b.min,metric)} to ${formatMetric(b.max,metric)}.${cite(f.source)}${metric==="resident" ? cite(8) : metric==="roads" ? cite(7) : ""} <strong>Investigate, not a verdict.</strong> ${metric==="resident" ? "Residents are scale, not service users or need." : metric==="roads" ? "Network miles are a scope/condition-sensitive proxy, not an audited unit cost." : "Absolute differences do not adjust council size."} Matched need/outcomes are not imported; <a href="#funding">funding constraints</a> are not demand adjustment.`;
  }
  function benchmarkTable(items) {
    const metric=benchmarkState.metric;
    return `<table><caption>2026–27 planned spending differences · ${escape(unit(metric))} · same selected-peer benchmark as each detailed section</caption><thead><tr><th scope="col">Published service</th><th scope="col">${identity("E09000026")} budget £m</th><th scope="col">Valid peers’ median budget £m (size unadjusted)</th><th scope="col">Redbridge · ${escape(unit(metric))}</th><th scope="col">Selected-peer benchmark · ${escape(unit(metric))}</th><th scope="col">Redbridge minus benchmark</th><th scope="col">Difference %</th><th scope="col">Valid peers / distribution</th><th scope="col">Evidence and next check</th></tr></thead><tbody>${items.map(({f,b})=>{
      const percent=isNumber(b.percent) ? `${b.percent>0 ? "+" : ""}${b.percent.toFixed(1)}%` : "Not reported: zero, net-income or missing base";
      return `<tr data-benchmark-row="${f.id}"><th scope="row"><a href="#line-${f.id}">${escape(f.label)}</a></th><td class="num">${sourceValue(authorities.get("E09000026"),f)}</td><td class="num">${formatMetric(b.budgetMedian,"absolute")}${cite(f.source)}</td><td class="num">${formatMetric(b.own,metric)}</td><td class="num">${formatMetric(b.benchmark,metric)}${cite(f.source)}${metric==="resident" ? cite(8) : metric==="roads" ? cite(7) : ""}</td><td class="num" data-difference="${isNumber(b.delta) ? b.delta : ""}">${formatMetric(b.delta,metric)}</td><td>${percent}</td><td>${b.count} valid / ${b.selectedCount} selected. ${b.count===1 ? "Direct comparison" : "Unweighted median"}. Range ${formatMetric(b.min,metric)} to ${formatMetric(b.max,metric)}.</td><td>${isNumber(b.delta) ? "Investigate" : "Insufficient data"}. Preferred unit: ${escape(f.denominator.preferred)}; ${escape(f.denominator.availability)}. Need, quality and outcomes not matched; net income, responsibilities and funding need checking.</td></tr>`;
    }).join("")}</tbody></table>`;
  }
  function updateBenchmarks() {
    if (!$("benchmark-table")) return;
    let items=data.fields.filter(f=>f.kind==="service").map(f=>({f,b:benchmark(f)}));
    const filter=benchmarkState.filter;
    items=items.filter(({b})=>filter==="above" ? b.delta>0 : filter==="below" ? b.delta<0 : filter==="available" ? isNumber(b.delta) : filter==="missing" ? !isNumber(b.delta) : true);
    items.sort((a,b)=>{
      if (benchmarkState.sort==="name") return a.f.label.localeCompare(b.f.label);
      if (isNumber(a.b.delta)!==isNumber(b.b.delta)) return isNumber(a.b.delta) ? -1 : 1;
      const x=a.b.delta ?? 0, y=b.b.delta ?? 0;
      return benchmarkState.sort==="above" ? y-x : benchmarkState.sort==="below" ? x-y : Math.abs(y)-Math.abs(x);
    });
    const example=benchmark(fields.get("ra1_servicetot"));
    $("benchmark-method").innerHTML=`${identity("E09000026")} is the persistent reference. ${selectedCodes().length-1} comparison authorities selected; this lens is ${escape(unit(benchmarkState.metric))}. Only selected London borough peers are eligible: ${example.excludedResponsibility} selected authorities excluded for unlike responsibilities; missing measures are filtered line by line. ${items.length} of 129 detailed service lines shown. <a href="#comparison-controls">Change selected councils</a>.`;
    $("benchmark-table").innerHTML=benchmarkTable(items);
    const top=items.filter(item=>isNumber(item.b.delta)).slice(0,3);
    $("headline-benchmarks").innerHTML=top.length ? `<div class="stat-grid">${top.map(({f,b})=>`<div class="stat"><span><a href="#line-${f.id}">${escape(f.label)}</a></span><strong>${formatMetric(b.delta,benchmarkState.metric)}</strong><span>${b.delta>0 ? "Above" : b.delta<0 ? "Below" : "At"} selected-peer benchmark · ${b.count} valid peers · investigate, not a verdict${cite(f.source)}</span></div>`).join("")}</div>` : '<p class="note">No valid differences in this selection and lens. Select comparable councils or use an eligible metric; no benchmark is invented.</p>';
    $("total-benchmark").innerHTML=`<p class="note">${benchmarkParagraph(fields.get("ra1_servicetot"))}</p>`;
    $("theme-benchmarks").innerHTML=benchmarkTable(data.meta.themeIds.map(id=>({f:fields.get(id),b:benchmark(fields.get(id))})));
    document.querySelectorAll("[data-benchmark]").forEach(el=>{
      const f=fields.get(el.dataset.benchmark);
      el.innerHTML=benchmarkParagraph(f);
      if (f.denominator.key==="roads" && benchmarkState.metric!=="roads") el.innerHTML+=`<br><strong>Matched network-scale lens:</strong> ${benchmarkParagraph(f,"roads")}`;
    });
    $("explorer-benchmark").innerHTML=`<p class="note">${benchmarkParagraph(fields.get(state.field),state.metric)}</p>`;
  }

  const storySets = [
    ["ra1_edutot", "ra1_asctot", "ra1_csctot", "ra1_housgfcftot", "ra1_phtot", "ra1_envtot", "ra1_transtot", "ra1_cultot"],
    ["ra1_eduerl", "ra1_eduprm", "ra1_eduscn", "ra1_eduspc", "ra1_edupst", "ra1_eduoth"],
    ["ra1_edutot", "ra1_asctot", "ra1_csctot", "ra1_housgfcftot", "ra1_phtot", "ra1_envtot", "ra1_transtot", "ra1_cultot"],
    ["ra1_transrdsmnt", "ra1_transrdsenv", "ra1_transrdswnt", "ra1_transrdslgh", "ra1_transprk", "ra1_transpblstt"]
  ];
  const shortLabels = {
    ra1_edutot: "Education", ra1_asctot: "Adult social care", ra1_csctot: "Children & families",
    ra1_housgfcftot: "Housing (General Fund)", ra1_phtot: "Public health", ra1_envtot: "Environment & waste",
    ra1_transtot: "Roads & transport", ra1_cultot: "Culture & leisure",
    ra1_eduerl: "Early years", ra1_eduprm: "Primary schools", ra1_eduscn: "Secondary schools",
    ra1_eduspc: "Special / alternative provision", ra1_edupst: "Post-16", ra1_eduoth: "Other education",
    ra1_transrdsmnt: "Structural maintenance", ra1_transrdsenv: "Routine / environmental", ra1_transrdswnt: "Winter service",
    ra1_transrdslgh: "Street lighting", ra1_transprk: "Parking (net)", ra1_transpblstt: "Statutory concessionary fares"
  };
  function svgFrame(content, height, title, description) {
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 ${height}" role="img" aria-label="${escape(title)}"><title>${escape(title)}</title><desc>${escape(description)}</desc>${content}</svg>`;
  }
  function councilRowsChart(rows, metric, title, comparison=null) {
    const values = rows.map(row => row.n).filter(isNumber);
    const lo = Math.min(0,...values), upper = Math.max(0,...values), hi = upper===lo ? lo+1 : upper;
    const x = n => 220 + (n-lo)/(hi-lo)*275;
    let content = "";
    for (let i=0; i<=3; i++) {
      const n = lo+(hi-lo)*i/3;
      content += `<line class="chart-grid" x1="${x(n)}" x2="${x(n)}" y1="28" y2="${rows.length*36+25}"/><text class="chart-axis" x="${x(n)}" y="15" text-anchor="middle">${nf.format(n)}</text>`;
    }
    content += `<line x1="${x(0)}" x2="${x(0)}" y1="28" y2="${rows.length*36+25}" style="stroke:var(--cp-text-soft);stroke-width:1.5"/>`;
    if (comparison && isNumber(comparison.benchmark)) content+=`<line data-benchmark-value="${comparison.benchmark}" x1="${x(comparison.benchmark)}" x2="${x(comparison.benchmark)}" y1="28" y2="${rows.length*36+25}" style="stroke:var(--cp-text);stroke-width:1.5;stroke-dasharray:5 4"><title>Valid selected-peer benchmark: ${escape(formatMetric(comparison.benchmark,metric))}; ${comparison.count} peers</title></line>`;
    rows.forEach(({a,n},i) => {
      const y=i*36+43, label=a.name.length>29 ? a.name.slice(0,26)+"…" : a.name;
      content += `<g class="chart-pair" data-chart-authority="${a.code}" data-chart-value="${isNumber(n) ? n : ""}" tabindex="0" role="img" aria-label="${escape(a.name+": "+formatMetric(n,metric))}"><title>${escape(a.name+": "+formatMetric(n,metric))}</title><rect x="2" y="${y-8}" width="8" height="8" style="${cssIdentity(a.code)};fill:var(--cp-council,var(--cp-border));stroke:var(--cp-text-soft)"/><text class="chart-label" x="16" y="${y}">${escape(label)}</text>`;
      if (isNumber(n)) content += `<rect class="${a.code===state.focus ? "chart-bar" : "chart-comparison"}" data-council="${a.code}" style="${cssIdentity(a.code)}" x="${Math.min(x(n),x(0))}" y="${y-11}" width="${Math.abs(x(n)-x(0))}" height="16"/>`;
      content += `<text class="chart-value" x="617" y="${y+1}" text-anchor="end">${escape(formatMetric(n,metric))}</text></g>`;
    });
    return svgFrame(content,rows.length*36+35,title,"All selected authorities, including missing values. Each has its own named row on a common zero-based axis; focus is solid and comparisons outlined. " +(comparison?.count ? `Dashed vertical line: valid selected-peer benchmark ${formatMetric(comparison.benchmark,metric)}, ${comparison.count} peers.` : "No supported peer benchmark line."));
  }
  const ledgerMetrics=new Map();
  function renderLedger(section) {
    const f=fields.get(section.id.slice(5)), selector=section.querySelector("[data-ledger-metric]");
    if (!ledgerMetrics.has(f.id)) ledgerMetrics.set(f.id,state.metric);
    const metric=ledgerMetrics.get(f.id); selector.value=metric;
    const pair=selectedAuthorities(), b=benchmark(f,metric);
    const rows=pair.map(a=>({a,n:metricValue(a,f,metric)})).sort((x,y)=>{
      if (x.a.code===state.focus) return -1;
      if (y.a.code===state.focus) return 1;
      if (isNumber(x.n)!==isNumber(y.n)) return isNumber(x.n) ? -1 : 1;
      return (y.n ?? 0)-(x.n ?? 0);
    });
    const container=section.querySelector("[data-ledger-chart]");
    container.innerHTML=rows.some(row=>isNumber(row.n)) ? councilRowsChart(rows,metric,`${f.label} · 2026–27 return · ${unit(metric)}`,b) : '<p class="note" data-chart-unavailable>No valid numerical data for this measure. Missing/suppressed/non-applicable amounts and absent denominators are not zero bars.</p>';
    container.dataset.rendered="true";
    const basis=f.kind==="service" || f.kind==="theme" || f.id==="ra1_servicetot" ? "Planned net service spending" : "Published accounting / financing / reserve / HRA line: preserve its reported sign and date; not a service-spending or efficiency measure";
    const serviceUnit=f.denominator.key==="roads" ? `A verified road-network denominator is available where joined: use the network-mile option. It remains a maintenance-scale proxy, not an audited unit cost.${cite(7)}` : f.kind==="service" ? `Preferred service unit: ${escape(f.denominator.preferred)}. No verified matching service-unit denominator is imported; resident scale is not unit cost.${cite(f.denominator.source)}` : "No service-output denominator is applicable to this accounting total or line.";
    section.querySelector("[data-ledger-caption]").innerHTML=`${escape(basis)} · 2026–27 budget return · ${escape(unit(metric))}. Redbridge first; comparisons descending, missing values last. Solid focus / outlined comparisons; dashed vertical line ${b.count ? `= ${b.count===1 ? "direct peer" : "median of valid selected peers"} ${formatMetric(b.benchmark,metric)} (${b.count} peers)` : "not available: no supported service benchmark"}. All selected authorities stay visible, but non-borough responsibilities and missing measures do not enter the benchmark.${cite(f.source)}${metric==="resident" ? cite(8) : metric==="roads" ? cite(7) : ""} ${serviceUnit} Hover, tap or focus a named row for values; the complete table follows. Differences identify questions, not waste or underprovision.`;
    section.querySelector("[data-benchmark]").innerHTML=`<strong>Chart lens:</strong> ${benchmarkParagraph(f,metric)}`;
    section.querySelector("[data-benchmark]").dataset.benchmarkDelta=isNumber(b.delta) ? String(b.delta) : "";
    section.querySelector("[data-benchmark]").dataset.benchmarkPeers=String(b.count);
    section.querySelector("table").innerHTML=`<caption>All ${pair.length} selected authorities · 2026–27 return · ${escape(unit(metric))}</caption><thead><tr><th scope="col">Authority</th><th scope="col">Published amount (£m)</th><th scope="col">Chart denominator</th><th scope="col">Chart value · ${escape(unit(metric))}</th></tr></thead><tbody>${pair.map(a=>{
      const den=metric==="resident" ? (a.population ? `${nf.format(a.population.value)} people · mid-2025` : "Population not joined") : metric==="roads" ? (f.denominator.key!=="roads" ? "No eligible denominator for this line" : a.roads ? `${a.roads.major} + ${a.roads.minor} = ${nf.format(a.roads.value)} miles · 2025` : "Road network not joined") : "Not used";
      const n=metricValue(a,f,metric);
      return `<tr${a.code===state.focus ? ' class="selected"' : ""}><th scope="row">${identity(a.code)}</th><td class="num">${sourceValue(a,f)}</td><td>${escape(den)}${metric==="resident" ? cite(8) : metric==="roads" ? cite(7) : ""}</td><td class="num">${isNumber(n) ? formatMetric(n,metric) : escape(unavailable(a,f,metric))}</td></tr>`;
    }).join("")}</tbody>`;
    syncLinks(section);
  }
  function refreshOpenLedgers() {
    document.querySelectorAll(".service > details[open]").forEach(details=>renderLedger(details.parentElement));
  }
  function clearLedgerChart(section) {
    const chart=section.querySelector("[data-ledger-chart]");
    chart.dataset.rendered="false";
    chart.innerHTML="<p>Chart renders when this section opens. The source-linked table remains available below.</p>";
  }
  const contribution = (a,item) => isNumber(a.values[item.id]) ? a.values[item.id]*item.sign : null;
  const sumContributions = (a,ids) => ids.every(id => isNumber(a.values[id])) ? -ids.reduce((sum,id) => sum+a.values[id],0) : null;
  const government = a => sumContributions(a,["ra1_grantinaef","ra1_grantrsg","ra1_grantpol"]);
  const reserves = a => sumContributions(a,["ra1_appressch","ra1_appresdsg","ra1_appresph","ra1_appresoth","ra1_appresunall"]);
  const percentage = (n,total) => isNumber(n) && isNumber(total) && total !== 0 ? `${(n/total*100).toFixed(1)}%` : "Not available";
  const perResident = (n,a) => isNumber(n) && a.population && a.population.value>0 ? pounds(n*1000/a.population.value) : "Not available";
  function updateFunding() {
    if (!$("funding-table")) return;
    const pair=selectedAuthorities(), focus=pair[0], total=focus.values.ra1_revenuetot;
    const cards=[["Own council-tax requirement",focus.values.ra1_ctrtot],["Explicit central-government grants",government(focus)],["Reconciling revenue expenditure",total]];
    $("funding-cards").innerHTML=`<div class="stat-grid">${cards.map(([label,n])=>`<div class="stat"><span>${escape(label)} · ${identity(focus.code)}</span><strong>${monetary(n)}${cite(1)}</strong><span>${perResident(n,focus)} per resident · ${percentage(n,total)} of RA 900${cite(8)}</span></div>`).join("")}</div><p class="small">Of the specific grants inside AEF, Dedicated Schools Grant is ${sourceValue(focus,fields.get("sg_grantindsg"))}. It is already included in government grants above; it is not additional funding to add again.</p>`;
    const tables=pair.map(a=>{
      const rev=a.values.ra1_revenuetot;
      const rows=data.meta.fundingLines.map(item=>{
        const n=contribution(a,item), f=fields.get(item.id);
        return `<tr data-funding-line="${f.id}"><th scope="row">${escape(item.label)} · RA ${escape(f.line)}</th><td class="num">${monetary(n)}${cite(1,locator(a,f))}</td><td class="num">${perResident(n,a)}${cite(8)}</td><td class="num">${percentage(n,rev)}</td></tr>`;
      }).join("");
      const available=data.meta.fundingLines.every(item=>isNumber(contribution(a,item)));
      const reconciling=available ? data.meta.fundingLines.reduce((sum,item)=>sum+contribution(a,item),0) : null;
      return `<details data-funding-authority="${a.code}"${pair.length<=3 || a.code===state.focus ? " open" : ""}><summary>${identity(a.code)} · revenue expenditure ${monetary(rev)}</summary><div class="table-scroll" tabindex="0" aria-label="${escape(a.name)} funding reconciliation"><table><caption>Complete financing · 2026–27 budget · signed contributions; shares of RA 900</caption><thead><tr><th scope="col">Financing line</th><th scope="col">Contribution (£m)</th><th scope="col">£ / resident (mid-2025)</th><th scope="col">Share of RA 900</th></tr></thead><tbody>${rows}<tr><th scope="row">Reconciling revenue expenditure · RA 900</th><td class="num">${sourceValue(a,fields.get("ra1_revenuetot"))}</td><td class="num">${perResident(rev,a)}${cite(8)}</td><td class="num">${percentage(rev,rev)}</td></tr><tr><th scope="row">Reconciliation difference (contributions − RA 900)</th><td class="num">${isNumber(reconciling) ? monetary(reconciling-rev) : "Not available"}</td><td colspan="2">${available ? "Zero in the published return; no residual is assigned to government." : "Missing return: no amounts, percentages or residuals are imputed."}</td></tr></tbody></table></div></details>`;
    }).join("");
    $("funding-table").innerHTML=tables;
    $("funding-chart").innerHTML=`<h4>Own council-tax requirement · £m</h4>${councilRowsChart(pair.map(a=>({a,n:isNumber(a.values.ra1_ctrtot) ? a.values.ra1_ctrtot/1000 : null})),"absolute","Own council-tax requirement")}<h4>Explicit central-government grants · £m</h4>${councilRowsChart(pair.map(a=>({a,n:isNumber(government(a)) ? government(a)/1000 : null})),"absolute","Central-government grants")}`;
    $("funding-caption").innerHTML=`All ${pair.length} selected authorities. Two separate, directly labelled charts: own council-tax requirement and the three explicit central-government grant lines. Each chart has its own common zero-based axis; axes differ between charts. Retained rates, reserves, collection-fund adjustments and other financing are kept in the complete reconciliation, not folded into these amounts.${cite(1)}${cite(3)}`;
    const peers=peerAuthorities(), codes=new Set(peers.map(a=>a.code));
    const rows=[...peers,...pair.filter(a=>!codes.has(a.code))].map(a=>{
      const rates=isNumber(a.values.ra1_retainnndr) ? -a.values.ra1_retainnndr : null;
      return `<tr${a.code===state.focus ? ' class="selected"' : ""}><th scope="row">${identity(a.code)}${codes.has(a.code) ? "" : " †"}</th><td class="num">${sourceValue(a,fields.get("ra1_ctrtot"))}</td><td class="num">${monetary(government(a))}${cite(1)}</td><td class="num">${monetary(rates)}${cite(1)}</td><td class="num">${monetary(reserves(a))}${cite(1)}</td><td class="num">${sourceValue(a,fields.get("ra1_revenuetot"))}</td><td class="num">${perResident(a.values.ra1_revenuetot,a)}${cite(8)}</td></tr>`;
    }).join("");
    $("funding-peer-table").innerHTML=`<table><caption>2026–27 peer-group financing, £m; † selected outside ranking peers. Full selected-authority reconciliation above includes every adjustment.</caption><thead><tr><th scope="col">Authority</th><th scope="col">Own council tax</th><th scope="col">Government grants</th><th scope="col">Retained rates</th><th scope="col">Net reserves use (+) / addition (−)</th><th scope="col">RA 900 revenue total</th><th scope="col">Total £ / resident</th></tr></thead><tbody>${rows}</tbody></table>`;
    $("capitalisation-context").innerHTML=`<strong>Capitalisation is not a government grant.</strong> ${identity(focus.code)} reports ${sourceValue(focus,fields.get("ra1_netoffexpcap"))} at RA 868: netting off expenditure capitalised by a Section 16(2)b direction. This is a non-current adjustment before RA 900, not extra grant income in the financing mix. Reserve use, borrowing, flexible capital receipts and Exceptional Financial Support are not interchangeable; this return does not identify all EFS arrangements.`;
  }
  function updateFundingContext() {
    if (!$("spending-funding-context")) return;
    $("spending-funding-context").innerHTML=`<p><strong>Selected-council funding context · 2026–27 budget:</strong></p>${selectedAuthorities().map(a=>`<p>${identity(a.code)}: own council-tax requirement ${sourceValue(a,fields.get("ra1_ctrtot"))}; explicit central-government grants ${monetary(government(a))}${cite(1)}; revenue-expenditure perimeter ${sourceValue(a,fields.get("ra1_revenuetot"))}.</p>`).join("")}<p>This is not a grant allocation to the selected service, a measure of fiscal need or an efficiency adjustment. <a href="#funding">Read the complete funding reconciliation</a>.</p>`;
  }
  function updateStory(step = state.story) {
    if (!$("story-chart")) return;
    state.story = step;
    const metric = step === 2 ? "resident" : "absolute";
    const ids = storySets[step];
    const pair = selectedAuthorities();
    const titles = ["Eight major service themes", "Education: the six published components", "The same themes, per resident", "Transport: six different functions"];
    if (pair.length > 3) {
      const detailId = ["ra1_servicetot", "ra1_edutot", "ra1_servicetot", "ra1_transprk"][step];
      const f = fields.get(detailId);
      const rows = pair.map(a => ({ a, n: metricValue(a,f,metric) }));
      $("story-chart-title").textContent = `${f.label} · all ${pair.length} selected authorities · ${unit(metric)}`;
      $("story-chart").innerHTML = councilRowsChart(rows, metric, f.label);
      $("story-legend").innerHTML = `<span>${identity(state.focus)} · focus, solid bar</span><span>${pair.length - 1} comparisons · outlined bars; full names and values in table</span>`;
      $("story-table").innerHTML = pairTable(ids,metric,titles[step]);
      $("story-caption").innerHTML = `For ${pair.length} selections, the graphic switches to one explicitly named line rather than overlapping council series. Each council gets its own labelled row, including missing returns. Scroll inside the graphic for all rows; the complete theme table keeps all ${pair.length} selections.${cite(1)}${metric === "resident" ? cite(8) : ""}`;
      document.querySelectorAll("[data-story]").forEach(button => button.setAttribute("aria-pressed", String(Number(button.dataset.story) === step)));
      updateContext();
      return;
    }
    const values = ids.flatMap(id => pair.map(a => metricValue(a, fields.get(id), metric))).filter(isNumber);
    const minimum = Math.min(0, ...values), upper = Math.max(0,...values), maximum = upper===minimum ? minimum+1 : upper;
    const range = maximum - minimum, left = 8, width = 490;
    const x = n => left + (n - minimum) / range * width;
    let content = "";
    for (let tick = 0; tick <= 4; tick++) {
      const n = minimum + range * tick / 4;
      content += `<line class="chart-grid" x1="${x(n)}" x2="${x(n)}" y1="30" y2="${ids.length * 72 + 20}"/><text class="chart-axis" x="${x(n)}" y="17" text-anchor="${tick === 0 ? "start" : "middle"}">${metric === "absolute" ? decimal.format(n) : nf.format(n)}</text>`;
    }
    content += `<line x1="${x(0)}" x2="${x(0)}" y1="30" y2="${ids.length * 72 + 20}" style="stroke:var(--cp-text-soft);stroke-width:1.5"/>`;
    ids.forEach((id, index) => {
      const f = fields.get(id), y = 40 + index * 72;
      const label = shortLabels[id] || f.label;
      const exact = pair.map(a => `${a.name}: ${formatMetric(metricValue(a, f, metric), metric)}`).join("; ");
      content += `<g class="chart-pair" tabindex="0" role="img" aria-label="${escape(label + ". " + exact)}"><title>${escape(exact)}</title><text class="chart-label" x="8" y="${y}">${escape(label)}</text>`;
      pair.forEach((a, i) => {
        const n = metricValue(a, f, metric);
        if (isNumber(n)) {
          const bx = Math.min(x(n), x(0)), bw = Math.abs(x(n) - x(0));
          content += `<rect class="${i ? "chart-comparison" : "chart-bar"}" data-council="${a.code}" style="${cssIdentity(a.code)}" x="${bx}" y="${y + 8 + i * 18}" width="${bw}" height="12"/><text class="chart-value" x="612" y="${y + 19 + i * 18}" text-anchor="end">${escape(formatMetric(n, metric))}</text>`;
        } else content += `<text class="chart-value" x="612" y="${y + 19 + i * 18}" text-anchor="end">Unavailable</text>`;
      });
      content += "</g>";
    });
    $("story-chart-title").textContent = `${titles[step]} · 2026–27 budget · ${unit(metric)}`;
    $("story-chart").innerHTML = svgFrame(content, ids.length * 72 + 34, titles[step], "Both councils share the same zero-based scale. Exact values are provided in the accompanying data table.");
    $("story-legend").innerHTML = pair.map((a,i) => `<span><span class="line-key${i ? " compare" : ""}"></span>${identity(a.code)} · ${i ? "outlined" : "solid"}</span>`).join("");
    $("story-table").innerHTML = pairTable(ids, metric, titles[step]);
    $("story-caption").innerHTML = `Shared zero-based scale; solid focus and outlined comparison bars. Exact values are available by keyboard focus, touch and the data table.${cite(1)}${metric === "resident" ? cite(8) : ""}`;
    document.querySelectorAll("[data-story]").forEach(button => button.setAttribute("aria-pressed", String(Number(button.dataset.story) === step)));
    updateContext();
  }

  function updateExplorer() {
    if (!$("peer-table")) return;
    const f = fields.get(state.field);
    const peers = peerAuthorities();
    const peerCodes = new Set(peers.map(a => a.code));
    const selected = new Set(selectedCodes());
    const added = selectedAuthorities().filter(a => !peerCodes.has(a.code));
    const available = peers.filter(a => isNumber(metricValue(a, f)));
    const ranked = [...available].sort((a, b) => metricValue(b, f) - metricValue(a, f) || a.name.localeCompare(b.name));
    const allRows = [...peers, ...added].sort((a, b) => {
      const x = metricValue(a, f), y = metricValue(b, f);
      if (isNumber(x) && isNumber(y)) return y - x || a.name.localeCompare(b.name);
      return isNumber(x) ? -1 : isNumber(y) ? 1 : a.name.localeCompare(b.name);
    });
    // Keep a legible graphic; never conceal the full selection in the accompanying table.
    const shown = ranked.slice(0, 12);
    for (const code of selectedCodes()) {
      if (!shown.some(a => a.code === code) && isNumber(metricValue(authorities.get(code), f))) shown.push(authorities.get(code));
    }
    shown.sort((a, b) => metricValue(b, f) - metricValue(a, f));
    const values = shown.map(a => metricValue(a, f));
    const lo = Math.min(0, ...values), upper = Math.max(0,...values), hi = upper===lo ? lo+1 : upper;
    const scale = n => 225 + (n - lo) / (hi - lo) * 270;
    let chart = "";
    if (shown.length) {
      for (let tick = 0; tick <= 3; tick++) {
        const n = lo + (hi - lo) * tick / 3;
        chart += `<line class="chart-grid" x1="${scale(n)}" x2="${scale(n)}" y1="32" y2="${shown.length * 38 + 34}"/><text class="chart-axis" x="${scale(n)}" y="18" text-anchor="middle">${state.metric === "absolute" ? nf.format(n) : nf.format(n)}</text>`;
      }
      chart += `<line x1="${scale(0)}" x2="${scale(0)}" y1="32" y2="${shown.length * 38 + 34}" style="stroke:var(--cp-text-soft);stroke-width:1.5"/>`;
      shown.forEach((a, i) => {
        const y = i * 38 + 45, n = metricValue(a, f);
        const label = a.name.length > 29 ? a.name.slice(0, 26) + "…" : a.name;
        chart += `<g tabindex="0" class="chart-pair" role="img" aria-label="${escape(a.name + ": " + formatMetric(n))}"><title>${escape(a.name + ": " + formatMetric(n) + (peerCodes.has(a.code) ? "" : "; selected outside peer group"))}</title><rect x="2" y="${y - 7}" width="8" height="8" style="${cssIdentity(a.code)};fill:var(--cp-council,var(--cp-border));stroke:var(--cp-text-soft)"/><text class="chart-label" x="16" y="${y + 1}">${escape(label)}${peerCodes.has(a.code) ? "" : " †"}</text><rect class="${a.code !== state.focus && selected.has(a.code) ? "chart-comparison" : "chart-bar"}" data-council="${a.code}" style="${cssIdentity(a.code)}" x="${Math.min(scale(n),scale(0))}" y="${y - 10}" width="${Math.abs(scale(n)-scale(0))}" height="16"/><text class="chart-value" x="617" y="${y + 2}" text-anchor="end">${escape(formatMetric(n))}</text></g>`;
      });
      $("comparison-chart").innerHTML = svgFrame(chart, shown.length * 38 + 45, f.label, "Largest twelve available budgets plus selected authorities, with an explicit zero baseline. Full data and source locators are in the table below.");
    } else {
      $("comparison-chart").innerHTML = '<p class="note">No ratios are available for this line and metric. The table preserves the reported numerator and explains the missing denominator; no unavailable value is ranked.</p>';
    }
    $("explorer-title").textContent = `${f.label} · 2026–27 budget · ${unit(state.metric)}`;
    $("explorer-caption").innerHTML = `${available.length} of ${peers.length} peer observations available for this measure. Graphic: largest 12 available values plus selected authorities (${shown.length} shown); † means selected outside the peer group. All ${allRows.length} rows, including missing values, appear below. No efficiency ranking is implied.${cite(f.source)}${state.metric === "resident" ? cite(8) : state.metric === "roads" ? cite(7) : ""}`;
    const rows = allRows.map(a => {
      const n = metricValue(a, f), pop = a.population, roads = a.roads;
      const denominator = state.metric === "resident" ? (pop ? `${nf.format(pop.value)} people · mid-2025` : "Population not joined") : state.metric === "roads" ? (f.denominator.key === "roads" && roads ? `${nf.format(roads.value)} miles · 2025` : "No eligible denominator") : "Not used";
      const rank = !isNumber(n) || !peerCodes.has(a.code) ? "—" : `${ranked.filter(p => metricValue(p, f) > n).length + 1}`;
      return `<tr${selected.has(a.code) ? ' class="selected"' : ""}><td>${rank}${peerCodes.has(a.code) ? "" : " †"}</td><th scope="row">${identity(a.code)}<br><small>${escape(a.subclass)}${!a.returned ? " · return absent" : ""}${a.notes && a.notes !== "M" ? ` · source flag ${escape(a.notes)}${cite(1)}` : ""}</small></th><td class="num">${sourceValue(a, f)}</td><td>${escape(denominator)}${state.metric === "resident" ? cite(8) : state.metric === "roads" ? cite(7) : ""}</td><td class="num">${isNumber(n) ? escape(formatMetric(n)) : escape(unavailable(a,f,state.metric))}</td><td><small>${escape(locator(a, f))}</small></td></tr>`;
    }).join("");
    $("peer-table").innerHTML = `<table><caption>${escape(f.label)} · 2026–27 budget · ${escape(unit(state.metric))}. Rank is descending value within the peer group, not performance.</caption><thead><tr><th scope="col">Order</th><th scope="col">Authority</th><th scope="col">Numerator (£m)</th><th scope="col">Denominator</th><th scope="col">Displayed metric</th><th scope="col">Source locator</th></tr></thead><tbody>${rows}</tbody></table>`;
    const d = f.denominator;
    $("line-explanation").innerHTML = `<p><strong>${escape(f.group)}</strong> · ${escape(f.part.toUpperCase())} line ${escape(f.line)} · ${escape(f.asset)}.${cite(f.source)}${cite(6)}</p><p>${f.kind === "service" ? "Planned net service provision, not a gross amount or an actual outturn." : "Accounting total, financing, reserve or memorandum line: read its sign and date; do not add overlapping totals."}</p><p>Preferred denominator: <strong>${escape(d.preferred)}</strong>. ${escape(d.definition)}${cite(d.source)}</p>`;
    $("metric-note").textContent = state.metric === "resident" ? "Per resident is population-scale context, not demand adjustment, service-user cost or efficiency." : state.metric === "roads" ? "Only selected maintenance lines can use this network-scale proxy. It excludes capital works and is not an audited cost per maintained mile. Other transport lines have no eligible ratio." : "Absolute budgets describe scale. Budgets with different service responsibilities are not like-for-like.";
    const a = authorities.get(state.focus), n = metricValue(a, f);
    const den = state.metric === "resident" ? a.population?.value : state.metric === "roads" ? a.roads?.value : null;
    $("comparison-formula").innerHTML = state.metric === "absolute" ? "" : `<div class="formula">${identity(a.code)}<br>${isNumber(raw(a,f)) ? `${nf.format(raw(a,f))} (£ thousands) × 1,000` : "Numerator not returned"} ÷ ${isNumber(den) ? nf.format(den) : "unavailable denominator"} = <strong>${isNumber(n) ? formatMetric(n) : unavailable(a,f,state.metric)}</strong>${cite(f.source,locator(a,f))}${cite(state.metric === "resident" ? 8 : 7)}</div>`;
    $("explorer-benchmark").innerHTML=`<p class="note">${benchmarkParagraph(f,state.metric)}</p>`;
    $("download-data").onclick = () => {
      const csvCell = text => `"${String(text).replace(/"/g,'""')}"`;
      const header = ["ONS code", "Authority", "Responsibility class", "Financial year", "Release", "Line", "Asset", "Numerator GBP thousands", "Value status", "Metric", "Denominator value", "Denominator year", "Displayed numeric value", "Source locator", "Budget source", "Denominator source"];
      const records = allRows.map(a => [a.code, a.name, a.subclass, data.meta.year, data.meta.published, f.line, f.asset, raw(a,f) ?? "", a.statuses[f.id] || "reported", state.metric, state.metric === "resident" ? a.population?.value ?? "" : state.metric === "roads" && d.key === "roads" ? a.roads?.value ?? "" : "", state.metric === "absolute" ? "" : "2025", metricValue(a,f) ?? "", locator(a,f), data.downloads[f.source - 1].url, state.metric === "resident" ? data.downloads[4].url : state.metric === "roads" ? data.downloads[3].url : ""]);
      const blob = new Blob(["\ufeff" + [header,...records].map(row => row.map(csvCell).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob), link = document.createElement("a");
      link.href = url; link.download = `council-budget-${f.asset}-${state.metric}-2026-27.csv`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
  }

  function updateRoads() {
    if (!$("roads-table")) return;
    const pair = selectedAuthorities();
    const f = fields.get("ra1_transrdsmnt"), a = pair[0], road = a.roads;
    const value = metricValue(a, f, "roads");
    $("roads-formula").innerHTML = `${identity(a.code)}<br>${isNumber(raw(a,f)) ? pounds(raw(a,f)*1000) : "No returned numerator"} planned structural maintenance ÷ ${road ? `(${road.major} + ${road.minor}) miles` : "unavailable road miles"} = <strong>${isNumber(value) ? `${pounds(value)} per network mile` : unavailable(a,f,"roads")}</strong>${cite(1,locator(a,f))}${cite(7)}`;
    $("roads-table").innerHTML = `<table><caption>Structural maintenance, 2026–27 budget; DfT network miles, 2025</caption><thead><tr><th scope="col">Authority</th><th scope="col">Budget (£m)</th><th scope="col">Miles</th><th scope="col">£ / network mile</th></tr></thead><tbody>${pair.map(x => `<tr><th scope="row">${identity(x.code)}</th><td class="num">${sourceValue(x,f)}</td><td class="num">${x.roads ? nf.format(x.roads.value) : "Not joined"}${cite(7)}</td><td class="num">${formatMetric(metricValue(x,f,"roads"),"roads")}</td></tr>`).join("")}</tbody></table>`;
  }
  function updateSelection() {
    const focus = authorities.get(state.focus), pair = selectedAuthorities();
    document.querySelectorAll("[data-money]").forEach(el => { el.textContent = monetary(focus.values[el.dataset.money]); el.title = locator(focus,fields.get(el.dataset.money)); });
    // The editorial introduction names the focus council after selection as well.
    document.querySelectorAll("[data-focus-name]").forEach(el => { el.innerHTML = identity(focus.code); });
    $("selection-colours").innerHTML = [...state.comparisons].map(code => `<span class="selected-chip">${identity(code)}<button type="button" data-remove="${code}" aria-label="Remove ${escape(authorities.get(code).name)}">×</button></span>`).join("");
    $("selection-colours").querySelectorAll("[data-remove]").forEach((button,index) => button.addEventListener("click", () => {
      state.comparisons.delete(button.dataset.remove); updateSelection();
      const remaining=$("selection-colours").querySelectorAll("[data-remove]");
      (remaining[Math.min(index,remaining.length-1)] || $("comparison-search")).focus();
    }));
    document.querySelectorAll('input[name="comparison"]').forEach(input => {
      input.checked = state.comparisons.has(input.value);
      input.closest(".comparison-option").classList.toggle("is-selected",input.checked);
    });
    const count=state.comparisons.size, selectedList=$("selected-comparisons");
    const noun=pair.some(a=>a.class==="O") ? (count===1 ? "authority" : "authorities") : (count===1 ? "council" : "councils");
    const announcement=`${count} comparison ${noun} selected.`;
    if ($("selected-count").textContent!==announcement) $("selected-count").textContent=announcement;
    $("selected-empty").hidden=count!==0;
    selectedList.hidden=count===0;
    if (count<=4) selectedList.open=true;
    else if (previousComparisonCount===null || previousComparisonCount<=4) selectedList.open=false;
    previousComparisonCount=count;
    $("clear-comparisons").disabled=count===0;
    const londonCount=londonComparisons.filter(code=>state.comparisons.has(code)).length, others=count-londonCount;
    const exactLondon=londonCount===londonComparisons.length && others===0;
    $("all-london").setAttribute("aria-pressed",String(exactLondon));
    $("all-london").dataset.selectionState=exactLondon ? "all" : londonCount>0 ? "partial" : "none";
    $("london-preset-status").textContent=(londonCount===londonComparisons.length ? `All ${londonCount} London comparison councils selected` : `${londonCount} of ${londonComparisons.length} London comparison councils selected`)+(others ? `; ${others} outside London.` : ".");
    const excluded=pair.filter(a=>a.code!==focus.code && (a.class!=="LB" || a.code==="E09000001")).length;
    const missing=pair.filter(a=>!a.returned).length;
    $("selection-status").innerHTML=(count ? "Benchmarks use selected London boroughs with valid matching data; Redbridge is excluded." : "No comparison selected: no peer benchmark is calculated.")+(excluded ? ` ${excluded} selected ${excluded===1 ? "authority has" : "authorities have"} different responsibilities.` : "")+(missing ? ` ${missing} selected ${missing===1 ? "return is" : "returns are"} missing; no figures are invented.` : "")+returnFlags(focus);
    filterComparisonOptions();
    document.querySelectorAll(".service").forEach(section => {
      const f = fields.get(section.id.slice(5));
      section.querySelector("table").innerHTML = `<caption>All ${pair.length} selected authorities · 2026–27 budget · £m</caption><thead><tr><th scope="col">Authority</th><th scope="col">Published amount</th></tr></thead><tbody>${pair.map(a => `<tr${a.code === state.focus ? ' class="selected"' : ""}><th scope="row">${identity(a.code)}</th><td class="num">${sourceValue(a,f)}</td></tr>`).join("")}</tbody>`;
      if (!section.querySelector("details").open) {
        clearLedgerChart(section);
      }
    });
    document.querySelectorAll("[data-summary-value]").forEach(el => {
      const f = fields.get(el.dataset.summaryValue);
      el.textContent = monetary(raw(focus, f));
      el.title = `${locator(focus,f)}; linked source inside expanded section`;
    });
    updateFunding(); updateFundingContext(); updateComposition(); updateStory(); updateExplorer(); updateRoads(); updateBenchmarks(); refreshOpenLedgers(); updateContext();
  }
  function explore(id, metric) {
    state.field = id;
    if (metric) { state.metric = metric; benchmarkState.metric=metric; }
    if (!$("budget-line")) {
      location.href=navigation.href(root+"index.html#london",query());
      return;
    }
    setControls();
    updateExplorer();
    updateContext();
    $("london").scrollIntoView({ behavior: reducedMotion.matches ? "instant" : "smooth" });
    $("budget-line").focus({ preventScroll: true });
  }
  function filterCatalogue() {
    const query = $("service-search").value.trim().toLocaleLowerCase("en-GB"), kind = $("catalog-kind").value;
    let count = 0;
    document.querySelectorAll(".service").forEach(section => {
      section.hidden = !(section.dataset.search.includes(query) && (kind === "all" || section.dataset.kind === kind));
      if (!section.hidden) count++;
    });
    $("catalog-count").textContent = `${count} of 192 accounting / theme lines match. The 129 individual services have separate documents.`;
    requestAnimationFrame(updateProgress);
  }
  function filterComparisonOptions() {
    const search=$("comparison-search").value.trim().toLocaleLowerCase("en-GB");
    let matches=0, checked=0;
    document.querySelectorAll("[data-option-search]").forEach(label=>{
      label.hidden=!label.dataset.optionSearch.includes(search);
      if (!label.hidden) { matches++; if (label.querySelector("input").checked) checked++; }
    });
    $("comparison-options").hidden=matches===0;
    $("comparison-no-results").hidden=matches!==0;
    $("comparison-result-count").textContent=`${matches} ${matches===1 ? "matching authority" : "matching authorities"}; ${checked} selected in these results.`;
  }
  function revealHash() {
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target?.classList.contains("service")) {
      target.hidden = false;
      target.querySelector("details").open = true;
      renderLedger(target);
      target.scrollIntoView();
    }
  }
  function updateProgress() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const percent = max > 0 ? Math.min(100, Math.max(0, window.scrollY / max * 100)) : 100;
    $("reading-progress").value = percent;
    $("reading-progress").textContent = `${Math.round(percent)}%`;
  }
  document.querySelectorAll('input[name="comparison"]').forEach(input => input.addEventListener("change", () => {
    if (input.checked) state.comparisons.add(input.value); else state.comparisons.delete(input.value);
    updateSelection();
  }));
  $("comparison-search").addEventListener("input", filterComparisonOptions);
  $("all-london").addEventListener("click", () => { state.comparisons = new Set(londonComparisons); $("comparison-search").value=""; updateSelection(); });
  $("clear-comparisons").addEventListener("click", () => { state.comparisons.clear(); updateSelection(); $("comparison-search").focus(); });
  $("reset-comparisons").addEventListener("click", () => { state.comparisons = new Set(["E09000031"]); $("comparison-search").value=""; updateSelection(); });
  $("peer-group")?.addEventListener("change", e => { state.peer = e.target.value; updateSelection(); });
  $("budget-line")?.addEventListener("change", e => { state.field = e.target.value; updateExplorer(); updateContext(); });
  $("shared-metric").addEventListener("change", e=>setMetric(e.target.value));
  for (const key of ["filter","sort"]) $("benchmark-"+key)?.addEventListener("change", e=>{ benchmarkState[key]=e.target.value; updateBenchmarks(); updateContext(); });
  document.querySelectorAll("[data-ledger-metric]").forEach(selector=>selector.addEventListener("change",()=>{
    setMetric(selector.value);
  }));
  $("service-search")?.addEventListener("input", filterCatalogue);
  $("catalog-kind")?.addEventListener("change", filterCatalogue);
  function filterDirectory() {
    const search=$("directory-search").value.trim().toLocaleLowerCase("en-GB"), group=$("directory-group").value;
    const entries=[...document.querySelectorAll(".directory-entry")];
    for (const entry of entries) entry.hidden=!entry.dataset.directorySearch.includes(search) || Boolean(group && entry.dataset.directoryGroup!==group);
    $("directory-count").textContent=`${entries.filter(entry=>!entry.hidden).length} of 129 service documents match.`;
    requestAnimationFrame(updateProgress);
  }
  $("directory-search")?.addEventListener("input",filterDirectory);
  $("directory-group")?.addEventListener("change",filterDirectory);
  $("report-search")?.addEventListener("input", e => {
    const query = e.target.value.toLocaleLowerCase("en-GB");
    document.querySelectorAll("[data-report-search]").forEach(row => { row.hidden = !row.dataset.reportSearch.includes(query); });
  });
  document.querySelectorAll("[data-explore]").forEach(button => button.addEventListener("click", () => explore(button.dataset.explore)));
  document.querySelectorAll("[data-story]").forEach(button => button.addEventListener("click", () => updateStory(Number(button.dataset.story))));
  $("explore-roads")?.addEventListener("click", () => explore("ra1_transrdsmnt", "roads"));
  $("theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    updateThemeButton();
    updateContext();
  });
  window.addEventListener("hashchange", revealHash);
  let scrollPending = false;
  window.addEventListener("scroll", () => {
    if (!scrollPending) requestAnimationFrame(() => { updateProgress(); scrollPending = false; });
    scrollPending = true;
  }, { passive: true });
  window.addEventListener("resize", updateProgress);
  document.addEventListener("toggle", () => requestAnimationFrame(updateProgress), true);
  document.addEventListener("toggle", event=>{
    const section=event.target.parentElement;
    if (section?.classList.contains("service")) {
      if (event.target.open) renderLedger(section);
      else clearLedgerChart(section);
    }
  },true);
  window.addEventListener("popstate",()=>{
    const restored=navigation.parse(location.search,data.authorities,data.fields);
    Object.assign(state,{comparisons:new Set(restored.peers),peer:restored.group,field:restored.field,metric:restored.metric,story:restored.story});
    Object.assign(benchmarkState,{metric:restored.metric,filter:restored.filter,sort:restored.sort});
    if (restored.theme) document.documentElement.dataset.theme=restored.theme;
    ledgerMetrics.clear(); setControls(); updateSelection();
  });
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => {
      entries.filter(entry => entry.isIntersecting).forEach(entry => updateStory(Number(entry.target.dataset.step)));
    }, { rootMargin: "-30% 0px -30% 0px", threshold: 0 });
    document.querySelectorAll(".story-step").forEach(step => observer.observe(step));
    if (!reducedMotion.matches) {
      const reveal = new IntersectionObserver(entries => entries.forEach(entry => {
        if (entry.isIntersecting) { entry.target.classList.add("is-visible"); reveal.unobserve(entry.target); }
      }), { threshold: .08 });
      document.querySelectorAll(".chapter > h2,.chapter > .section-head,.stat-grid,.coverage-card,.service > details > summary,.ledger-figure").forEach(el => {
        el.classList.add("reveal", "will-reveal"); reveal.observe(el);
      });
    }
  }
  setControls(); updateSelection();
  document.documentElement.classList.add("js");
  updateProgress(); revealHash();
  // Expose read-only data for reproducibility and local audits, not a remote dependency.
  window.atlasAudit = Object.freeze({ version: data.meta.year, fields: fields.size, authorities: authorities.size });
})();
