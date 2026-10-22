(function (root) {
  "use strict";
  const finite = n => typeof n === "number" && Number.isFinite(n);
  function median(values) {
    const sorted = values.filter(finite).slice().sort((a,b) => a-b);
    const middle = Math.floor(sorted.length/2);
    return sorted.length ? (sorted.length%2 ? sorted[middle] : (sorted[middle-1]+sorted[middle])/2) : null;
  }
  function value(authority,field,metric) {
    const n = authority.values[field.id];
    if (!finite(n)) return null;
    if (metric === "resident") return authority.population?.value>0 ? n*1000/authority.population.value : null;
    if (metric === "roads") return field.denominator.key === "roads" && authority.roads?.value>0 ? n*1000/authority.roads.value : null;
    return n/1000;
  }
  function difference(reference,benchmark) {
    const delta = finite(reference) && finite(benchmark) ? reference-benchmark : null;
    return { delta, percent: finite(delta) && benchmark>0 ? delta/benchmark*100 : null };
  }
  function compare(reference,selected,field,metric) {
    const service = field.kind === "service" || field.kind === "theme" || field.id === "ra1_servicetot";
    const candidates = [...new Map(selected.map(a=>[a.code,a])).values()].filter(a=>a.code!==reference.code);
    const compatible = candidates.filter(a=>a.class==="LB" && a.code!=="E09000001");
    const valid = service ? compatible.filter(a=>finite(value(a,field,metric))) : [];
    const observations = valid.map(a=>value(a,field,metric));
    const benchmark = median(observations), own = service ? value(reference,field,metric) : null;
    return {
      service, own, benchmark, ...difference(own,benchmark),
      budgetMedian: median(valid.map(a=>a.values[field.id]/1000)),
      count: valid.length, selectedCount: candidates.length,
      excludedResponsibility: candidates.length-compatible.length,
      missing: compatible.length-valid.length,
      min: observations.length ? Math.min(...observations) : null,
      max: observations.length ? Math.max(...observations) : null,
      codes: valid.map(a=>a.code)
    };
  }
  const api = Object.freeze({ median,value,difference,compare });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.BudgetBenchmarks = api;
})(globalThis);
