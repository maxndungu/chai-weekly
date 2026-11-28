/* Tea map page: a world map (or spinning globe) and blocks of world > region > country, all tied to one choice.
   Tap a country anywhere and the panel opens its production and, where it sells at an auction we keep, its prices.
   Data comes from window.TEA_MAP, filled by Jekyll from _data/ (see tea-map.html and _data/tea_map.yml).
   Nothing is estimated: a year with no figure stays blank. */
(function () {
  var D = window.TEA_MAP, root = document.getElementById("tmap");
  if (!D || !root || !window.d3 || !window.topojson) return;
  var $ = function (id) { return document.getElementById(id); };
  var NS = "http://www.w3.org/2000/svg";
  var reduceMotion = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var num = function (x) { return Math.round(x).toLocaleString("en-GB"); };
  var tonnes = function (t) { return t >= 1e6 ? (t / 1e6).toFixed(2) + "M t" : t >= 1e4 ? Math.round(t / 1e3) + "k t" : num(t) + " t"; };
  var share = function (a, b) { var p = 100 * a / b; return (p >= 10 ? p.toFixed(0) : p >= 1 ? p.toFixed(1) : p >= 0.1 ? p.toFixed(1) : "under 0.1") + "%"; };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var change = function (a, b) { var p = Math.round(100 * (a - b) / b); return "<span class='" + (p > 0 ? "up" : p < 0 ? "down" : "") + "'>" + (p > 0 ? "▲ " : p < 0 ? "▼ " : "▬ ") + Math.abs(p) + "%</span>"; };

  /* ---------- data ---------- */
  // One set of figures per measure; by, world and the words on the page follow the measure chosen.
  var M = { production: { by: {}, world: {} } }, names = {};
  D.production.forEach(function (r) {
    var t = +r.made_tea_t; if (!(t > 0)) return;
    if (r.iso3 === "WLD") { M.production.world[+r.year] = t; return; }
    (M.production.by[r.iso3] = M.production.by[r.iso3] || {})[+r.year] = t; names[r.iso3] = r.country;
  });
  var by = M.production.by, world = M.production.world;
  var WORDS = {
    production: { past: "grew", what: "Made tea", legend: "Made tea a year", of: "of the world's tea", count: "Countries growing tea", since: "Production", none: "No tea figure" },
    exports: { past: "exported", what: "Exported", legend: "Tea exported a year", of: "of the world's tea exports", count: "Countries exporting tea", since: "Exports", none: "No export figure" },
    imports: { past: "imported", what: "Imported", legend: "Tea imported a year", of: "of the world's tea imports", count: "Countries importing tea", since: "Imports", none: "No import figure" },
    consumption: { past: "drank", what: "Drunk", legend: "Tea drunk a year", of: "of the world's tea drinking", count: "Countries with a figure", since: "Tea drunk", none: "No figure" }
  };
  var words = function () { return WORDS[st.measure]; };
  var FAONAME = { "United Republic of Tanzania": "Tanzania", "Democratic Republic of the Congo": "DR Congo", "Ethiopia PDR": "Ethiopia (with Eritrea, to 1992)",
    "Viet Nam": "Vietnam", "Iran (Islamic Republic of)": "Iran", "Lao People's Democratic Republic": "Laos", "Republic of Korea": "South Korea",
    "China, mainland": "China", "China, Taiwan Province of": "Taiwan", "Russian Federation": "Russia", "Bolivia (Plurinational State of)": "Bolivia", "USSR": "USSR (to 1991)" };
  var isoByName = {}; Object.keys(names).forEach(function (k) { isoByName[names[k]] = k; });
  var area = {};
  D.area.forEach(function (r) { if (!r.area_ha) return; var k = isoByName[FAONAME[r.country] || r.country]; if (k) (area[k] = area[k] || {})[+r.year] = +r.area_ha; });

  var regions = D.layout.regions, meta = {}, regionById = {}, owners = {};
  regions.forEach(function (rg) {
    regionById[rg.id] = rg;
    rg.countries.forEach(function (c) {
      var ids = c.map == null ? [] : [].concat(c.map);
      meta[c.iso3] = { iso3: c.iso3, region: rg.id, ids: ids, dot: c.dot, to: c.to };
      ids.forEach(function (id) { (owners[id] = owners[id] || []).push(meta[c.iso3]); });
    });
  });
  // Countries with figures but no place in tea_map.yml still count, under "Other".
  Object.keys(by).forEach(function (k) {
    if (meta[k]) return;
    if (!regionById.other) { regionById.other = { id: "other", name: "Other", countries: [] }; regions.push(regionById.other); }
    regionById.other.countries.push({ iso3: k }); meta[k] = { iso3: k, region: "other", ids: [] };
  });
  var market = {}; (D.layout.markets || []).forEach(function (m) { m.countries.forEach(function (c) { market[c] = m; }); });

  var wYears = Object.keys(world).map(Number).sort(function (a, b) { return a - b; });
  var Y0 = wYears[0], Y1 = wYears[wYears.length - 1];
  var val = function (iso, y) { return (by[iso] || {})[y]; };
  // Which country a map shape stands for in a year: the USSR to 1991, Ethiopia with Eritrea to 1992, and so on.
  function owner(id, y) {
    var list = owners[id] || [], hit = null;
    list.forEach(function (m) { if (!hit && m.to && y <= m.to && val(m.iso3, y)) hit = m; });
    list.forEach(function (m) { if (!hit && !m.to && val(m.iso3, y)) hit = m; });
    list.forEach(function (m) { if (!hit && !m.to) hit = m; });
    return hit;
  }
  function regionTotal(rid, y) { return regionById[rid].countries.reduce(function (s, c) { return s + (val(c.iso3, y) || 0); }, 0); }
  function producers(rid, y) { return regionById[rid].countries.filter(function (c) { return val(c.iso3, y); }).map(function (c) { return c.iso3; }); }

  /* ---------- colour: one green, light to dark, by tonnes ---------- */
  var BINS = [1e3, 1e4, 5e4, 2e5, 1e6];
  var RAMP = ["#CFE0D3", "#A6C7B1", "#79A68D", "#4F836B", "#2C6655", "#173E32"];
  var LAND = "#E2DCCD";
  var colour = function (t) { if (!t) return LAND; var i = 0; while (i < BINS.length && t >= BINS[i]) i++; return RAMP[i]; };
  var darkFill = function (t) { return t >= 5e4; };
  var binLabel = ["Under 1,000 t", "1,000 to 10,000", "10,000 to 50,000", "50,000 to 200,000", "200,000 to 1M", "1M t and over"];
  function legend() {
    $("tm-legend").innerHTML = "<span class='tmap-legend-h'>" + words().legend + "</span>" + RAMP.map(function (c, i) { return "<span><i class='k-sw' style='background:" + c + "'></i>" + binLabel[i] + "</span>"; }).join("") +
      "<span><i class='k-sw' style='background:" + LAND + "'></i>" + words().none + "</span>";
  }

  /* ---------- state ---------- */
  var st = { year: Y1, view: "map", region: null, country: null, measure: "production" };
  (function readHash() {
    var h = {}; location.hash.slice(1).split("&").forEach(function (p) { var kv = p.split("="); if (kv[1]) h[kv[0]] = decodeURIComponent(kv[1]); });
    if (h.y && +h.y >= Y0 && +h.y <= Y1) st.year = +h.y;
    if (h.c && meta[h.c.toUpperCase()]) { st.country = h.c.toUpperCase(); st.region = meta[st.country].region; }
    else if (h.r && regionById[h.r]) st.region = h.r;
    if (h.v === "globe") st.view = "globe";
    if (WORDS[h.m]) st.wantMeasure = h.m;   // applied once the trade figures arrive
  })();
  function writeHash() {
    var p = []; if (st.country) p.push("c=" + st.country); else if (st.region) p.push("r=" + st.region);
    if (st.year !== Y1) p.push("y=" + st.year); if (st.view === "globe") p.push("v=globe"); if (st.measure !== "production") p.push("m=" + st.measure);
    try { history.replaceState(null, "", p.length ? "#" + p.join("&") : location.pathname + location.search); } catch (e) {}
  }
  var listeners = [];
  function set(patch, opts) {
    for (var k in patch) st[k] = patch[k];
    writeHash();
    listeners.forEach(function (fn) { fn(opts || {}); });
  }
  function pickCountry(iso, opts) { if (!meta[iso]) return; set({ country: iso, region: meta[iso].region }, opts); }
  function pickRegion(rid) { set({ region: rid, country: null }); }
  function pickWorld() { set({ region: null, country: null }); }

  /* ---------- breadcrumbs ---------- */
  function crumbs() {
    var parts = ["<button type='button' data-go='world'" + (!st.region ? " aria-current='page'" : "") + ">World</button>"];
    if (st.region) parts.push("<button type='button' data-go='region'" + (!st.country ? " aria-current='page'" : "") + ">" + esc(regionById[st.region].name) + "</button>");
    if (st.country) parts.push("<button type='button' aria-current='page'>" + esc(names[st.country] || st.country) + "</button>");
    $("tm-crumbs").innerHTML = parts.join("<span aria-hidden='true'>›</span>");
  }
  $("tm-crumbs").addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b) return;
    if (b.dataset.go === "world") pickWorld(); else if (b.dataset.go === "region") pickRegion(st.region);
  });
  listeners.push(crumbs);

  /* ---------- year slider and play ---------- */
  var slider = $("tm-year"), playing = null;
  slider.min = Y0; slider.max = Y1; slider.value = st.year;
  function showYear() { $("tm-year-v").textContent = st.year; slider.value = st.year; }
  slider.addEventListener("input", function () { stopPlay(); set({ year: +this.value }, { quick: true }); });
  function stopPlay() { if (playing) { clearInterval(playing); playing = null; $("tm-play").innerHTML = "▶ Play"; $("tm-play").setAttribute("aria-label", "Play through the years"); } }
  $("tm-play").addEventListener("click", function () {
    if (playing) return stopPlay();
    if (st.year >= Y1) set({ year: Y0 }, { quick: true });
    this.innerHTML = "❚❚ Pause"; this.setAttribute("aria-label", "Pause");
    playing = setInterval(function () { if (st.year >= Y1) return stopPlay(); set({ year: st.year + 1 }, { quick: true }); }, 320);
  });
  listeners.push(showYear);

  /* ---------- tooltip ---------- */
  var tip = $("tm-tip"), stage = root.querySelector(".tmap-stage");
  function tipHtml(iso) {
    var v = val(iso, st.year), n = names[iso] || iso;
    return "<b>" + esc(n) + "</b>" + (v ? tonnes(v) + " in " + st.year + "<br><span>" + share(v, world[st.year]) + " " + words().of + "</span>" : "<span>" + words().none + " for " + st.year + "</span>");
  }
  function showTip(e, html) {
    var r = stage.getBoundingClientRect();
    tip.innerHTML = html; tip.hidden = false;
    var x = e.clientX - r.left, y = e.clientY - r.top, w = tip.offsetWidth;
    tip.style.left = Math.max(4, Math.min(r.width - w - 4, x - w / 2)) + "px";
    tip.style.top = Math.max(4, y - tip.offsetHeight - 14) + "px";
  }
  function hideTip() { tip.hidden = true; }

  /* ---------- map and globe ---------- */
  var box = $("tm-map"), shapes = [], land, graticule = d3.geoGraticule10();
  var svg, gMap, paths, dots, sphere, grat, shade, path, proj, W, H, zoomK = 1;
  var spin = null, rot = [-20, -8], spinPausedUntil = 0;

  function drawMap() {
    stopSpin();
    box.innerHTML = ""; box.className = "tmap-figure is-" + st.view;
    var phone = box.clientWidth < 600;
    if (st.view === "map") { W = 960; H = phone ? 640 : 500; proj = d3.geoNaturalEarth1(); }
    else { W = 600; H = 600; proj = d3.geoOrthographic().clipAngle(90).rotate(rot); }
    // On a phone, crop to where tea grows (no Arctic, no far Pacific) so the countries are bigger.
    if (st.view === "map") proj.fitExtent([[6, 6], [W - 6, H - 6]], phone ? { type: "MultiPoint", coordinates: [[-92, -42], [152, -42], [-92, 52], [152, 52], [30, 56]] } : { type: "FeatureCollection", features: shapes });
    else proj.scale(W / 2 - 24).translate([W / 2, H / 2]);
    path = d3.geoPath(proj);
    svg = d3.select(box).append("svg").attr("viewBox", "0 0 " + W + " " + H).attr("role", "presentation");
    if (st.view === "globe") {
      var defs = svg.append("defs");
      var g1 = defs.append("radialGradient").attr("id", "tm-ocean").attr("cx", "38%").attr("cy", "32%").attr("r", "75%");
      g1.append("stop").attr("offset", "0%").attr("stop-color", "#F7F3EA");
      g1.append("stop").attr("offset", "100%").attr("stop-color", "#D6E0D7");
      var g2 = defs.append("radialGradient").attr("id", "tm-shade").attr("cx", "36%").attr("cy", "30%").attr("r", "72%");
      g2.append("stop").attr("offset", "0%").attr("stop-color", "#fff").attr("stop-opacity", 0.38);
      g2.append("stop").attr("offset", "55%").attr("stop-color", "#fff").attr("stop-opacity", 0);
      g2.append("stop").attr("offset", "100%").attr("stop-color", "#173E32").attr("stop-opacity", 0.42);
      var g3 = defs.append("radialGradient").attr("id", "tm-drop");
      g3.append("stop").attr("offset", "0%").attr("stop-color", "#173E32").attr("stop-opacity", 0.28);
      g3.append("stop").attr("offset", "100%").attr("stop-color", "#173E32").attr("stop-opacity", 0);
      svg.append("ellipse").attr("cx", W / 2).attr("cy", H - 10).attr("rx", W * 0.32).attr("ry", 10).attr("fill", "url(#tm-drop)");
    }
    gMap = svg.append("g");
    sphere = gMap.append("path").datum({ type: "Sphere" }).attr("class", "tm-sphere").attr("fill", st.view === "globe" ? "url(#tm-ocean)" : "none");
    grat = gMap.append("path").datum(graticule).attr("class", "tm-grat");
    paths = gMap.append("g").selectAll("path").data(shapes).join("path").attr("class", "tm-c")
      .on("pointermove", function (e, d) { var o = owner(d.id, st.year); if (o) showTip(e, tipHtml(o.iso3)); else showTip(e, "<b>" + esc(d.properties.name) + "</b><span>" + words().none + "</span>"); })
      .on("pointerleave", hideTip)
      .on("click", function (e, d) { var o = owner(d.id, st.year); if (o) { hideTip(); pickCountry(o.iso3, { fromMap: true }); } });
    var dotList = Object.keys(meta).filter(function (k) { return meta[k].dot; }).map(function (k) { return meta[k]; });
    dots = gMap.append("g").selectAll("circle").data(dotList).join("circle").attr("class", "tm-dot")
      .on("pointermove", function (e, d) { showTip(e, tipHtml(d.iso3)); })
      .on("pointerleave", hideTip)
      .on("click", function (e, d) { hideTip(); pickCountry(d.iso3, { fromMap: true }); });
    if (st.view === "globe") {
      shade = svg.append("circle").attr("cx", W / 2).attr("cy", H / 2).attr("r", proj.scale()).attr("fill", "url(#tm-shade)").attr("pointer-events", "none");
      svg.append("circle").attr("cx", W / 2).attr("cy", H / 2).attr("r", proj.scale()).attr("class", "tm-rim");
      svg.call(d3.drag().on("start", function () { spinPausedUntil = Infinity; hideTip(); })
        .on("drag", function (e) { var k = 75 / proj.scale(); rot = [rot[0] + e.dx * k, Math.max(-70, Math.min(70, rot[1] - e.dy * k))]; proj.rotate(rot); redraw(); })
        .on("end", function () { spinPausedUntil = Date.now() + 5000; }));
    }
    zoomK = 1;
    redraw(); paint(); frame(false);
    if (st.view === "globe") startSpin();
    $("tm-hint").textContent = st.view === "globe" ? "Drag to turn the globe. Tap a country for its figures." : "Tap a country for its figures, or a region in the blocks below to zoom in.";
  }
  function redraw() {
    sphere.attr("d", path); grat.attr("d", path); paths.attr("d", path);
    dots.each(function (d) {
      var p = proj(d.dot), hidden = st.view === "globe" && d3.geoDistance(d.dot, [-rot[0], -rot[1]]) > Math.PI / 2;
      d3.select(this).attr("cx", p ? p[0] : -99).attr("cy", p ? p[1] : -99).attr("r", (st.view === "globe" ? 5 : 4.5) / zoomK).attr("display", hidden || !p ? "none" : null);
    });
  }
  // Fill each shape for the chosen year; outline the chosen country and region.
  function paint() {
    if (!paths) return;
    paths.attr("fill", function (d) { var o = owner(d.id, st.year); return colour(o && val(o.iso3, st.year)); })
      .classed("is-tea", function (d) { var o = owner(d.id, st.year); return !!o; })
      .classed("is-picked", function (d) { var o = owner(d.id, st.year); return !!o && o.iso3 === st.country; })
      .classed("is-dim", function (d) { if (!st.region) return false; var o = owner(d.id, st.year); return !o || o.region !== st.region; })
      .attr("aria-label", function (d) { var o = owner(d.id, st.year); return o ? (names[o.iso3] || "") : null; });
    paths.filter(".is-picked").raise();
    dots.attr("fill", function (d) { return colour(val(d.iso3, st.year)); })
      .classed("is-picked", function (d) { return d.iso3 === st.country; })
      .classed("is-dim", function (d) { return !!st.region && d.region !== st.region; });
  }
  // The features and points that frame the chosen region (or country's region).
  function regionFrame(rid) {
    var feats = shapes.filter(function (s) { var o = owner(s.id, st.year) || (owners[s.id] || [])[0]; return o && o.region === rid && s.id !== "643"; });
    if (rid === "europe-west-asia") feats = shapes.filter(function (s) { return ["792", "268", "031", "620", "499"].indexOf(s.id) >= 0; });
    var pts = regionById[rid].countries.filter(function (c) { return meta[c.iso3].dot; }).map(function (c) { return { type: "Point", coordinates: meta[c.iso3].dot }; });
    return { type: "FeatureCollection", features: feats.concat(pts.map(function (p) { return { type: "Feature", geometry: p }; })) };
  }
  function frame(animate) {
    if (!svg) return;
    if (st.view === "map") {
      var t = d3.zoomIdentity;
      if (st.region) {
        var b = path.bounds(regionFrame(st.region)), dx = b[1][0] - b[0][0], dy = b[1][1] - b[0][1];
        var k = Math.max(1, Math.min(7, 0.86 / Math.max(dx / W, dy / H)));
        t = d3.zoomIdentity.translate(W / 2 - k * (b[0][0] + b[1][0]) / 2, H / 2 - k * (b[0][1] + b[1][1]) / 2).scale(k);
        // keep the map's edges inside the frame
        t = d3.zoomIdentity.translate(Math.min(0, Math.max(W - W * k, t.x)), Math.min(0, Math.max(H - H * k, t.y))).scale(k);
      }
      zoomK = t.k;
      var sel = animate && !reduceMotion ? gMap.transition().duration(750).ease(d3.easeCubicInOut) : gMap;
      sel.attr("transform", t.toString());
      redraw();
    } else {
      var target = null;
      if (st.country) {
        var m = meta[st.country];
        if (m.dot) target = m.dot;
        else { var f = shapes.filter(function (s) { return m.ids.indexOf(s.id) >= 0; }); if (f.length) target = d3.geoCentroid({ type: "FeatureCollection", features: f }); }
      } else if (st.region) target = d3.geoCentroid(regionFrame(st.region));
      if (target) { stopSpin(); turnTo(target, animate); }
      else if (!spin) { spinPausedUntil = 0; startSpin(); }
    }
  }
  function turnTo(p, animate) {
    var from = rot.slice(), to = [-p[0], Math.max(-60, Math.min(60, -p[1]))];
    var d = to[0] - from[0]; d = ((d + 540) % 360) - 180; to[0] = from[0] + d;
    if (!animate || reduceMotion) { rot = to; proj.rotate(rot); redraw(); return; }
    var i = d3.interpolate(from, to);
    d3.transition().duration(1000).ease(d3.easeCubicInOut).tween("turn", function () { return function (t) { rot = i(t); proj.rotate(rot); redraw(); }; });
  }
  function startSpin() {
    if (reduceMotion || spin || st.view !== "globe" || st.country || st.region) return;
    var last = null;
    spin = d3.timer(function (el) {
      var dt = last == null ? 0 : el - last; last = el;
      if (Date.now() < spinPausedUntil || document.hidden) return;
      rot = [rot[0] + dt * 0.012, rot[1]]; proj.rotate(rot); redraw();
    });
  }
  function stopSpin() { if (spin) { spin.stop(); spin = null; } }
  listeners.push(function (o) { paint(); if (!o.quick) frame(true); });

  $("tmap").querySelectorAll("[data-view]").forEach(function (b) {
    b.addEventListener("click", function () {
      if (st.view === b.dataset.view) return;
      $("tmap").querySelectorAll("[data-view]").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      set({ view: b.dataset.view }, { quick: true }); drawMap();
    });
  });

  /* ---------- small 2D line charts for the panel ---------- */
  function el(name, attrs, parent) { var e = document.createElementNS(NS, name); for (var k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
  function nice(max) { var p = Math.pow(10, Math.floor(Math.log10(max))), m = max / p; var s = m <= 1.5 ? 0.25 : m <= 3 ? 0.5 : m <= 6 ? 1 : 2; return s * p; }
  // d: {year: value}; mark: the year to ring in gold; fmt: axis label; tipFmt: hover text
  function lineChart(boxEl, d, mark, fmt, tipFmt) {
    boxEl.innerHTML = "";
    var ys = Object.keys(d).map(Number).sort(function (a, b) { return a - b; });
    if (!ys.length) { boxEl.innerHTML = "<p class='muted'>No figures.</p>"; return; }
    var Wc = 520, Hc = 230, pad = { l: 46, r: 14, t: 12, b: 28 };
    var x0 = ys[0], x1 = Math.max(ys[ys.length - 1], x0 + 1), max = Math.max.apply(0, ys.map(function (y) { return d[y]; }));
    var step = nice(max / 1.2), ymax = Math.ceil(max / step) * step || 1;
    var X = function (x) { return pad.l + (x - x0) / (x1 - x0) * (Wc - pad.l - pad.r); }, Y = function (v) { return Hc - pad.b - v / ymax * (Hc - pad.t - pad.b); };
    var s = el("svg", { viewBox: "0 0 " + Wc + " " + Hc }, boxEl);
    for (var v = 0; v <= ymax + 1e-9; v += step) {
      el("line", { x1: pad.l, x2: Wc - pad.r, y1: Y(v), y2: Y(v), class: "grid" }, s);
      el("text", { x: pad.l - 6, y: Y(v) + 4, class: "tick", "text-anchor": "end" }, s).textContent = fmt(v);
    }
    var gap = x1 - x0 > 40 ? 20 : x1 - x0 > 12 ? 5 : x1 - x0 > 6 ? 2 : 1;
    for (var y = Math.ceil(x0 / gap) * gap; y <= x1; y += gap) el("text", { x: X(y), y: Hc - 8, class: "tick", "text-anchor": "middle" }, s).textContent = y;
    var run = [];
    ys.forEach(function (y, i) {
      run.push((run.length ? "L" : "M") + X(y).toFixed(1) + "," + Y(d[y]).toFixed(1));
      if (i === ys.length - 1 || ys[i + 1] !== y + 1) { if (run.length > 1) el("path", { d: run.join(""), class: "line-main" }, s); else el("circle", { cx: X(y), cy: Y(d[y]), r: 2.5, class: "pt" }, s); run = []; }
    });
    // hover: a guide and label for the nearest year
    var guide = el("line", { y1: pad.t, y2: Hc - pad.b, class: "tm-guide", visibility: "hidden" }, s);
    var hot = el("circle", { r: 4.5, class: "pt pt-last", visibility: "hidden" }, s);
    if (mark != null && d[mark] != null) el("circle", { cx: X(mark), cy: Y(d[mark]), r: 5, class: "pt pt-last" }, s);
    var lab = document.createElement("div"); lab.className = "tm-clab"; lab.hidden = true; boxEl.appendChild(lab);
    var hit = el("rect", { x: pad.l, y: pad.t, width: Wc - pad.l - pad.r, height: Hc - pad.t - pad.b, fill: "transparent" }, s);
    hit.addEventListener("pointermove", function (e) {
      var r = s.getBoundingClientRect(), xv = x0 + ((e.clientX - r.left) / r.width * Wc - pad.l) / (Wc - pad.l - pad.r) * (x1 - x0);
      var near = ys.reduce(function (a, b) { return Math.abs(b - xv) < Math.abs(a - xv) ? b : a; });
      guide.setAttribute("x1", X(near)); guide.setAttribute("x2", X(near)); guide.setAttribute("visibility", "visible");
      hot.setAttribute("cx", X(near)); hot.setAttribute("cy", Y(d[near])); hot.setAttribute("visibility", "visible");
      lab.innerHTML = tipFmt(near, d[near]); lab.hidden = false;
      var px = X(near) / Wc * r.width; lab.style.left = Math.max(0, Math.min(r.width - lab.offsetWidth, px - lab.offsetWidth / 2)) + "px";
    });
    hit.addEventListener("pointerleave", function () { guide.setAttribute("visibility", "hidden"); hot.setAttribute("visibility", "hidden"); lab.hidden = true; });
  }
  var unit = function () { return st.measure === "production" ? "Tonnes of made tea" : "Tonnes"; };
  var axisT = function (v) { return v >= 1e6 ? (v / 1e6).toFixed(v % 1e6 ? 1 : 0) + "M" : v >= 1e3 ? Math.round(v / 1e3) + "k" : Math.round(v); };

  /* ---------- auction series ---------- */
  var sales = null;
  // Each market's yearly average price (US$/kg), weighted by kg sold. Add new markets here.
  function marketSeries(m) {
    if (m.series !== "mombasa" || !sales) return null;
    var rows = {}, key = function (y, n) { return y + "-" + n; };
    var num2 = function (v) { return v === "" || v == null ? null : +v; };
    (sales.history || []).forEach(function (r) { rows[key(r.year, r.sale)] = { y: +r.year, p: num2(r.all_avg_usd_kg), kg: num2(r.all_sold_kg) }; });
    (sales.combrok || []).forEach(function (r) { rows[key(r.year, r.sale)] = { y: +r.year, p: num2(r.ctc_avg_usd_kg), kg: num2(r.ctc_sold_kg) }; });
    (sales.eatta || []).forEach(function (r) { var o = rows[key(r.year, r.sale)] || {}; var p = num2(r.avg_usd_kg), kg = num2(r.sold_kg); rows[key(r.year, r.sale)] = { y: +r.year, p: p != null ? p : o.p, kg: kg != null ? kg : o.kg }; });
    var sum = {}, kg = {}, n = {};
    Object.keys(rows).forEach(function (k) { var r = rows[k]; if (r.p == null || !r.kg) return; sum[r.y] = (sum[r.y] || 0) + r.p * r.kg; kg[r.y] = (kg[r.y] || 0) + r.kg; n[r.y] = (n[r.y] || 0) + 1; });
    var out = {}; Object.keys(sum).forEach(function (y) { out[y] = sum[y] / kg[y]; });
    var last = Math.max.apply(0, Object.keys(out).map(Number));
    return { avg: out, sales: n, last: last, current: last === new Date().getFullYear() };
  }
  fetch(D.sales).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { sales = j; if (st.country && market[st.country]) panel(); }).catch(function () {});

  /* ---------- the panel under the map ---------- */
  var pbox = $("tm-panel");
  function stats(list) { return "<div class='stat-row tmap-stats'>" + list.map(function (s) { return "<div class='stat'><span class='stat-label'>" + s[0] + "</span><strong>" + s[1] + "</strong><span class='stat-note'>" + (s[2] || "") + "</span></div>"; }).join("") + "</div>"; }
  function panel() {
    var y = st.year, wt = world[y];
    if (st.country) return countryPanel(st.country);
    if (st.region) {
      var rg = regionById[st.region], rt = regionTotal(st.region, y), prs = producers(st.region, y);
      var series = {}; wYears.forEach(function (yy) { var v = regionTotal(st.region, yy); if (v) series[yy] = v; });
      pbox.innerHTML = "<p class='eyebrow'>Region</p><h2 class='tmap-panel-h'>" + esc(rg.name) + "</h2>" +
        stats([[words().what + ", " + y, tonnes(rt), rt && series[y - 10] ? change(rt, series[y - 10]) + " in ten years" : ""], ["Share of world, " + y, share(rt, wt), ""], [words().count, prs.length, "with figures for " + y]]) +
        "<div class='tmap-grid'><figure class='dash-panel'><figcaption><span class='dash-panel-h'>" + esc(rg.name) + " since " + Y0 + "</span><span class='dash-panel-u'>" + unit() + "</span></figcaption><div class='chart tm-chart' id='tm-c1'></div></figure>" +
        "<div><p class='dash-panel-u tmap-list-h'>Countries, " + y + "</p><ul class='tmap-list'>" + rg.countries.filter(function (c) { return by[c.iso3]; }).map(function (c) {
          var v = val(c.iso3, y); return "<li><button type='button' data-iso='" + c.iso3 + "'><span>" + esc(names[c.iso3]) + "</span><b>" + (v ? tonnes(v) : "–") + "</b></button></li>";
        }).join("") + "</ul></div></div>";
      lineChart($("tm-c1"), series, y, axisT, function (yy, v) { return "<b>" + yy + "</b> " + num(v) + " t"; });
      return;
    }
    var ea = regionTotal("eastern-africa", y), n = Object.keys(by).filter(function (k) { return val(k, y); }).length;
    pbox.innerHTML = "<p class='eyebrow'>The world</p><h2 class='tmap-panel-h'>" + (st.measure === "production" ? "The world's tea in " : "The world's tea trade in ") + y + "</h2>" +
      stats([["World, " + y, wt ? tonnes(wt) : "–", wt && world[y - 10] ? change(wt, world[y - 10]) + " in ten years" : ""], ["Eastern Africa", wt ? share(ea, wt) : "–", words().of], [words().count, n, "with figures for " + y]]) +
      "<div class='tmap-grid'><figure class='dash-panel'><figcaption><span class='dash-panel-h'>World " + words().since.toLowerCase() + " since " + Y0 + "</span><span class='dash-panel-u'>" + unit() + "</span></figcaption><div class='chart tm-chart' id='tm-c1'></div></figure>" +
      "<div><p class='dash-panel-u tmap-list-h'>Regions, " + y + "</p><ul class='tmap-list'>" + regions.map(function (rg) {
        var v = regionTotal(rg.id, y); return "<li><button type='button' data-region='" + rg.id + "'><span>" + esc(rg.name) + "</span><b>" + (v ? tonnes(v) : "–") + "</b></button></li>";
      }).join("") + "</ul></div></div>";
    lineChart($("tm-c1"), world, y, axisT, function (yy, v) { return "<b>" + yy + "</b> " + num(v) + " t"; });
  }
  function countryPanel(iso) {
    var y = st.year, d = by[iso] || {}, v = d[y], name = names[iso] || iso, m = market[iso];
    var ys = Object.keys(d).map(Number).sort(function (a, b) { return a - b; }), ly = ys[ys.length - 1];
    var a = (area[iso] || {})[y];
    var list = [
      [words().what + ", " + y, v ? tonnes(v) : "–", v && d[y - 1] ? change(v, d[y - 1]) + " on " + (y - 1) : v ? "" : "No figure for " + y],
      ["Share of world, " + y, v && world[y] ? share(v, world[y]) : "–", ""],
      ["Latest, " + ly, ly ? tonnes(d[ly]) : "–", ly && d[ly - 1] ? change(d[ly], d[ly - 1]) + " on " + (ly - 1) : ""]
    ];
    if (st.measure === "production") list.push(["Tonnes a hectare, " + y, v && a ? (v / a).toFixed(2) : "–", a ? num(a) + " ha picked" : ""]);
    else { var g = M.production.by[iso] || {}; list.push(["Grown, " + y, g[y] ? tonnes(g[y]) : "–", g[y] ? "" : M.production.by[iso] ? "No figure for " + y : "Grows no tea"]); }
    var ms = m ? marketSeries(m) : null;
    var second = m
      ? "<figure class='dash-panel'><figcaption><span class='dash-panel-h'>" + esc(m.name) + "</span><span class='dash-panel-u'>US$ a kg, year average</span></figcaption>" +
        (ms ? "<div class='chart tm-chart' id='tm-c2'></div><p class='fine muted'>All teas sold at the auction, weighted by kilos." + (ms.current ? " " + ms.last + " is the year so far, " + ms.sales[ms.last] + " sales." : "") +
          " <a href='" + D.base + m.page + "'>Every sale on the Auctions page</a></p>" : "<p class='muted'>Loading prices…</p>") + "</figure>"
      : "<figure class='dash-panel'><figcaption><span class='dash-panel-h'>Area picked</span><span class='dash-panel-u'>Hectares</span></figcaption><div class='chart tm-chart' id='tm-c2'></div></figure>";
    pbox.innerHTML = "<p class='eyebrow'>" + esc(regionById[meta[iso].region].name) + "</p><h2 class='tmap-panel-h'>" + esc(name) + "</h2>" + stats(list) +
      "<div class='tmap-grid'><figure class='dash-panel'><figcaption><span class='dash-panel-h'>" + words().since + (ys.length ? " since " + ys[0] : "") + "</span><span class='dash-panel-u'>" + unit() + "</span></figcaption><div class='chart tm-chart' id='tm-c1'></div>" +
      (st.measure === "consumption" && iso === "KEN" ? "<p class='fine muted'>Not worked out for Kenya in most recent years: its exports include tea grown in neighbouring countries.</p>" : "") + "</figure>" + second + "</div>";
    lineChart($("tm-c1"), d, y, axisT, function (yy, val2) { return "<b>" + yy + "</b> " + num(val2) + " t"; });
    if (m && ms) lineChart($("tm-c2"), ms.avg, ms.avg[y] != null ? y : null, function (x) { return "$" + x.toFixed(x % 1 ? 1 : 0); }, function (yy, p) { return "<b>" + yy + (ms.current && yy === ms.last ? " so far" : "") + "</b> US$ " + p.toFixed(2) + " a kg"; });
    else if (!m) lineChart($("tm-c2"), area[iso] || {}, y, axisT, function (yy, h) { return "<b>" + yy + "</b> " + num(h) + " ha"; });
  }
  pbox.addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b) return;
    if (b.dataset.iso) pickCountry(b.dataset.iso); else if (b.dataset.region) pickRegion(b.dataset.region);
  });
  listeners.push(function (o) {
    panel();
    if (o.fromMap && pbox.getBoundingClientRect().top > window.innerHeight - 80) pbox.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  });

  /* ---------- blocks: world > region > country ---------- */
  var tbox = $("tm-tree"), tiles = {};
  function tree() {
    var y = st.year, Wt = tbox.clientWidth, Ht = Wt < 600 ? 380 : 440;
    tbox.style.height = Ht + "px";
    var data = { children: (st.region ? [regionById[st.region]] : regions).map(function (rg) {
      return { id: "r:" + rg.id, rid: rg.id, name: rg.name, children: rg.countries.filter(function (c) { return val(c.iso3, y); }).map(function (c) { return { id: "c:" + c.iso3, iso: c.iso3, rid: rg.id, value: val(c.iso3, y) }; }) };
    }).filter(function (r) { return r.children.length; }) };
    var h = d3.hierarchy(data).sum(function (d) { return d.value || 0; }).sort(function (a, b) { return b.value - a.value; });
    d3.treemap().size([Wt, Ht]).paddingInner(2).paddingTop(function (n) { return n.depth === 1 ? 22 : 0; }).round(true).tile(d3.treemapSquarify.ratio(1.2))(h);
    var seen = {};
    h.descendants().forEach(function (n) {
      if (!n.depth) return;
      var d = n.data, t = tiles[d.id], w = n.x1 - n.x0, hh = n.y1 - n.y0;
      if (!t) {
        t = document.createElement("button"); t.type = "button"; t.dataset.id = d.id;
        t.className = d.iso ? "tm-tile" : "tm-group";
        tbox.appendChild(t); tiles[d.id] = t;
        t.style.left = n.x0 + "px"; t.style.top = n.y0 + "px"; t.style.width = "0px"; t.style.height = "0px";
        void t.offsetWidth;
      }
      seen[d.id] = 1;
      t.style.left = n.x0 + "px"; t.style.top = n.y0 + "px"; t.style.width = w + "px"; t.style.height = hh + "px";
      if (d.iso) {
        var nm = names[d.iso], sh = share(d.value, world[y]);
        t.style.background = colour(d.value); t.classList.toggle("on-dark", darkFill(d.value));
        t.classList.toggle("is-picked", d.iso === st.country);
        t.innerHTML = w > 46 && hh > 24 ? "<span class='tm-tn'>" + esc(nm) + "</span>" + (hh > 42 && w > 54 ? "<span class='tm-tv'>" + sh + "</span>" : "") : "";
        t.title = nm + ": " + num(d.value) + " t in " + y + " (" + sh + " " + words().of + ")";
        t.setAttribute("aria-label", t.title);
      } else {
        var rgT = n.value;
        t.innerHTML = "<span class='tm-gn'>" + esc(d.name) + (w > 150 ? " · " + share(rgT, world[y]) : "") + "</span>";
        t.title = d.name + ": " + num(rgT) + " t in " + y + ". Tap to open."; t.setAttribute("aria-label", t.title);
        t.classList.toggle("is-open", !!st.region);
      }
      t.style.zIndex = d.iso ? 2 : 1;
    });
    Object.keys(tiles).forEach(function (k) { if (!seen[k]) { tiles[k].remove(); delete tiles[k]; } });
    $("tm-tree-note").textContent = st.region
      ? "Blocks are sized by the tea each country " + words().past + " in " + y + ", with its share " + words().of + ". Tap a country for its figures, or the region's name to go back to the world."
      : "Each block is one country's share " + words().of + " in " + y + ". Tap a region's name to open it, then a country for its figures.";
  }
  tbox.addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b) return;
    var id = b.dataset.id;
    if (id.slice(0, 2) === "c:") pickCountry(id.slice(2)); else if (!st.region) pickRegion(id.slice(2)); else pickWorld();
  });
  listeners.push(tree);

  /* ---------- start ---------- */
  var resizeT;
  window.addEventListener("resize", function () { clearTimeout(resizeT); resizeT = setTimeout(function () { drawMap(); tree(); }, 200); });
  root.querySelectorAll("[data-view]").forEach(function (x) { x.setAttribute("aria-pressed", x.dataset.view === st.view ? "true" : "false"); });
  fetch(D.world).then(function (r) { return r.json(); }).then(function (topo) {
    shapes = topojson.feature(topo, topo.objects.countries).features.filter(function (f) { return f.id !== "010"; });
    legend(); drawMap(); showYear(); crumbs(); panel(); tree();
    return fetch(D.trade).then(function (r) { return r.json(); });
  }).then(function (j) {
    if (!j) return;
    var REGION_NAMES = { "middle-east-north-africa": "Middle East and North Africa" };
    ["exports", "imports", "consumption"].forEach(function (k) {
      var m = M[k] = { by: {}, world: {} };
      Object.keys(j[k]).forEach(function (iso) { var o = m.by[iso] = {}; j[k][iso].forEach(function (v, i) { if (v) o[j.from + i] = v; }); });
      j.world[k].forEach(function (v, i) { if (v) m.world[j.from + i] = v; });
    });
    // Countries that only trade tea get a place on the map and in a region
    Object.keys(j.places).forEach(function (iso) {
      var p = j.places[iso]; if (!names[iso]) names[iso] = p[0];
      if (meta[iso]) return;
      var rid = p[2];
      if (!regionById[rid]) { regionById[rid] = { id: rid, name: REGION_NAMES[rid] || rid, countries: [] }; regions.splice(regions.length - (regionById.other ? 1 : 0), 0, regionById[rid]); }
      regionById[rid].countries.push({ iso3: iso });
      meta[iso] = { iso3: iso, region: rid, ids: p[1] ? [p[1]] : [] };
      if (p[1]) (owners[p[1]] = owners[p[1]] || []).push(meta[iso]);
    });
    root.querySelectorAll("[data-measure]").forEach(function (b) { b.disabled = false; });
    if (st.wantMeasure) { useMeasure(st.wantMeasure); delete st.wantMeasure; }
  }).catch(function () {});
  function useMeasure(k) {
    if (!M[k]) return;
    by = M[k].by; world = M[k].world;
    root.querySelectorAll("[data-measure]").forEach(function (x) { x.setAttribute("aria-pressed", x.dataset.measure === k ? "true" : "false"); });
    if (st.country && !by[st.country] && !M.production.by[st.country]) st.country = null;
    st.measure = k; legend(); set({ measure: k }, { quick: true });
  }
  root.querySelectorAll("[data-measure]").forEach(function (b) {
    b.disabled = b.dataset.measure !== "production";
    b.addEventListener("click", function () { if (st.measure !== b.dataset.measure) useMeasure(b.dataset.measure); });
  });
})();
