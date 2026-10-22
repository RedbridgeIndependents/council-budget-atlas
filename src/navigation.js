(function (root) {
  "use strict";
  const focus = "E09000026";
  const metrics = ["absolute", "resident", "roads"];
  function parse(search, authorities, fields) {
    const params = new URLSearchParams(search), issues = [];
    const validCodes = new Set(authorities.map(a=>a.code)), validFields = new Set(fields.map(f=>f.id));
    const rawPeers = params.has("peers") ? params.get("peers").split(",").filter(Boolean) : ["E09000031"];
    const peers = [...new Set(rawPeers)].filter(code=>{
      if (code===focus) return false;
      if (validCodes.has(code)) return true;
      issues.push(`Unknown comparison authority omitted: ${code.slice(0,40)}.`);
      return false;
    });
    function option(key, allowed, fallback) {
      const value=params.get(key);
      if (value===null) return fallback;
      if (allowed.includes(value)) return value;
      issues.push(`Unsupported ${key} setting; using ${fallback===null ? "automatic theme" : fallback}.`);
      return fallback;
    }
    const line=params.get("line");
    if (line!==null && !validFields.has(line)) issues.push("Unknown budget line; using the published service total.");
    return {
      focus, peers, metric: option("metric",metrics,"resident"),
      group: option("group",["london","single","same","councils","all"],"london"),
      field: validFields.has(line) ? line : "ra1_servicetot",
      filter: option("filter",["all","above","below","available","missing"],"all"),
      sort: option("sort",["magnitude","above","below","name"],"magnitude"),
      story: Number(option("story",["0","1","2","3"],"0")),
      theme: option("scoutTheme",["light","dark"],null), issues
    };
  }
  function serialize(state) {
    const params = new URLSearchParams();
    params.set("peers",[...state.comparisons].filter(code=>code!==focus).join(","));
    params.set("metric",state.metric);
    params.set("group",state.peer);
    params.set("line",state.field);
    params.set("filter",state.filter);
    params.set("sort",state.sort);
    params.set("story",String(state.story));
    params.set("scoutTheme",state.theme);
    return params.toString();
  }
  function href(base,search) {
    const [path,anchor] = base.split("#",2);
    return path.split("?")[0]+"?"+search+(anchor===undefined ? "" : "#"+anchor);
  }
  const api=Object.freeze({parse,serialize,href,focus,metrics});
  if (typeof module!=="undefined" && module.exports) module.exports=api;
  else root.AtlasNavigation=api;
})(globalThis);
