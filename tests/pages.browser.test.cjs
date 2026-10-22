const {test}=require("node:test");
const assert=require("node:assert/strict");
const {execFileSync}=require("node:child_process");
const fs=require("node:fs");
const http=require("node:http");
const path=require("node:path");
const {chromium}=require("@playwright/test");

test("packaged Pages website works over HTTP under its project prefix without exposing the checkout",{timeout:120000},async t=>{
  const root=path.resolve(__dirname,"..");
  execFileSync("python",[path.join(root,"scripts","package_site.py")],{cwd:root});
  const site=path.join(root,"_site"),prefix="/council-budget-atlas/";
  const types={".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",".css":"text/css; charset=utf-8"};
  const server=http.createServer((request,response)=>{
    const pathname=new URL(request.url,"http://localhost").pathname;
    const relative=pathname.startsWith(prefix) ? pathname.slice(prefix.length) || "index.html" : "";
    const file=path.resolve(site,relative);
    if(!relative || !file.startsWith(site+path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()){
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200,{"Content-Type":types[path.extname(file)] || "application/octet-stream"});
    response.end(fs.readFileSync(file));
  });
  await new Promise((resolve,reject)=>{
    server.once("error",reject);
    server.listen(0,"127.0.0.1",resolve);
  });
  let browser;
  t.after(async()=>{
    await browser?.close();
    server.closeAllConnections();
    await new Promise((resolve,reject)=>server.close(error=>error ? reject(error) : resolve()));
  });
  const base=`http://127.0.0.1:${server.address().port}${prefix}`;
  browser=await chromium.launch({headless:true,channel:process.env.ATLAS_BROWSER || "msedge"});
  const context=await browser.newContext({reducedMotion:"reduce"});
  const page=await context.newPage(),errors=[],failed=[],external=[];
  page.on("pageerror",error=>errors.push(error.message));
  page.on("requestfailed",request=>failed.push(request.url()));
  page.on("request",request=>{if(!request.url().startsWith(base))external.push(request.url());});
  await page.goto(base+"?peers=E09000027,E09000029&metric=resident&scoutTheme=dark");
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.equal(await page.locator("#selected-count").textContent(),"2 comparison councils selected.");
  await page.locator('.directory-entry a[href*="ra1_cullib.html"]').click();
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.equal(new URL(page.url()).pathname,prefix+"services/ra1_cullib.html");
  assert.equal(new URL(page.url()).searchParams.get("peers"),"E09000027,E09000029");
  assert.equal(await page.locator("html").getAttribute("data-theme"),"dark");
  await page.getByRole("button",{name:"Use light theme",exact:true}).click();
  await page.reload();
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.equal(await page.locator("html").getAttribute("data-theme"),"light");
  await page.getByRole("navigation",{name:"Major sections",exact:true}).getByRole("link",{name:"Funding",exact:true}).click();
  await page.waitForFunction(()=>Boolean(window.atlasAudit));
  assert.equal(new URL(page.url()).pathname,prefix+"funding.html");
  assert.equal(new URL(page.url()).searchParams.get("peers"),"E09000027,E09000029");
  assert.equal(await page.locator("#selected-count").textContent(),"2 comparison councils selected.");
  for(const file of [".git/config",".github/workflows/pages.yml","README.md","src/page.html","data/processed/atlas.json","scripts/build.py","package.json"]){
    assert.equal((await context.request.get(base+file)).status(),404,file);
  }
  const noScript=await browser.newContext({javaScriptEnabled:false});
  const fallback=await noScript.newPage();
  await fallback.goto(base+"services/ra1_cullib.html");
  assert.ok(await fallback.getByRole("heading",{level:1}).isVisible());
  assert.ok(await fallback.locator(".service table").isVisible());
  assert.match(await fallback.locator(".service table").textContent(),/5\.867m/);
  assert.deepEqual(errors,[]);
  assert.deepEqual(failed,[]);
  assert.deepEqual(external,[]);
});
