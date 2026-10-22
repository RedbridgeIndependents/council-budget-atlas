const {test,before,after}=require("node:test");
const assert=require("node:assert/strict");
const {chromium}=require("@playwright/test");
const {pathToFileURL}=require("node:url");
const path=require("node:path");
const fs=require("node:fs");
const data=require("../data/processed/atlas.json");
const manifest=require("../data/processed/documents.json");
const axe=require.resolve("axe-core/axe.min.js");
const focus="E09000026", forest="E09000031";
const london=data.authorities.filter(a=>a.class==="LB").map(a=>a.code);
const locationFor=(file,query="")=>pathToFileURL(path.resolve(file)).href+(query ? "?"+query : "");
const selectedQuery=metric=>new URLSearchParams({peers:london.filter(code=>code!==focus).join(","),metric,scoutTheme:"light"}).toString();
let browser;
before(async()=>{browser=await chromium.launch({headless:true,channel:process.env.ATLAS_BROWSER || "msedge"});});
after(async()=>{await browser?.close();});

async function open(file="index.html",options={}) {
  const {query="",fixture=null,...browserOptions}=options;
  const context=await browser.newContext({viewport:{width:1440,height:1000},offline:true,reducedMotion:"reduce",...browserOptions});
  if(fixture) await context.addInitScript(config=>{
    let source;
    Object.defineProperty(window,"atlasData",{
      get(){return source;},
      set(next){
        if(config==="missing-library") for(const authority of next.authorities){
          authority.values.ra1_cullib=null;
          authority.statuses.ra1_cullib=authority.code==="E09000026" ? "suppressed" : "not-applicable";
        }
        if(config==="zero-finance"){
          const reference=next.authorities.find(a=>a.code==="E09000026");
          reference.values.ra1_revenuetot=0;
          for(const item of next.meta.fundingLines) reference.values[item.id]=0;
        }
        source=next;
      }
    });
  },fixture);
  const page=await context.newPage(),errors=[],requests=[];
  page.on("pageerror",error=>errors.push(error.message));
  page.on("request",request=>{if(request.url().startsWith("http"))requests.push(request.url());});
  await page.goto(locationFor(file,query));
  if(browserOptions.javaScriptEnabled!==false) await page.waitForFunction(()=>Boolean(window.atlasAudit));
  return {context,page,errors,requests};
}
async function major(page,label,enhanced=true) {
  await page.getByRole("navigation",{name:"Major sections",exact:true}).getByRole("link",{name:label,exact:true}).click();
  if(enhanced)await page.waitForFunction(()=>Boolean(window.atlasAudit));
}
async function library(page,enhanced=true) {
  await page.locator('.directory-entry a[href*="ra1_cullib.html"]').click();
  if(enhanced)await page.waitForFunction(()=>Boolean(window.atlasAudit));
}
const metricSelect=page=>page.locator("[data-ledger-metric]").first();

test("icon-only theme button has action labels, keyboard/touch round-trips and cross-document URL persistence",async()=>{
  for(const [width,initial] of [[1440,"light"],[390,"dark"]]){
    const {page,context,errors,requests}=await open("index.html",{
      viewport:{width,height:1000},hasTouch:width===390,
      query:`peers=E09000027,E09000029&metric=resident&scoutTheme=${initial}`
    });
    const button=page.locator("#theme-toggle");
    async function verify(theme){
      const action=theme==="dark" ? "Use light theme" : "Use dark theme";
      assert.equal(await page.locator("html").getAttribute("data-theme"),theme);
      assert.equal(await page.getByRole("button",{name:action,exact:true}).count(),1);
      assert.equal(await button.getAttribute("title"),action);
      assert.equal((await button.innerText()).trim(),"");
      assert.equal(await button.locator("svg:visible").count(),1);
      assert.equal(await button.locator("svg:visible").getAttribute("data-theme-icon"),theme==="dark" ? "sun" : "moon");
      const box=await button.boundingBox();
      assert.ok(box.width>=44 && box.width<=48 && box.height>=44 && box.height<=48);
      const contrast=await button.evaluate(el=>{
        const luminance=colour=>colour.match(/\d+(\.\d+)?/g).slice(0,3).map(Number).map(n=>{
          n/=255;return n<=.04045 ? n/12.92 : ((n+.055)/1.055)**2.4;
        }).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);
        const styles=getComputedStyle(el),foreground=luminance(styles.color),background=luminance(styles.backgroundColor);
        return (Math.max(foreground,background)+.05)/(Math.min(foreground,background)+.05);
      });
      assert.ok(contrast>=3);
      const params=new URL(page.url()).searchParams;
      assert.equal(params.get("scoutTheme"),theme);
      assert.equal(params.get("peers"),"E09000027,E09000029");
      assert.equal(params.get("metric"),await page.locator("#shared-metric").inputValue());
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    }
    await verify(initial);
    await button.focus();
    assert.equal(await button.evaluate(el=>getComputedStyle(el).outlineStyle),"solid");
    const opposite=initial==="dark" ? "light" : "dark";
    await page.keyboard.press("Enter");
    await verify(opposite);
    await page.keyboard.press("Space");
    await verify(initial);
    if(width===390)await button.tap();else await button.click();
    await verify(opposite);
    await library(page);
    await verify(opposite);
    assert.equal(await page.locator(".service tbody tr").count(),3);
    await page.reload();
    await page.waitForFunction(()=>Boolean(window.atlasAudit));
    await verify(opposite);
    await page.selectOption("#shared-metric","absolute");
    await verify(opposite);
    await major(page,"Overview");
    await verify(opposite);
    assert.deepEqual(errors,[]);
    assert.deepEqual(requests,[]);
    await context.close();
  }
});

test("comparison panel supports visible search, keyboard labels, truthful presets, compact removal and cross-page state on desktop/mobile",async()=>{
  const outside=data.authorities.find(a=>a.name==="Adur").code;
  for(const width of [1440,390]){
    const {page,context,errors,requests}=await open("index.html",{
      viewport:{width,height:844},hasTouch:width===390,query:`scoutTheme=${width===390 ? "dark" : "light"}`
    });
    const search=page.getByRole("searchbox",{name:"Compare with",exact:true});
    const checked=()=>page.locator('input[name="comparison"]:checked').evaluateAll(inputs=>inputs.map(input=>input.value));
    async function checkCount(count){
      assert.equal(await page.locator("#selected-count").textContent(),`${count} comparison ${count===1 ? "council" : "councils"} selected.`);
      assert.equal((await checked()).length,count);
      assert.equal(await page.locator('input[name="comparison"][value="E09000026"]').count(),0);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    }
    assert.match(await page.locator(".comparison-reference").textContent(),/Comparing Redbridge/);
    assert.equal(await page.locator("#focus-council").count(),0);
    assert.equal(await page.locator("#comparison-controls #peer-group").count(),0);
    assert.equal(await page.locator("#comparison-options").isVisible(),true);
    assert.equal(await search.getAttribute("autocomplete"),"off");
    assert.equal(await search.getAttribute("name"),"comparison-search");
    assert.ok((await search.boundingBox()).height>=44);
    await checkCount(1);
    await search.fill("Richmond");
    assert.equal(await page.locator(".comparison-option:visible").count(),1);
    await page.locator(".comparison-option:visible").click();
    await checkCount(2);
    await page.locator(".comparison-option:visible").click();
    await checkCount(1);
    await page.locator(".comparison-option:visible").click();
    await checkCount(2);
    await search.fill("Sutton");
    await search.focus();
    await page.keyboard.press("Tab");
    assert.equal(await page.locator(".selection-skip").evaluate(el=>el===document.activeElement),true);
    await page.keyboard.press("Tab");
    const sutton=page.locator('input[name="comparison"][value="E09000029"]');
    assert.equal(await sutton.evaluate(el=>el===document.activeElement),true);
    assert.equal(await sutton.evaluate(el=>getComputedStyle(el).outlineStyle),"solid");
    const box=await sutton.boundingBox(),header=await page.locator(".masthead").boundingBox();
    assert.ok(box.y>=header.y+header.height && box.y+box.height<=844);
    await page.keyboard.press("Space");
    await checkCount(3);
    assert.match(await page.locator("#comparison-result-count").textContent(),/1 matching authority; 1 selected/);
    await page.evaluate(()=>{
      window.selectionAnnouncements=[];
      new MutationObserver(records=>window.selectionAnnouncements.push(...records.map(record=>record.type)))
        .observe(document.getElementById("selected-count"),{childList:true,subtree:true,characterData:true});
    });
    const beforeSearch=new URL(page.url()).searchParams.get("peers");
    await search.fill("ZZZ-no-such-council");
    assert.equal(await page.locator("#comparison-no-results").isVisible(),true);
    assert.equal(await page.locator("#comparison-options").isVisible(),false);
    assert.match(await page.locator("#comparison-result-count").textContent(),/^0 matching/);
    assert.equal(new URL(page.url()).searchParams.get("peers"),beforeSearch);
    assert.deepEqual(await page.evaluate(()=>window.selectionAnnouncements),[]);
    await page.getByRole("button",{name:"Remove Richmond upon Thames",exact:true}).click();
    await checkCount(2);
    assert.ok(await page.evaluate(()=>Boolean(document.activeElement.dataset.remove)));
    assert.equal(await page.locator("#comparison-no-results").isVisible(),true);
    await page.locator("#all-london").click();
    await checkCount(32);
    assert.equal(await search.inputValue(),"");
    assert.equal(await page.locator("#all-london").getAttribute("aria-pressed"),"true");
    assert.equal(await page.locator("#all-london").getAttribute("data-selection-state"),"all");
    assert.match(await page.locator("#london-preset-status").textContent(),/^All 32 London comparison councils selected\.$/);
    assert.equal(await page.locator("#selected-comparisons").getAttribute("open"),null);
    assert.equal(await page.locator("#selection-colours [data-remove]").count(),32);
    const list=await page.locator("#comparison-options").evaluate(el=>({height:el.clientHeight,content:el.scrollHeight}));
    assert.ok(list.height<=352 && list.content>list.height);
    assert.match(await page.locator('.comparison-option:has(input[value="E09000001"])').textContent(),/Different responsibilities/);
    assert.match(await page.locator('.comparison-option:has(input[value="E09000011"])').textContent(),/Budget not returned/);
    assert.match(await page.locator("#total-benchmark").textContent(),/30 valid peers/);
    const allLondonBenchmark=await page.locator("#total-benchmark").textContent();
    await search.fill("Adur");
    await page.locator(".comparison-option:visible").click();
    await checkCount(33);
    assert.equal(await page.locator("#all-london").getAttribute("aria-pressed"),"false");
    assert.equal(await page.locator("#all-london").getAttribute("data-selection-state"),"partial");
    assert.match(await page.locator("#london-preset-status").textContent(),/All 32.*1 outside London/);
    assert.equal(await page.locator("#total-benchmark").textContent(),allLondonBenchmark);
    assert.ok((await checked()).includes(outside));
    await page.locator("#all-london").click();
    assert.ok(!(await checked()).includes(outside));
    await page.locator("#selected-comparisons > summary").click();
    await page.getByRole("button",{name:"Remove Sutton",exact:true}).click();
    await checkCount(31);
    assert.equal(await page.locator("#selected-comparisons").getAttribute("open"),"");
    assert.equal(await sutton.isChecked(),false);
    assert.equal(await page.locator("#all-london").getAttribute("aria-pressed"),"false");
    assert.match(await page.locator("#london-preset-status").textContent(),/^31 of 32/);
    await page.locator("#clear-comparisons").click();
    await checkCount(0);
    assert.equal(await search.evaluate(el=>el===document.activeElement),true);
    assert.equal(await page.locator("#clear-comparisons").isDisabled(),true);
    assert.equal(await page.locator("#selected-empty").isVisible(),true);
    assert.equal(new URL(page.url()).searchParams.get("peers"),"");
    assert.match(await page.locator("#selection-status").textContent(),/no peer benchmark/);
    await page.locator("#reset-comparisons").click();
    await checkCount(1);
    assert.deepEqual(await checked(),[forest]);
    await page.getByRole("button",{name:"Remove Waltham Forest",exact:true}).click();
    await checkCount(0);
    assert.equal(await search.evaluate(el=>el===document.activeElement),true);
    await page.locator("#reset-comparisons").click();
    await search.fill("Richmond");
    await page.locator(".comparison-option:visible").click();
    const selectedBeforeBrowse=new URL(page.url()).searchParams.get("peers");
    const benchmarkBeforeBrowse=await page.locator("#total-benchmark").textContent();
    for(const group of ["single","same","councils","all","london"]){
      await page.selectOption("#peer-group",group);
      assert.equal(new URL(page.url()).searchParams.get("peers"),selectedBeforeBrowse);
      assert.equal(await page.locator("#total-benchmark").textContent(),benchmarkBeforeBrowse);
    }
    await page.selectOption("#shared-metric","absolute");
    assert.ok((await page.locator("[data-current-metric]").allTextContents()).every(text=>text==="Total budget (£m)"));
    await page.locator("#theme-toggle").click();
    const theme=await page.locator("html").getAttribute("data-theme");
    await major(page,"Funding");
    await checkCount(2);
    assert.equal(await page.locator("#funding-table [data-funding-authority]").count(),3);
    assert.equal(await page.locator("#shared-metric").inputValue(),"absolute");
    await major(page,"Services");
    await library(page);
    await checkCount(2);
    assert.equal(await page.locator(".service tbody tr").count(),3);
    assert.equal(await metricSelect(page).inputValue(),"absolute");
    await metricSelect(page).selectOption("resident");
    assert.equal(await page.locator("#shared-metric").inputValue(),"resident");
    await page.selectOption("#shared-metric","roads");
    assert.match(await page.locator("#shared-metric-help").textContent(),/^Unavailable for this service/);
    await page.reload();
    await page.waitForFunction(()=>Boolean(window.atlasAudit));
    await checkCount(2);
    assert.equal(new URL(page.url()).searchParams.get("peers"),selectedBeforeBrowse);
    assert.equal(await page.locator("#shared-metric").inputValue(),"roads");
    assert.equal(await page.locator("html").getAttribute("data-theme"),theme);
    assert.deepEqual(errors,[]);
    assert.deepEqual(requests,[]);
    await context.close();
  }
});

test("overview is a real smaller directory, not a hidden full ledger; precise totals remain",async()=>{
  const {page,context,errors,requests}=await open();
  assert.equal(await page.locator(".service").count(),0);
  assert.equal(await page.locator(".directory-entry").count(),129);
  assert.equal(await page.locator("#benchmark-table tbody tr").count(),129);
  assert.equal(await page.locator("#total .hero-number .number").textContent(),"£787.766m");
  assert.match(await page.locator("#total-benchmark").textContent(),/1 valid peers/);
  assert.match(await page.locator("#roads-formula").textContent(),/1,718,000.*36 \+ 295.*5,190/s);
  assert.match(await page.locator("#explorer-caption").textContent(),/31 of 32 peer observations/);
  assert.equal(await page.locator("#story-chart svg").count(),1);
  await page.fill("#directory-search","library");
  assert.equal(await page.locator(".directory-entry:visible").count(),1);
  await library(page);
  assert.match(new URL(page.url()).pathname,/services\/ra1_cullib.html$/);
  assert.match(await page.locator("h1").textContent(),/Library service/);
  assert.equal(await page.locator(".service > details[open]").count(),1);
  assert.deepEqual(errors,[]);
  assert.deepEqual(requests,[]);
  await context.close();
});

test("funding comes before spending, reconciles on its own document and keeps definitions",async()=>{
  const {page,context,errors}=await open();
  await major(page,"Funding");
  assert.match(new URL(page.url()).pathname,/funding.html$/);
  assert.equal(await page.locator("#funding .hero-number .number").textContent(),"£167.968m");
  assert.match(await page.locator("#funding-cards").textContent(),/477\.529/);
  const reference=page.locator(`[data-funding-authority="${focus}"]`);
  assert.match(await reference.locator('[data-funding-line="ra1_ctrtot"]').textContent(),/167\.968.*23\.0%/s);
  assert.match(await reference.locator('[data-funding-line="ra1_appresunall"]').textContent(),/−£20\.000m.*[-−]2\.7%/s);
  assert.match(await reference.locator('[data-funding-line="ra1_grantpol"]').textContent(),/£0\.000m.*0\.0%/s);
  assert.match(await reference.textContent(),/difference.*£0\.000m/s);
  assert.match(await page.locator("#capitalisation-context").textContent(),/−£70\.001m.*RA 868/);
  assert.match(await page.locator("#funding").textContent(),/not cash already collected/);
  assert.match(await page.locator("#funding").textContent(),/Actual council-tax receipts.*not imported/s);
  assert.equal(await page.locator(".service").count(),0);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("one, multiple and empty selections synchronize funding, service, URL and reset",async()=>{
  const {page,context,errors}=await open("funding.html");
  await page.check('input[name="comparison"][value="E09000027"]');
  assert.equal(await page.locator("#funding-table [data-funding-authority]").count(),3);
  await page.selectOption("#shared-metric","absolute");
  await major(page,"Services");
  await library(page);
  assert.equal(await page.locator(".service tbody tr").count(),3);
  assert.equal(await metricSelect(page).inputValue(),"absolute");
  assert.equal(await page.locator("#spending-funding-context [data-council]").count(),3);
  assert.match(await page.locator("[data-benchmark]").textContent(),/2 valid peers/);
  await page.getByRole("button",{name:"Remove Waltham Forest",exact:true}).click();
  assert.equal(await page.locator(".service tbody tr").count(),2);
  assert.match(await page.locator("[data-benchmark]").textContent(),/direct peer/);
  await page.locator("#clear-comparisons").click();
  assert.equal(new URL(page.url()).searchParams.get("peers"),"");
  assert.equal(await page.locator(".service tbody tr").count(),1);
  assert.match(await page.locator("[data-benchmark]").textContent(),/0 valid selected borough peers/);
  await page.reload();
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.equal(await page.locator(".service tbody tr").count(),1);
  await page.locator("#reset-comparisons").click();
  assert.equal(new URL(page.url()).searchParams.get("peers"),forest);
  assert.equal(await page.locator(".service tbody tr").count(),2);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("All London membership and excluded responsibilities survive links, reload and opening a new tab",async()=>{
  const {page,context,errors}=await open();
  await page.locator("#all-london").click();
  await page.selectOption("#shared-metric","absolute");
  await page.locator("#theme-toggle").click();
  const selected=await page.locator('input[name="comparison"]:checked').evaluateAll(inputs=>inputs.map(input=>input.value));
  assert.deepEqual(new Set([focus,...selected]),new Set(london));
  assert.equal(selected.length,32);
  assert.match(await page.locator("#comparison-coverage").textContent(),/City of London.*different responsibilities/);
  assert.match(await page.locator("#selection-status").textContent(),/1 selected return is missing/);
  assert.match(await page.locator("#total-benchmark").textContent(),/30 valid peers/);
  const href=await page.locator('.directory-entry a[href*="ra1_cullib.html"]').getAttribute("href");
  const other=await context.newPage();
  await other.goto(new URL(href,page.url()).href);
  await other.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.equal(await other.locator(".service tbody tr").count(),33);
  assert.equal(await other.locator('[data-chart-authority="E09000011"] rect[data-council]').count(),0);
  assert.equal(await other.locator("html").getAttribute("data-theme"),"dark");
  assert.equal(await metricSelect(other).inputValue(),"absolute");
  assert.match(await other.locator("[data-benchmark]").textContent(),/30 valid peers/);
  await other.reload();
  assert.equal(await other.locator(".service tbody tr").count(),33);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("metric, empty set, citations, breadcrumbs and back/forward work on actual file URLs",async()=>{
  const {page,context,errors}=await open("services\\ra1_transrdsmnt.html",{query:"peers=&metric=roads&scoutTheme=dark"});
  assert.equal(await metricSelect(page).inputValue(),"roads");
  assert.match(await page.locator(".service table").textContent(),/5,190/);
  await metricSelect(page).selectOption("resident");
  assert.equal(new URL(page.url()).searchParams.get("metric"),"resident");
  await metricSelect(page).selectOption("roads");
  await major(page,"Funding");
  assert.equal(new URL(page.url()).searchParams.get("metric"),"roads");
  assert.equal(new URL(page.url()).searchParams.get("peers"),"");
  await major(page,"Methods / sources");
  assert.match(new URL(page.url()).pathname,/methodology.html$/);
  await page.goBack();
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.match(new URL(page.url()).pathname,/funding.html$/);
  await page.goBack();
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.match(new URL(page.url()).pathname,/ra1_transrdsmnt.html$/);
  assert.equal(await metricSelect(page).inputValue(),"roads");
  await page.goForward();
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  await major(page,"Services");
  await library(page);
  assert.equal(await metricSelect(page).inputValue(),"roads");
  assert.equal(await page.locator("[data-chart-unavailable]").count(),1);
  assert.match(await page.locator(".service table").textContent(),/No eligible denominator/);
  assert.match(await page.locator(".service table").textContent(),/Not an eligible road-maintenance line/);
  await page.locator(".service a.citation").first().click();
  assert.match(new URL(page.url()).pathname,/methodology.html$/);
  assert.match(new URL(page.url()).hash,/^#source-/);
  assert.equal(new URL(page.url()).searchParams.get("metric"),"roads");
  assert.equal(await page.locator("html").getAttribute("data-theme"),"dark");
  assert.deepEqual(errors,[]);
  await context.close();
});

test("previous/next service documents and browser history keep selected state",async()=>{
  const {page,context,errors}=await open("services\\ra1_cullib.html",{query:"peers=E09000027,E09000029&metric=resident"});
  const original=page.url();
  await page.locator('a[rel="next"]').click();
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.equal(await page.locator(".service").count(),1);
  assert.equal(await page.locator(".service tbody tr").count(),3);
  assert.equal(new URL(page.url()).searchParams.get("peers"),"E09000027,E09000029");
  await page.locator('a[rel="prev"]').click();
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.equal(page.url(),original);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("overview filters, theme directory and detail links retain the exact benchmark",async()=>{
  const {page,context,errors}=await open();
  await page.selectOption("#benchmark-filter","below");
  await page.selectOption("#benchmark-sort","below");
  const deltas=await page.locator("#benchmark-table [data-difference]").evaluateAll(els=>els.map(el=>Number(el.dataset.difference)));
  assert.ok(deltas.length>0 && deltas.every((n,i)=>n<0 && (i===0 || n>=deltas[i-1])));
  const row=page.locator("#benchmark-table tbody tr").first();
  const delta=await row.locator("[data-difference]").getAttribute("data-difference");
  await row.locator("th a").click();
  assert.equal(await page.locator("[data-benchmark-delta]").getAttribute("data-benchmark-delta"),delta);
  await major(page,"Services");
  await page.selectOption("#shared-metric","roads");
  await page.selectOption("#benchmark-filter","available");
  assert.equal(await page.locator("#benchmark-table tbody tr").count(),3);
  await page.selectOption("#directory-group",data.fields.find(f=>f.id==="ra1_cullib").group);
  const entries=await page.locator(".directory-entry:visible").count();
  assert.ok(entries>0 && entries<129);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("exhaustive: all 129 service documents and 192 appendix lines have accurate charts, tables and benchmarks in 645 lenses",async()=>{
  const {page,context,errors,requests}=await open("index.html",{query:selectedQuery("absolute")});
  const summary={};
  for(const metric of ["absolute","resident"]){
    await page.selectOption("#shared-metric",metric);
    summary[metric]=await page.locator("#benchmark-table tbody tr").evaluateAll(rows=>Object.fromEntries(rows.map(row=>[row.dataset.benchmarkRow,row.querySelector("[data-difference]").dataset.difference])));
  }
  let charts=0,observations=0,summaryChecks=0;
  const problems=[];
  const pages=manifest.documents.filter(doc=>doc.kind==="service");
  pages.push(manifest.documents.find(doc=>doc.kind==="accounting"));
  for(const doc of pages){
    await page.goto(locationFor(doc.path,selectedQuery("absolute")));
    await page.waitForFunction(()=>Boolean(window.atlasAudit));
    const result=await page.evaluate(expectedSummary=>{
      const source=window.atlasData,reference=source.authorities.find(a=>a.code==="E09000026");
      const selected=source.authorities.filter(a=>a.class==="LB");
      const failures=[];let charts=0,observations=0,summaryChecks=0;
      const numeric=n=>typeof n==="number" && Number.isFinite(n);
      const value=(a,f,lens)=>{
        const n=a.values[f.id];if(!numeric(n))return null;
        if(lens==="resident")return a.population?.value>0 ? n*1000/a.population.value : null;
        if(lens==="roads")return f.denominator.key==="roads" && a.roads?.value>0 ? n*1000/a.roads.value : null;
        return n/1000;
      };
      const money=(n,lens)=>!numeric(n) ? "Not available" : (n<0?"−":"")+"£"+Math.abs(n).toLocaleString("en-GB",{minimumFractionDigits:lens==="absolute"?3:0,maximumFractionDigits:lens==="absolute"?3:0})+(lens==="absolute"?"m":"");
      const close=(x,y)=>numeric(x) && numeric(y) && Math.abs(x-y)<=Math.max(1,Math.abs(y))*1e-11;
      for(const lens of ["absolute","resident","roads"]){
        const sections=[...document.querySelectorAll(".service")].filter(section=>lens!=="roads" || source.fields.find(f=>"line-"+f.id===section.id).denominator.key==="roads");
        if(!sections.length)continue;
        const selector=document.querySelector("#shared-metric");
        selector.value=lens;selector.dispatchEvent(new Event("change"));
        for(const section of sections){
          const f=source.fields.find(item=>"line-"+item.id===section.id),details=section.querySelector("details");
          details.open=true;details.dispatchEvent(new Event("toggle"));
          charts++;
          const container=section.querySelector("[data-ledger-chart]"),svg=container.querySelector("svg");
          const tableRows=[...section.querySelectorAll("tbody tr")];
          if(tableRows.length!==selected.length)failures.push(f.id+" table count");
          for(const authority of selected){
            const n=value(authority,f,lens),row=tableRows.find(row=>row.querySelector(`[data-council="${authority.code}"]`));
            const chartRow=container.querySelector(`[data-chart-authority="${authority.code}"]`);
            const bar=chartRow?.querySelector("rect[data-council]");
            observations++;
            if(!row) {failures.push(f.id+" missing table authority "+authority.code);continue;}
            const cells=row.querySelectorAll("td");
            if(!cells[0].textContent.includes(money(numeric(authority.values[f.id]) ? authority.values[f.id]/1000 : null,"absolute"))) failures.push(f.id+" numerator "+authority.code);
            if(numeric(n)){
              if(!chartRow || !close(Number(chartRow.dataset.chartValue),n))failures.push(f.id+" chart numeric "+authority.code);
              if(!cells[2].textContent.includes(money(n,lens)))failures.push(f.id+" table metric "+authority.code);
              if(!bar)failures.push(f.id+" missing bar "+authority.code);
              if(n===0 && Number(bar?.getAttribute("width"))!==0)failures.push(f.id+" zero bar width");
              if(n<0){
                const baseline=svg.querySelector('line[style*="stroke-width:1.5"]:not([data-benchmark-value])');
                if(!close(Number(bar.getAttribute("x"))+Number(bar.getAttribute("width")),Number(baseline.getAttribute("x1"))))failures.push(f.id+" negative baseline");
              }
            }else if(bar || chartRow?.dataset.chartValue)failures.push(f.id+" fabricated missing bar");
          }
          const eligible=f.kind==="service" || f.kind==="theme" || f.id==="ra1_servicetot";
          const peerValues=eligible ? selected.filter(a=>a.code!==reference.code && a.code!=="E09000001").map(a=>value(a,f,lens)).filter(numeric).sort((a,b)=>a-b) : [];
          const m=Math.floor(peerValues.length/2),median=peerValues.length ? (peerValues.length%2 ? peerValues[m] : (peerValues[m-1]+peerValues[m])/2) : null;
          const own=eligible ? value(reference,f,lens) : null,delta=numeric(own)&&numeric(median) ? own-median : null;
          const note=section.querySelector("[data-benchmark]"),line=container.querySelector("[data-benchmark-value]");
          if(note.dataset.benchmarkPeers!==String(peerValues.length))failures.push(f.id+" peer count");
          if(numeric(delta) ? !close(Number(note.dataset.benchmarkDelta),delta) : note.dataset.benchmarkDelta!=="")failures.push(f.id+" delta");
          if(numeric(median) ? !line || !close(Number(line.dataset.benchmarkValue),median) : Boolean(line))failures.push(f.id+" benchmark line");
          if(f.kind==="service" && lens!=="roads"){
            if(note.dataset.benchmarkDelta!==expectedSummary[lens][f.id])failures.push(f.id+" overview/detail mismatch");
            summaryChecks++;
          }
          if(numeric(delta) && !note.textContent.includes(money(delta,lens)))failures.push(f.id+" displayed difference");
          const ownBar=container.querySelector('rect[data-council="E09000026"]');
          if(ownBar && getComputedStyle(ownBar).fill!=="rgb(148, 39, 37)")failures.push(f.id+" Redbridge colour");
          if(!svg && !container.querySelector("[data-chart-unavailable]"))failures.push(f.id+" no chart or unavailable state");
          for(const citation of section.querySelectorAll("a.citation")){
            const target=new URL(citation.href);
            if(!target.pathname.endsWith("/methodology.html") || !target.hash.startsWith("#source-"))failures.push(f.id+" source route");
          }
          if(section.querySelector("[data-ledger-metric]").value!==lens)failures.push(f.id+" metric control");
          details.open=false;details.dispatchEvent(new Event("toggle"));
          if(section.querySelector("[data-ledger-chart] svg"))failures.push(f.id+" collapsed SVG retained");
        }
      }
      return {charts,observations,summaryChecks,failures:failures.slice(0,100)};
    },summary);
    charts+=result.charts;observations+=result.observations;summaryChecks+=result.summaryChecks;problems.push(...result.failures);
  }
  assert.equal(charts,645);
  assert.equal(observations,21285);
  assert.equal(summaryChecks,258);
  assert.deepEqual(problems,[]);
  assert.deepEqual(errors,[]);
  assert.deepEqual(requests,[]);
  await context.close();
});

test("all London financing shares and zero/null year states stay source-consistent",async()=>{
  const {page,context,errors}=await open("funding.html",{query:selectedQuery("resident")});
  const result=await page.evaluate(()=>{
    const source=window.atlasData,failures=[];let shares=0;
    const number=n=>typeof n==="number" && Number.isFinite(n);
    const money=n=>number(n) ? (n<0?"−":"")+"£"+(Math.abs(n)/1000).toLocaleString("en-GB",{minimumFractionDigits:3,maximumFractionDigits:3})+"m" : "Not available";
    for(const authority of source.authorities.filter(a=>a.class==="LB")){
      const table=document.querySelector(`[data-funding-authority="${authority.code}"]`);
      for(const item of source.meta.fundingLines){
        const n=number(authority.values[item.id]) ? authority.values[item.id]*item.sign : null,total=authority.values.ra1_revenuetot;
        const cells=table.querySelector(`[data-funding-line="${item.id}"]`).querySelectorAll("td");
        const share=number(n) && number(total) && total!==0 ? (n/total*100).toFixed(1)+"%" : "Not available";
        if(!cells[0].textContent.includes(money(n)) || !cells[2].textContent.includes(share))failures.push(authority.name+" "+item.id);
        shares++;
      }
      if(!table.textContent.includes("2026–27"))failures.push("wrong year "+authority.code);
    }
    return {shares,failures};
  });
  assert.deepEqual(result,{shares:429,failures:[]});
  assert.deepEqual(errors,[]);
  await context.close();
});

test("negative net income, reported zero and missing returns never become clipped or invented bars",async()=>{
  const {page,context,errors}=await open("services\\ra1_transprk.html",{query:selectedQuery("absolute")});
  assert.match(await page.locator(".service table").textContent(),/−£17\.984m/);
  const reference=page.locator('[data-chart-authority="E09000026"]');
  assert.equal(await reference.getAttribute("data-chart-value"),"-17.984");
  assert.ok(Number(await reference.locator("rect[data-council]").getAttribute("width"))>0);
  assert.equal(await page.locator('[data-chart-authority="E09000011"] rect[data-council]').count(),0);
  assert.match(await page.locator(".service table").textContent(),/Not returned \[x\]/);
  assert.match(await page.locator("[data-benchmark]").textContent(),/percentage not reported: benchmark is zero or net income/);
  const zeroField=data.fields.find(f=>f.kind==="service" && data.authorities.some(a=>a.class==="LB" && a.values[f.id]===0));
  await page.goto(locationFor(manifest.fieldPaths[zeroField.id],selectedQuery("absolute")));
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  const zero=await page.evaluate(()=>{
    const groups=[...document.querySelectorAll("[data-chart-authority]")];
    return groups.filter(group=>group.dataset.chartValue==="0").map(group=>Number(group.querySelector("rect[data-council]").getAttribute("width")));
  });
  assert.ok(zero.length>0 && zero.every(width=>width===0));
  assert.deepEqual(errors,[]);
  await context.close();
});

test("unavailable/suppressed/non-applicable fixtures retain tables and an explicit chart state",async()=>{
  const {page,context,errors}=await open("services\\ra1_cullib.html",{fixture:"missing-library"});
  assert.equal(await page.locator("[data-chart-unavailable]").count(),1);
  assert.equal(await page.locator(".service svg").count(),0);
  assert.match(await page.locator(".service table").textContent(),/Suppressed/);
  assert.match(await page.locator(".service table").textContent(),/Not applicable/);
  assert.match(await page.locator("[data-benchmark]").textContent(),/Insufficient comparison data/);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("zero funding denominator has no percentages or fabricated residual",async()=>{
  const {page,context,errors}=await open("funding.html",{fixture:"zero-finance"});
  const reference=page.locator('[data-funding-authority="E09000026"]');
  const percentages=await reference.locator('tbody tr[data-funding-line] td:last-child').allTextContents();
  assert.ok(percentages.every(text=>text==="Not available"));
  assert.doesNotMatch(await reference.textContent(),/Infinity|NaN/);
  assert.match(await reference.textContent(),/difference.*£0\.000m/s);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("no-JS offline fallback is readable across all document types with actual relative links",async()=>{
  const {page,context,requests}=await open("index.html",{javaScriptEnabled:false});
  assert.equal(await page.locator(".directory-entry").count(),129);
  assert.equal(await page.locator("#comparison-controls").isVisible(),false);
  await library(page,false);
  assert.match(await page.locator(".service table").textContent(),/5\.867m/);
  assert.equal(await page.locator(".service details").getAttribute("open"),"");
  await major(page,"Funding",false);
  assert.match(await page.locator("#funding-table").textContent(),/167\.968/);
  await page.goto(locationFor("accounting.html"));
  assert.equal(await page.locator(".service").count(),192);
  await page.goto(locationFor("methodology.html"));
  assert.equal(await page.locator(".sources li").count(),151);
  assert.equal(await page.locator("#report-ledger tbody tr").count(),33);
  assert.match(await page.locator("#methods").textContent(),/not three independent confirmations/);
  assert.deepEqual(requests,[]);
  await context.close();
});

test("mobile keyboard/touch, selected names, theme and reduced motion stay accessible",async()=>{
  const {page,context,errors}=await open("services\\ra1_cullib.html",{viewport:{width:390,height:844},hasTouch:true});
  await page.keyboard.press("Tab");
  assert.equal(await page.locator(".skip").evaluate(el=>el===document.activeElement),true);
  await page.keyboard.press("Enter");
  assert.equal(await page.locator("#content").evaluate(el=>el===document.activeElement),true);
  await page.fill("#comparison-search","Sutton");
  const checkbox=page.locator('input[name="comparison"][value="E09000029"]');
  await checkbox.focus();await page.keyboard.press("Space");
  assert.equal(await checkbox.isChecked(),true);
  assert.equal(await page.locator(".service tbody tr").count(),3);
  await page.getByRole("button",{name:"Remove Sutton",exact:true}).tap();
  assert.equal(await page.locator(".service tbody tr").count(),2);
  for(const theme of ["dark","light"]){
    if(await page.locator("html").getAttribute("data-theme")!==theme)await page.locator("#theme-toggle").tap();
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  }
  assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior),"auto");
  assert.deepEqual(errors,[]);
  await context.close();
});

test("verified council tokens and permission-aware names remain consistent across documents",async()=>{
  const {page,context,requests}=await open("services\\ra1_cullib.html",{query:selectedQuery("absolute")});
  await page.evaluate(()=>document.fonts.ready);
  for(const theme of ["light","dark"]){
    await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);
    const colours=await page.evaluate(()=>({
      data:window.atlasData.colours.E09000026.colour,
      token:getComputedStyle(document.documentElement).getPropertyValue("--cp-council-E09000026").trim(),
      markers:[...document.querySelectorAll('.council[data-council="E09000026"]')].map(el=>getComputedStyle(el,"::before").backgroundColor),
      fills:[...document.querySelectorAll('rect[data-council="E09000026"]')].map(el=>getComputedStyle(el).fill),
      fonts:document.fonts.check('800 24px "Barlow Condensed"')
    }));
    assert.equal(colours.data,"#942725");
    assert.equal(colours.token,"#942725");
    assert.ok(colours.fonts);
    assert.ok(colours.markers.length>0 && colours.fills.length>0);
    assert.ok([...colours.markers,...colours.fills].every(colour=>colour==="rgb(148, 39, 37)"));
    const contrasts=await page.locator(".breadcrumbs a,.document-neighbours a").evaluateAll(links=>{
      const rgb=s=>s.match(/\d+(\.\d+)?/g).slice(0,3).map(Number);
      const luminance=arr=>arr.map(n=>{n/=255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;}).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);
      const background=luminance(rgb(getComputedStyle(document.body).backgroundColor));
      return links.map(link=>{
        const foreground=luminance(rgb(getComputedStyle(link).color));
        return (Math.max(foreground,background)+.05)/(Math.min(foreground,background)+.05);
      });
    });
    assert.ok(contrasts.length>0 && contrasts.every(ratio=>ratio>=4.5));
  }
  assert.equal(await page.locator("img").count(),0);
  assert.equal(await page.locator('.comparison-reference [data-council="E09000026"]').getAttribute("data-logo-state"),"not-established");
  assert.deepEqual(requests,[]);
  await context.close();
});

test("service-to-explorer CSV uses the same selected metric and exact unrounded source values",async()=>{
  const {page,context,errors}=await open("services\\ra1_cullib.html",{acceptDownloads:true,query:selectedQuery("resident")});
  await page.locator('[data-explore="ra1_cullib"]').click();
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.match(new URL(page.url()).pathname,/index.html$/);
  assert.equal(await page.locator("#budget-line").inputValue(),"ra1_cullib");
  assert.equal(await page.locator("#shared-metric").inputValue(),"resident");
  await page.selectOption("#peer-group","all");
  assert.equal(await page.locator("#peer-table tbody tr").count(),415);
  const promise=page.waitForEvent("download");
  await page.locator("#download-data").click();
  const download=await promise,text=fs.readFileSync(await download.path(),"utf8");
  assert.match(text,/"2026-27"/);
  assert.match(text,/"5867"/);
  assert.match(text,new RegExp(String(5867*1000/321829).replace(".","\\.")));
  assert.match(text,/"E09000011".*"not-returned"/);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("story, progress, source navigation and back-to-top survive the shorter overview",async()=>{
  const {page,context,errors}=await open("index.html",{reducedMotion:"no-preference"});
  await page.locator('[data-story="1"]').click();
  assert.match(await page.locator("#story-chart-title").textContent(),/Education/);
  await page.locator('[data-story="3"]').click();
  assert.match(await page.locator("#story-table").textContent(),/−£17\.984m/);
  await page.locator("#services").scrollIntoViewIfNeeded();
  assert.ok(await page.locator("#reading-progress").evaluate(el=>el.value>0));
  await page.locator(".back-top").click();
  await page.waitForFunction(()=>window.scrollY===0);
  assert.equal(await page.locator("#reading-progress").evaluate(el=>Math.round(el.value)),0);
  await major(page,"Methods / sources");
  assert.equal(await page.locator(".sources li").count(),151);
  await page.fill("#report-search","Redbridge");
  assert.equal(await page.locator("#report-ledger tbody tr:visible").count(),1);
  await page.goto(locationFor("services\\ra1_transprk.html",selectedQuery("absolute")));
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  await page.locator(".ledger-figure").scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>getComputedStyle(document.querySelector(".ledger-figure")).opacity==="1");
  assert.equal(await page.locator(".service").evaluate(el=>el.classList.contains("will-reveal")),false);
  assert.deepEqual(errors,[]);
  await context.close();
});

test("invalid query state reports the rejected settings without creating fake councils",async()=>{
  const {page,context,errors}=await open("services\\ra1_cullib.html",{query:"peers=UNKNOWN,E09000031&metric=INVALID&line=missing&scoutTheme=INVALID"});
  assert.equal(await page.locator("#navigation-notice").isVisible(),true);
  assert.match(await page.locator("#navigation-notice").textContent(),/Unknown comparison authority/);
  assert.equal(await page.locator(".service tbody tr").count(),2);
  assert.equal(await metricSelect(page).inputValue(),"resident");
  assert.equal(await page.locator("html").getAttribute("data-theme"),"light");
  assert.ok(!new URL(page.url()).searchParams.get("peers").includes("UNKNOWN"));
  assert.deepEqual(errors,[]);
  await context.close();
});

test("axe WCAG 2.2 A/AA checks cover every document type, open charts, light/dark and mobile",async()=>{
  const {page,context,errors}=await open();
  const audits=[
    ["index.html","light",1440],["index.html","dark",390],
    ["funding.html","dark",1440],["services\\ra1_cullib.html","light",1440],
    ["services\\ra1_transprk.html","dark",390],["accounting.html","light",1440],
    ["methodology.html","light",390]
  ];
  const failures=[];
  for(const [file,theme,width] of audits){
    await page.setViewportSize({width,height:1000});
    await page.goto(locationFor(file,"scoutTheme="+theme));
    await page.waitForFunction(()=>Boolean(window.atlasAudit));
    if(file==="accounting.html"){
      await page.locator("#line-ra1_servicetot > details > summary").click();
      await page.waitForSelector("#line-ra1_servicetot svg");
    }
    await page.addScriptTag({path:axe});
    const results=await page.evaluate(()=>axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21a","wcag21aa","wcag22aa"]}}));
    failures.push(...results.violations.map(item=>({file,theme,width,id:item.id,nodes:item.nodes.map(node=>node.target)})));
    if(width===390)assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),file+" overflow");
  }
  assert.deepEqual(failures,[]);
  assert.deepEqual(errors,[]);
  await context.close();
});
