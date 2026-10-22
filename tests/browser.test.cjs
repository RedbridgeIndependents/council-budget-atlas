const { test, before, after } = require("node:test");
const assert = require("node:assert/strict");
const { chromium } = require("@playwright/test");
const path = require("node:path");
const fs = require("node:fs");
const { pathToFileURL } = require("node:url");
const axe = require.resolve("axe-core/axe.min.js");
const url = pathToFileURL(path.resolve("index.html")).href;
let browser;
before(async () => { browser = await chromium.launch({ headless: true, channel: process.env.ATLAS_BROWSER || "msedge" }); });
after(async () => { await browser?.close(); });

async function open(options = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, ...options });
  const page = await context.newPage();
  const errors = [], requests = [];
  page.on("pageerror", e => errors.push(e.message));
  page.on("request", r => { if (r.url().startsWith("http")) requests.push(r.url()); });
  await page.goto(url);
  return { page, context, errors, requests };
}

test("offline initial page, precise figures, source locators and no console errors", async () => {
  const { page, context, errors, requests } = await open({ offline: true });
  assert.equal(await page.locator(".service").count(), 321);
  assert.equal(await page.locator("#total .hero-number .number").textContent(), "£787.766m");
  assert.equal(await page.locator("#funding .hero-number .number").textContent(), "£167.968m");
  assert.match(await page.locator("#funding-cards").textContent(), /477\.529/);
  assert.equal(await page.locator("#benchmark-table tbody tr").count(),129);
  assert.match(await page.locator("#total-benchmark").textContent(),/1 valid peers/);
  assert.match(await page.locator("#roads-formula").textContent(), /1,718,000.*36 \+ 295.*5,190/s);
  assert.match(await page.locator("#explorer-caption").textContent(), /31 of 32 peer observations/);
  assert.equal(await page.locator("#peer-table tbody tr").count(), 32);
  assert.match(await page.locator("#peer-table").textContent(), /RA_LA_Data_2026-27!ES284/);
  assert.equal(await page.locator("#story-chart svg").count(), 1);
  assert.deepEqual(errors, []);
  assert.deepEqual(requests, []);
  await context.close();
});

test("selection, metrics, peer groups, missing returns, zero and negative income", async () => {
  const { page, context, errors } = await open();
  await page.selectOption("#display-metric", "resident");
  const redbridge = page.locator("#peer-table tbody tr").filter({ has: page.locator('[data-council="E09000026"]') });
  assert.match(await redbridge.textContent(), /2,448/);
  await page.locator("#comparison-picker > summary").click();
  await page.check('input[name="comparison"][value="E09000011"]');
  assert.match(await page.locator("#selection-status").textContent(), /missing returns remain visible/);
  assert.match(await page.locator('[data-funding-authority="E09000011"]').textContent(),/Not available/);
  await page.check('input[name="comparison"][value="E09000001"]');
  assert.match(await page.locator("#selection-status").textContent(), /distinct responsibilities/);
  await page.selectOption("#budget-line", "ra1_transprk");
  await page.selectOption("#display-metric", "absolute");
  assert.match(await redbridge.textContent(), /−£17\.984m/);
  const negative = await page.locator("#comparison-chart").evaluate(el => {
    const rect = el.querySelector('[data-council="E09000026"]');
    return rect && Number(rect.getAttribute("width")) > 0;
  });
  assert.ok(negative);
  await page.selectOption("#display-metric", "roads");
  assert.match(await page.locator("#comparison-chart").textContent(), /No ratios are available/);
  await page.selectOption("#budget-line", "ra1_transrdsmnt");
  assert.match(await redbridge.textContent(), /5,190/);
  await page.selectOption("#peer-group", "all");
  assert.equal(await page.locator("#peer-table tbody tr").count(), 415);
  assert.match(await page.locator("#selection-status").textContent(), /different service responsibilities/);
  await page.check('input[name="comparison"][value="E08000038"]');
  await page.selectOption("#display-metric", "resident");
  assert.match(await page.locator("#peer-table tbody tr").filter({has:page.locator('[data-council="E08000038"]')}).textContent(),/Population not joined/);
  assert.deepEqual(errors, []);
  await context.close();
});

test("catalogue search, individual sections, story buttons and CSV export", async () => {
  const { page, context, errors } = await open({ acceptDownloads: true, reducedMotion: "reduce" });
  await page.fill("#service-search", "library");
  assert.equal(await page.locator(".service:visible").count(), 1);
  await page.locator("#line-ra1_cullib summary").click();
  await page.locator('[data-explore="ra1_cullib"]').click();
  assert.equal(await page.locator("#budget-line").inputValue(), "ra1_cullib");
  await page.fill("#service-search", "");
  await page.selectOption("#catalog-kind", "service");
  assert.equal(await page.locator(".service:visible").count(), 129);
  await page.locator('[data-story="1"]').click();
  assert.match(await page.locator("#story-chart-title").textContent(), /Education/);
  assert.equal(await page.locator("#story-table tbody tr").count(), 6);
  await page.locator('[data-story="3"]').click();
  assert.match(await page.locator("#story-table").textContent(), /−£17.984m/);
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#download-data").click();
  const download = await downloadPromise;
  const text = fs.readFileSync(await download.path(), "utf8");
  assert.match(text, /Financial year/);
  assert.match(text, /2026-27/);
  assert.match(text, /library|cullib/);
  assert.deepEqual(errors, []);
  await context.close();
});

test("desktop scroll story, navigation, progress and back-to-top", async () => {
  const { page, context } = await open({ reducedMotion: "reduce" });
  await page.locator('[data-step="2"]').scrollIntoViewIfNeeded();
  await page.waitForFunction(() => document.querySelector("#story-chart-title").textContent.includes("per resident"));
  assert.ok(await page.locator("#reading-progress").evaluate(el => el.value > 0));
  await page.locator('nav a[href="#services"]').click();
  assert.equal(new URL(page.url()).hash, "#services");
  const box = await page.locator("#services").boundingBox();
  assert.ok(box.y >= 110, `anchor top ${box.y}`);
  await page.locator('a.back-top').click();
  await page.waitForFunction(() => window.scrollY === 0);
  assert.equal(await page.locator("#reading-progress").evaluate(el => Math.round(el.value)), 0);
  await context.close();
});

test("mobile light/dark layouts, keyboard skip, source links and reduced motion", async () => {
  const { page, context, errors } = await open({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  await page.keyboard.press("Tab");
  assert.equal(await page.locator(".skip").evaluate(el => el === document.activeElement), true);
  await page.keyboard.press("Enter");
  assert.equal(await page.locator("#content").evaluate(el => el === document.activeElement), true);
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), "auto");
  const original = await page.locator("html").getAttribute("data-theme");
  await page.locator("#theme-toggle").click();
  assert.notEqual(await page.locator("html").getAttribute("data-theme"), original);
  await page.locator('nav a[href="#sources"]').click();
  assert.equal(await page.locator("#sources").isVisible(), true);
  assert.deepEqual(errors, []);
  await context.close();
});

test("no-JS fallback contains real data, complete service catalogue and working source anchors", async () => {
  const { page, context, requests } = await open({ javaScriptEnabled: false, offline: true });
  assert.equal(await page.locator("#total .hero-number .number").textContent(), "£787.766m");
  assert.equal(await page.locator(".service").count(), 321);
  await page.locator("#line-ra1_cullib summary").click();
  assert.match(await page.locator("#line-ra1_cullib").textContent(), /5\.867m/);
  assert.equal(await page.locator("#focus-council").isVisible(), false);
  assert.equal(await page.locator("#peer-table tbody tr").count(), 32);
  assert.deepEqual(requests, []);
  await context.close();
});

test("multi-selection and All London synchronize funding, themes, service tables and benchmark",async()=>{
  const {page,context,errors}=await open({reducedMotion:"reduce"});
  await page.locator("#comparison-picker > summary").click();
  await page.check('input[name="comparison"][value="E09000027"]');
  assert.match(await page.locator("#selected-count").textContent(),/3 selected/);
  assert.equal(await page.locator("#funding-table [data-funding-authority]").count(),3);
  assert.equal(await page.locator("#line-ra1_cullib tbody tr").count(),3);
  await page.locator("#all-london").click();
  assert.match(await page.locator("#selected-count").textContent(),/33 selected/);
  assert.equal(await page.locator('input[name="comparison"]:checked').count(),32);
  assert.equal(await page.locator("#funding-table [data-funding-authority]").count(),33);
  assert.equal(await page.locator("#line-ra1_cullib tbody tr").count(),33);
  assert.equal(await page.locator("#theme-table tbody tr").count(),33);
  assert.equal(await page.locator("#peer-table tbody tr").count(),33);
  assert.match(await page.locator("#total-benchmark").textContent(),/30 valid peers/);
  assert.match(await page.locator("#selection-status").textContent(),/City of London.*distinct responsibilities/);
  const row=page.locator('[data-benchmark-row="ra1_cullib"]').first();
  const difference=await row.locator("[data-difference]").getAttribute("data-difference");
  assert.ok(Number.isFinite(Number(difference)));
  assert.match(await page.locator('[data-benchmark="ra1_cullib"]').textContent(),/30 valid peers/);
  await page.getByRole("button",{name:"Remove Waltham Forest",exact:true}).click();
  assert.match(await page.locator("#selected-count").textContent(),/32 selected/);
  await page.locator("#clear-comparisons").click();
  assert.match(await page.locator("#selected-count").textContent(),/1 selected/);
  assert.match(await page.locator("#headline-benchmarks").textContent(),/No valid differences/);
  await page.locator("#reset-comparisons").click();
  assert.match(await page.locator("#selected-count").textContent(),/2 selected/);
  assert.equal(await page.locator("#funding-table [data-funding-authority]").count(),2);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("funding signs, source years, null and zero handling with exact percentages",async()=>{
  const {page,context}=await open();
  const funding=page.locator('[data-funding-authority="E09000026"]');
  assert.match(await funding.locator('[data-funding-line="ra1_ctrtot"]').textContent(),/167\.968.*23\.0%/s);
  assert.match(await funding.locator('[data-funding-line="ra1_appresunall"]').textContent(),/−£20\.000m.*−?2\.7%/s);
  assert.match(await funding.locator('[data-funding-line="ra1_grantpol"]').textContent(),/£0\.000m.*0\.0%/s);
  assert.match(await funding.textContent(),/difference.*£0\.000m/s);
  assert.match(await page.locator("#capitalisation-context").textContent(),/−£70\.001m.*RA 868/);
  assert.match(await page.locator("#funding").textContent(),/not cash already collected/);
  assert.match(await page.locator("#funding").textContent(),/not imported/);
  await context.close();
});

test("benchmark filter, ordering and detail links preserve one canonical comparison",async()=>{
  const {page,context}=await open({reducedMotion:"reduce"});
  await page.selectOption("#benchmark-filter","above");
  assert.ok((await page.locator("#benchmark-table [data-difference]").evaluateAll(els=>els.map(el=>Number(el.dataset.difference)))).every(n=>n>0));
  await page.selectOption("#benchmark-sort","below");
  await page.selectOption("#benchmark-filter","below");
  const values=await page.locator("#benchmark-table [data-difference]").evaluateAll(els=>els.map(el=>Number(el.dataset.difference)));
  assert.ok(values.every((n,i)=>n<0 && (i===0 || n>=values[i-1])));
  await page.locator("#benchmark-table tbody a").first().click();
  const id=new URL(page.url()).hash;
  assert.equal(await page.locator(id+" > details").getAttribute("open"),"");
  assert.match(await page.locator(id+" [data-benchmark]").textContent(),/Investigate, not a verdict/);
  await page.selectOption("#benchmark-metric","roads");
  await page.selectOption("#benchmark-filter","available");
  assert.equal(await page.locator("#benchmark-table tbody tr").count(),3);
  await context.close();
});

test("official colours, logo-permission fallbacks and licensed typography work offline in both themes",async()=>{
  const {page,context,requests}=await open({offline:true});
  const verified=await page.evaluate(()=>{
    const data=JSON.parse(document.getElementById("atlas-data").textContent);
    const colours=data.colours;
    return {
      counts:data.authorities.filter(a=>a.class==="LB" && colours[a.code]?.colour).length,
      redbridge:colours.E09000026.colour,
      token:getComputedStyle(document.documentElement).getPropertyValue("--cp-council-E09000026").trim(),
      fonts:document.fonts.check('800 24px "Barlow Condensed"'),
      cleared:Object.values(data.logos).filter(logo=>logo.permission==="permitted").length
    };
  });
  assert.equal(verified.counts,33);
  assert.equal(verified.redbridge.toLowerCase(),"#942725");
  assert.equal(verified.token.toLowerCase(),verified.redbridge.toLowerCase());
  assert.equal(verified.fonts,true);
  assert.equal(verified.cleared,0);
  assert.equal(await page.locator("img").count(),0);
  assert.match(await page.locator("#logo-coverage").textContent(),/0 reuse permissions established/);
  assert.equal(await page.locator('#selection-colours [data-council="E09000026"]').getAttribute("data-logo-state"),"not-established");
  for(const theme of ["light","dark"]){
    await page.evaluate(t=>document.documentElement.dataset.theme=t,theme);
    const contrast=await page.locator('#selection-colours [data-council="E09000026"]').evaluate(el=>{
      const rgb=s=>s.match(/\d+(\.\d+)?/g).slice(0,3).map(Number);
      const luminance=arr=>arr.map(n=>{n/=255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;}).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);
      const foreground=luminance(rgb(getComputedStyle(el).color));
      const background=luminance(rgb(getComputedStyle(document.body).backgroundColor));
      return (Math.max(foreground,background)+.05)/(Math.min(foreground,background)+.05);
    });
    assert.ok(contrast>=4.5);
    const colours=await page.evaluate(()=>({
      markers:[...document.querySelectorAll('.council[data-council="E09000026"]')].map(el=>getComputedStyle(el,"::before").backgroundColor),
      series:[...document.querySelectorAll('rect[data-council="E09000026"]')].map(el=>getComputedStyle(el).fill),
      themes:[...document.querySelectorAll("#theme-bars .fill")].map(el=>getComputedStyle(el).backgroundColor)
    }));
    assert.ok(colours.markers.length>10);
    assert.ok(colours.series.length>5);
    for(const colour of [...colours.markers,...colours.series,...colours.themes]) assert.equal(colour,"rgb(148, 39, 37)");
  }
  assert.deepEqual(requests,[]);
  await context.close();
});

test("mobile comparison search and checkboxes have normal keyboard and touch operation",async()=>{
  const {page,context}=await open({viewport:{width:390,height:844},reducedMotion:"reduce",hasTouch:true});
  await page.locator("#comparison-picker > summary").focus();
  await page.keyboard.press("Enter");
  await page.locator("#comparison-search").fill("Sutton");
  const checkbox=page.locator('input[name="comparison"][value="E09000029"]');
  await checkbox.focus(); await page.keyboard.press("Space");
  assert.equal(await checkbox.isChecked(),true);
  assert.match(await page.locator("#selected-count").textContent(),/3 selected/);
  await page.getByRole("button",{name:"Remove Sutton",exact:true}).tap();
  assert.match(await page.locator("#selected-count").textContent(),/2 selected/);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await context.close();
});

test("exhaustive rendered All London service values, funding shares, summary gaps and CSV stay source-consistent",async()=>{
  const {page,context}=await open({reducedMotion:"reduce",acceptDownloads:true});
  await page.locator("#all-london").click();
  const result=await page.evaluate(()=>{
    const data=JSON.parse(document.getElementById("atlas-data").textContent);
    const london=data.authorities.filter(a=>a.class==="LB");
    const authorities=new Map(data.authorities.map(a=>[a.code,a]));
    const fields=new Map(data.fields.map(f=>[f.id,f]));
    const decimal=new Intl.NumberFormat("en-GB",{minimumFractionDigits:3,maximumFractionDigits:3});
    const integer=new Intl.NumberFormat("en-GB",{maximumFractionDigits:0});
    const money=n=>n===null ? "Not available" : `${n<0 ? "−" : ""}£${decimal.format(Math.abs(n)/1000)}m`;
    const redbridge=authorities.get("E09000026"), errors=[];
    let cells=0, shares=0, benchmarks=0;
    for(const section of document.querySelectorAll(".service")){
      const f=fields.get(section.id.slice(5));
      for(const row of section.querySelectorAll("tbody tr")){
        const a=authorities.get(row.querySelector("[data-council]").dataset.council);
        const text=row.querySelector("td").textContent.split("[")[0];
        if(text!==money(a.values[f.id])) errors.push(`${a.code}/${f.id}: ${text}`);
        cells++;
      }
    }
    for(const card of document.querySelectorAll("[data-funding-authority]")){
      const a=authorities.get(card.dataset.fundingAuthority), total=a.values.ra1_revenuetot;
      for(const item of data.meta.fundingLines){
        const row=card.querySelector(`[data-funding-line="${item.id}"]`), raw=a.values[item.id];
        const contribution=raw===null ? null : raw*item.sign;
        const expected=contribution!==null && total!==null && total!==0 ? `${(contribution/total*100).toFixed(1)}%` : "Not available";
        if(row.cells[1].textContent.split("[")[0]!==money(contribution) || row.cells[3].textContent!==expected) errors.push(`${a.code}/${item.id}/financing`);
        shares++;
      }
    }
    for(const row of document.querySelectorAll("#benchmark-table [data-benchmark-row]")){
      const f=fields.get(row.dataset.benchmarkRow);
      const values=london.filter(a=>a.code!==redbridge.code && a.code!=="E09000001" && a.values[f.id]!==null && a.population?.value>0).map(a=>a.values[f.id]*1000/a.population.value).sort((a,b)=>a-b);
      const middle=(values[Math.floor((values.length-1)/2)]+values[Math.ceil((values.length-1)/2)])/2;
      const difference=redbridge.values[f.id]*1000/redbridge.population.value-middle;
      const actual=Number(row.querySelector("[data-difference]").dataset.difference);
      if(Math.abs(actual-difference)>1e-8) errors.push(`${f.id}/difference`);
      const rendered=`${difference<0 ? "−" : ""}£${integer.format(Math.abs(difference))}`;
      if(row.querySelector("[data-difference]").textContent!==rendered || !document.querySelector(`[data-benchmark="${f.id}"]`).textContent.includes(rendered)) errors.push(`${f.id}/rounding-detail`);
      benchmarks++;
    }
    return {cells,shares,benchmarks,errors:errors.slice(0,10)};
  });
  assert.deepEqual(result,{cells:321*33,shares:13*33,benchmarks:129,errors:[]});
  await page.selectOption("#budget-line","ra1_transrdsmnt");
  await page.selectOption("#display-metric","roads");
  const promise=page.waitForEvent("download");
  await page.locator("#download-data").click();
  const text=fs.readFileSync(await (await promise).path(),"utf8");
  assert.match(text,/"E09000026","Redbridge".*"1718".*"331".*"5190\.332326283988"/);
  assert.match(text,/"E09000011","Greenwich".*"not-returned"/);
  assert.equal(text.split(/\r?\n/).length,34);
  await context.close();
});

test("all 321 ledger charts lazy-render, reconcile every selected value and benchmark in each supported lens",async()=>{
  const {page,context,errors}=await open({reducedMotion:"reduce"});
  assert.equal(await page.locator("[data-ledger-chart]").count(),321);
  assert.equal(await page.locator(".ledger-chart svg").count(),0);
  await page.locator("#all-london").click();
  const result=await page.evaluate(async()=>{
    const data=JSON.parse(document.getElementById("atlas-data").textContent);
    const authorities=new Map(data.authorities.map(a=>[a.code,a]));
    const fields=new Map(data.fields.map(f=>[f.id,f]));
    const decimal=new Intl.NumberFormat("en-GB",{minimumFractionDigits:3,maximumFractionDigits:3});
    const integer=new Intl.NumberFormat("en-GB",{maximumFractionDigits:0});
    const formatted=(n,metric)=>n===null ? "Not available" : `${n<0 ? "−" : ""}£${metric==="absolute" ? decimal.format(Math.abs(n))+"m" : integer.format(Math.abs(n))}`;
    const failures=[]; let charts=0,observations=0,zeroes=0,negative=0,missing=0;
    const toggled=(details,open)=>new Promise(resolve=>{
      details.addEventListener("toggle",resolve,{once:true});details.open=open;
    });
    for(const section of document.querySelectorAll(".service")){
      const f=fields.get(section.id.slice(5));
      const details=section.querySelector("details"), select=section.querySelector("[data-ledger-metric]");
      await toggled(details,true);
      for(const metric of [...select.options].map(option=>option.value)){
        select.value=metric;select.dispatchEvent(new Event("change",{bubbles:true}));
        const chart=section.querySelector("[data-ledger-chart]");
        const groups=[...chart.querySelectorAll("[data-chart-authority]")];
        if(groups.length!==33 || !chart.querySelector("svg desc")) failures.push(`${f.id}/${metric}/coverage`);
        const values=[];
        for(const group of groups){
          const a=authorities.get(group.dataset.chartAuthority), raw=a.values[f.id];
          const denominator=metric==="resident" ? a.population?.value : metric==="roads" ? a.roads?.value : 1000000;
          const value=raw===null || !(denominator>0) ? null : metric==="absolute" ? raw/1000 : raw*1000/denominator;
          const actual=group.dataset.chartValue==="" ? null : Number(group.dataset.chartValue);
          const bar=group.querySelector("rect[data-council]");
          if(actual!==value || group.querySelector(".chart-value").textContent!==formatted(value,metric)) failures.push(`${f.id}/${metric}/${a.code}/value`);
          const row=[...section.querySelectorAll("table tbody tr")].find(row=>row.querySelector("[data-council]").dataset.council===a.code);
          if(value!==null && row.cells[3].textContent!==formatted(value,metric)) failures.push(`${f.id}/${metric}/${a.code}/table`);
          if(value===null){if(bar)failures.push(`${f.id}/${a.code}/null-bar`);missing++;}
          else if(value===0){if(Number(bar?.getAttribute("width"))!==0)failures.push(`${f.id}/${a.code}/zero-bar`);zeroes++;}
          else if(value<0)negative++;
          if(a.code==="E09000026" && bar && getComputedStyle(bar).fill!=="rgb(148, 39, 37)") failures.push(`${f.id}/redbridge-colour`);
          if(a.code!=="E09000026" && a.code!=="E09000001" && a.class==="LB" && value!==null)values.push(value);
          observations++;
        }
        const supported=f.kind==="service" || f.kind==="theme" || f.id==="ra1_servicetot";
        const line=chart.querySelector("[data-benchmark-value]");
        if(supported && values.length){
          values.sort((a,b)=>a-b);
          const expected=(values[Math.floor((values.length-1)/2)]+values[Math.ceil((values.length-1)/2)])/2;
          if(!line || Number(line.dataset.benchmarkValue)!==expected)failures.push(`${f.id}/${metric}/benchmark`);
        }else if(line)failures.push(`${f.id}/ineligible-benchmark`);
        charts++;
      }
      await toggled(details,false);
    }
    return {charts,observations,zeroes,negative,missing,failures:failures.slice(0,15)};
  });
  assert.equal(result.charts,321*2+3);
  assert.equal(result.observations,(321*2+3)*33);
  assert.ok(result.zeroes>100);
  assert.ok(result.negative>100);
  assert.ok(result.missing>600);
  assert.deepEqual(result.failures,[]);
  assert.equal(await page.locator(".ledger-chart svg").count(),0);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("ledger unavailable states do not fabricate bars when every selected numerator is absent",async()=>{
  const context=await browser.newContext({reducedMotion:"reduce"});
  const page=await context.newPage(),errors=[];
  page.on("pageerror",error=>errors.push(error.message));
  let html=fs.readFileSync("index.html","utf8");
  const pattern=/<script type="application\/json" id="atlas-data">([\s\S]*?)<\/script>/;
  const data=JSON.parse(html.match(pattern)[1]);
  for(const code of ["E09000026","E09000031"]){
    const a=data.authorities.find(a=>a.code===code);
    a.values.ra1_transrdsmnt=null;
    a.statuses.ra1_transrdsmnt=code==="E09000026" ? "suppressed" : "not-applicable";
  }
  html=html.replace(pattern,`<script type="application/json" id="atlas-data">${JSON.stringify(data).replace(/</g,"\\u003c")}</script>`);
  await page.setContent(html,{waitUntil:"load"});
  const section=page.locator("#line-ra1_transrdsmnt");
  await section.locator("summary").click();
  assert.equal(await section.locator("[data-chart-unavailable]").count(),1);
  assert.equal(await section.locator("svg").count(),0);
  assert.match(await section.locator("tbody").textContent(),/Suppressed.*Not applicable/s);
  assert.equal(await section.locator("[data-benchmark-value]").count(),0);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("ledger chart changes synchronize selection, no peers, negative geometry and mobile keyboard lenses",async()=>{
  const {page,context,errors}=await open({viewport:{width:390,height:844},reducedMotion:"reduce",hasTouch:true});
  const section=page.locator("#line-ra1_transprk");
  await section.locator("summary").click();
  assert.equal(await section.locator("[data-chart-authority]").count(),2);
  const geometry=await section.locator('[data-chart-authority="E09000026"] rect[data-council]').evaluate(bar=>({x:Number(bar.getAttribute("x")),width:Number(bar.getAttribute("width"))}));
  assert.ok(geometry.width>0);
  assert.ok(geometry.x+geometry.width>geometry.x);
  assert.match(await section.locator("figcaption").textContent(),/No verified matching service-unit denominator/);
  await section.locator("select").selectOption("resident");
  assert.match(await section.locator("table caption").textContent(),/per resident/);
  await page.locator("#all-london").click();
  assert.equal(await section.locator("[data-chart-authority]").count(),33);
  assert.equal(await section.locator("tbody tr").count(),33);
  assert.match(await section.locator("figcaption").textContent(),/30 peers/);
  await page.locator("#clear-comparisons").click();
  assert.equal(await section.locator("[data-chart-authority]").count(),1);
  assert.equal(await section.locator("[data-benchmark-value]").count(),0);
  const road=page.locator("#line-ra1_transrdsmnt");
  await road.locator("summary").click();
  await road.locator("select").focus();
  await page.keyboard.press("End");await page.keyboard.press("Enter");
  assert.equal(await road.locator("select").inputValue(),"roads");
  assert.match(await road.locator("table").textContent(),/331 miles.*5,190/s);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert.deepEqual(errors,[]);
  await context.close();
});

test("axe WCAG 2.2 AA audit in both themes and mobile", async () => {
  const { page, context } = await open({ reducedMotion: "reduce" });
  await page.locator("#line-ra1_transrdsmnt summary").click();
  await page.locator("#line-ra1_transprk summary").click();
  await page.addScriptTag({ path: axe });
  for (const theme of ["light", "dark"]) {
    await page.evaluate(t => document.documentElement.dataset.theme = t, theme);
    const result = await page.evaluate(async () => axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"] } }));
    assert.deepEqual(result.violations.map(v => ({ id: v.id, description: v.description, nodes: v.nodes.slice(0,3).map(n => n.target) })), [], theme);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  const result = await page.evaluate(async () => axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"] } }));
  assert.deepEqual(result.violations.map(v => ({ id: v.id, nodes: v.nodes.slice(0,3).map(n => n.target) })), [], "mobile");
  await context.close();
});
