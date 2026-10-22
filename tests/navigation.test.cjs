const {test}=require("node:test");
const assert=require("node:assert/strict");
const data=require("../data/processed/atlas.json");
const nav=require("../src/navigation.js");
const parse=search=>nav.parse(search,data.authorities,data.fields);
const state=result=>({comparisons:new Set(result.peers),metric:result.metric,peer:result.group,field:result.field,filter:result.filter,sort:result.sort,story:result.story,theme:result.theme || "light"});

test("URL defaults and explicitly empty comparisons are distinct",()=>{
  assert.deepEqual(parse("").peers,["E09000031"]);
  assert.equal(parse("").metric,"resident");
  assert.deepEqual(parse("?peers=").peers,[]);
  assert.deepEqual(parse("?peers=E09000026,E09000031,E09000031").peers,["E09000031"]);
});
test("every authority and supported metric round-trips without local storage",()=>{
  for(const metric of nav.metrics){
    const peers=data.authorities.map(a=>a.code).filter(code=>code!==nav.focus);
    const initial=parse("?peers="+peers.join(",")+"&metric="+metric+"&line=ra1_cullib&group=all&sort=below&filter=missing&story=3&scoutTheme=dark");
    assert.deepEqual(parse(nav.serialize(state(initial))),initial);
  }
});
test("All London is the actual 33-authority metadata set including City and Greenwich",()=>{
  const selected=data.authorities.filter(a=>a.class==="LB").map(a=>a.code);
  assert.equal(selected.length,33);
  const result=parse("?peers="+selected.join(","));
  assert.equal(result.peers.length,32);
  assert.ok(result.peers.includes("E09000001"));
  assert.ok(result.peers.includes("E09000011"));
  assert.ok(!result.peers.includes(nav.focus));
});
test("invalid URL settings are visibly reportable, not fabricated authority values",()=>{
  const result=parse("?peers=UNKNOWN,E09000031&metric=wrong&line=missing&group=wrong&sort=wrong&filter=wrong&scoutTheme=wrong");
  assert.deepEqual(result.peers,["E09000031"]);
  assert.equal(result.issues.length,7);
  assert.equal(result.field,"ra1_servicetot");
  assert.equal(result.metric,"resident");
});
test("relative document and fragment links retain canonical state and useful anchors",()=>{
  const query=nav.serialize(state(parse("?peers=&metric=roads&scoutTheme=dark")));
  for(const base of ["../funding.html","../methodology.html#source-1","#top","ra1_cullib.html?old=1#line-ra1_cullib"]){
    const href=nav.href(base,query), url=new URL(href,"file:///D:/atlas/services/ra1_transprk.html");
    assert.equal(url.searchParams.get("peers"),"");
    assert.equal(url.searchParams.get("metric"),"roads");
    assert.equal(url.searchParams.get("scoutTheme"),"dark");
    assert.equal(url.hash,base.includes("#") ? "#"+base.split("#")[1] : "");
    assert.ok(!url.searchParams.has("old"));
  }
});
