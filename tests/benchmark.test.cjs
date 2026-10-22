const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const stats = require("../src/benchmark.js");
const data = JSON.parse(fs.readFileSync("data\\processed\\atlas.json","utf8"));
const redbridge = data.authorities.find(a=>a.code==="E09000026");
const waltham = data.authorities.find(a=>a.code==="E09000031");
const field = data.fields.find(f=>f.id==="ra1_servicetot");

test("median: sorted, even, odd, empty, zero and negative values",()=>{
  assert.equal(stats.median([8,2,4]),4);
  assert.equal(stats.median([9,1,3,7]),5);
  assert.equal(stats.median([null,NaN]),null);
  assert.equal(stats.median([0,-4]),-2);
});
test("one peer is direct; focal and duplicate entries cannot enter benchmark",()=>{
  const result=stats.compare(redbridge,[redbridge,waltham,waltham],field,"resident");
  assert.equal(result.count,1);
  assert.equal(result.benchmark,waltham.values[field.id]*1000/waltham.population.value);
  assert.equal(result.delta,result.own-result.benchmark);
  assert.deepEqual(result.codes,[waltham.code]);
});
test("all London keeps City and missing entries in selection but not benchmark",()=>{
  const london=data.authorities.filter(a=>a.class==="LB");
  const result=stats.compare(redbridge,london,field,"resident");
  assert.equal(london.length,33);
  assert.equal(result.selectedCount,32);
  assert.equal(result.count,30);
  assert.equal(result.excludedResponsibility,1);
  assert.equal(result.missing,1);
  assert.ok(!result.codes.includes("E09000001"));
  assert.ok(!result.codes.includes("E09000011"));
  assert.ok(!result.codes.includes(redbridge.code));
});
test("other authority classes stay out even when a numeric value exists",()=>{
  const unlike=data.authorities.find(a=>a.class==="UA" && a.returned);
  const result=stats.compare(redbridge,[unlike],field,"absolute");
  assert.equal(result.count,0);
  assert.equal(result.benchmark,null);
  assert.equal(result.delta,null);
  assert.equal(result.excludedResponsibility,1);
});
test("no peers is an unavailable comparison, not a zero benchmark",()=>{
  const result=stats.compare(redbridge,[],field,"resident");
  assert.equal(result.benchmark,null);
  assert.equal(result.delta,null);
  assert.equal(result.percent,null);
});
test("zero and net-income benchmarks retain signed differences, suppress misleading percentage",()=>{
  assert.deepEqual(stats.difference(8,0),{delta:8,percent:null});
  assert.deepEqual(stats.difference(-5,-9),{delta:4,percent:null});
  assert.deepEqual(stats.difference(0,10),{delta:-10,percent:-100});
  assert.deepEqual(stats.difference(null,10),{delta:null,percent:null});
});
test("reported zero is valid but missing/suppressed/not-applicable values are not",()=>{
  const zero=structuredClone(waltham), missing=structuredClone(waltham);
  zero.values[field.id]=0; missing.values[field.id]=null;
  assert.equal(stats.compare(redbridge,[zero],field,"absolute").count,1);
  for(const status of ["not-returned","suppressed","not-applicable","missing"]){
    missing.statuses[field.id]=status;
    assert.equal(stats.compare(redbridge,[missing],field,"absolute").count,0);
  }
});
test("road-unit numerator conversion uses only eligible lines and positive joined miles",()=>{
  const maintenance=data.fields.find(f=>f.id==="ra1_transrdsmnt");
  assert.equal(stats.value(redbridge,maintenance,"roads"),1718000/331);
  assert.equal(stats.value(redbridge,field,"roads"),null);
  const noRoad=structuredClone(waltham); noRoad.roads={value:0};
  assert.equal(stats.compare(redbridge,[noRoad],maintenance,"roads").count,0);
});
test("missing population is not approximated or assigned zero",()=>{
  const missing=structuredClone(waltham); missing.population=null;
  assert.equal(stats.value(missing,field,"resident"),null);
  assert.equal(stats.compare(redbridge,[missing],field,"resident").count,0);
});
test("grant and reserve lines cannot become service-spending benchmarks",()=>{
  const grant=data.fields.find(f=>f.id==="sg_grantindsg");
  const result=stats.compare(redbridge,[waltham],grant,"absolute");
  assert.equal(result.service,false);
  assert.equal(result.count,0);
});

test("exhaustive: every authority and field has independently recomputed units/null states",()=>{
  for(const a of data.authorities) for(const f of data.fields){
    const n=a.values[f.id], numeric=typeof n==="number" && Number.isFinite(n);
    const absolute=numeric ? n/1000 : null;
    const resident=numeric && a.population?.value>0 ? n/(a.population.value/1000) : null;
    const roads=numeric && f.denominator.key==="roads" && a.roads?.value>0 ? n/(a.roads.value/1000) : null;
    for(const [metric,expected] of [["absolute",absolute],["resident",resident],["roads",roads]]){
      const actual=stats.value(a,f,metric);
      if(expected===null) assert.equal(actual,null,`${a.code}/${f.id}/${metric}`);
      else assert.ok(Math.abs(actual-expected)<=Math.max(1e-9,Math.abs(expected)*1e-12),`${a.code}/${f.id}/${metric}`);
    }
  }
});
test("exhaustive: all service/total/theme benchmark lenses, cohorts, distributions and rounding",()=>{
  const eligible=data.fields.filter(f=>f.kind==="service" || f.kind==="theme" || f.id==="ra1_servicetot");
  for(const cohort of [[],[waltham],data.authorities.filter(a=>a.class==="LB"),data.authorities]){
    for(const f of eligible) for(const metric of ["absolute","resident","roads"]){
      const independentValue=a=>{
        const n=a.values[f.id];
        if(typeof n!=="number" || !Number.isFinite(n)) return null;
        if(metric==="absolute") return n/1000;
        const denominator=metric==="resident" ? a.population?.value : f.denominator.key==="roads" ? a.roads?.value : null;
        return denominator>0 ? n*1000/denominator : null;
      };
      const peers=cohort.filter(a=>a.code!==redbridge.code && a.code!=="E09000001" && a.class==="LB").map(independentValue).filter(n=>n!==null).sort((a,b)=>a-b);
      const count=peers.length;
      const expected=count ? (peers[Math.floor((count-1)/2)]+peers[Math.ceil((count-1)/2)])/2 : null;
      const result=stats.compare(redbridge,cohort,f,metric);
      assert.equal(result.count,count,`${f.id}/${metric}`);
      assert.equal(result.benchmark,expected,`${f.id}/${metric}`);
      assert.equal(result.min,count ? peers[0] : null);
      assert.equal(result.max,count ? peers[count-1] : null);
      const own=independentValue(redbridge);
      assert.equal(result.delta,expected!==null && own!==null ? own-expected : null);
      const expectedPercent=expected>0 && own!==null ? (own/expected-1)*100 : null;
      if(expectedPercent===null) assert.equal(result.percent,null);
      else assert.ok(Math.abs(result.percent-expectedPercent)<1e-8);
      if(result.delta!==null) assert.ok(Math.abs(result.delta-Number(result.delta.toFixed(3)))<=.00050001);
    }
  }
});
test("exhaustive: every returned authority financing component and unrounded share reconciles",()=>{
  for(const a of data.authorities.filter(a=>a.returned)){
    const total=a.values.ra1_revenuetot;
    const contributions=data.meta.fundingLines.map(item=>a.values[item.id]*item.sign);
    assert.ok(contributions.every(Number.isFinite));
    assert.equal(contributions.reduce((sum,n)=>sum+n,0),total,a.code);
    if(total!==0) assert.ok(Math.abs(contributions.map(n=>100*n/total).reduce((sum,n)=>sum+n,0)-100)<1e-9,a.code);
  }
});
