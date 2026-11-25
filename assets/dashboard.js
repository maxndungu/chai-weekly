/* Mombasa auction dashboard (Markets page).
   Data: assets/data/mombasa-sales.json = {eatta, combrok, highlights}, filled by Jekyll from _data/:
     eatta      mombasa_eatta_sales.csv        official EATTA figures, 2026 on (prices and kg sold)
     combrok    mombasa_combrok_sales.csv      Combrok's per-sale figures, 2020 on (kg and lots offered and sold)
     highlights mombasa_combrok_highlights.json top prices and grade averages per sale
   EATTA's price and kg sold are used wherever EATTA has the sale; Combrok fills what EATTA does not publish.
   Never estimates a missing figure. */
(function () {
  var root = document.getElementById("dashboard");
  if (!root) return;
  var NS = "http://www.w3.org/2000/svg";
  var $ = function (id) { return document.getElementById(id); };
  var each = function (sel, fn) { Array.prototype.forEach.call(root.querySelectorAll(sel), fn); };
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var TEA = { all: "All teas", ctc: "CTC", orthodox: "Orthodox" };
  // The first sale with separate orthodox figures (set in build). Earlier sales have none to show.
  var orthStart = null;
  function beforeOrth(y, n) { return !orthStart || y < orthStart.y || (y === orthStart.y && n < orthStart.n); }
  // What a sale with no figure for the chosen tea shows. Orthodox is sold every other week, so a gap is no sale.
  function missing(r) {
    if (st.tea !== "orthodox") return "Not published";
    return beforeOrth(r.y, r.n) ? "Not available" : "No orthodox sale";
  }
  function noneText(def) {
    if (st.tea !== "orthodox" || !beforeOrth(st.year, st.to)) return def;
    return orthStart ? "Orthodox figures start at sale " + orthStart.n + " of " + orthStart.y : "No orthodox figures yet";
  }
  var el = function (n, a, p) { var e = document.createElementNS(NS, n); for (var k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  var usd = function (v) { return "$" + v.toFixed(2); };
  var pct = function (v) { return (v * 100).toFixed(1) + "%"; };
  var mkg = function (kg) { return (kg / 1e6).toFixed(kg >= 1e7 ? 1 : 2); };
  var kgFull = function (kg) { return Math.round(kg).toLocaleString("en-GB"); };
  var bigKg = function (kg) { return kg >= 1e6 ? mkg(kg) + "<small> m kg</small>" : Math.round(kg / 1e3).toLocaleString("en-GB") + "<small> thousand kg</small>"; };
  var dateOf = function (s) { var p = s.split("-"); return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])); };
  var dShort = function (s) { if (!s) return ""; var d = dateOf(s); return d.getUTCDate() + " " + MON[d.getUTCMonth()]; };
  var num = function (v) { return v === "" || v == null ? null : +v; };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var signed = function (v, f) { return (v > 0 ? "+" : v < 0 ? "−" : "") + f(Math.abs(v)); };

  var byYear = {}, years = [], highlights = {};
  var st = { year: null, from: null, to: null, tea: "all", cmp: true, sort: "sale", dir: -1 };  // newest sale first

  /* ---------- data ---------- */
  function build(data) {
    var rows = {}, key = function (y, n) { return y + "-" + n; };
    var get = function (y, n) {
      var k = key(y, n);
      return rows[k] || (rows[k] = { y: y, n: n, date: "", src: "combrok", all: {}, ctc: {}, orthodox: {}, cb: { all: {}, ctc: {}, orthodox: {} } });
    };
    // Maxwell's lot-by-lot records (2009 to 2020), totalled per sale: used where neither Combrok nor EATTA has the sale.
    // All teas and CTC only: the records do not cover the orthodox catalogue (see ORTH_FROM).
    (data.history || []).forEach(function (h) {
      var r = get(+h.year, +h.sale);
      r.src = "history"; r.date = h.auction_date || "";
      ["all", "ctc"].forEach(function (t) {
        r.cb[t] = { p: num(h[t + "_avg_usd_kg"]), kg: num(h[t + "_sold_kg"]), off: num(h[t + "_offered_kg"]),
          lo: num(h[t + "_offered_lots"]), ls: num(h[t + "_sold_lots"]) };
        r[t] = { p: r.cb[t].p, kg: r.cb[t].kg };
      });
    });
    (data.combrok || []).forEach(function (c) {
      var r = get(+c.year, +c.sale);
      if (r.src === "history") { r.src = "combrok"; r.cb = { all: {}, ctc: {}, orthodox: {} }; r.orthodox = {}; }
      r.src = "combrok";
      ["ctc", "orthodox"].forEach(function (t) {
        r.cb[t] = { p: num(c[t + "_avg_usd_kg"]), kg: num(c[t + "_sold_kg"]), off: num(c[t + "_offered_kg"]),
          lo: num(c[t + "_offered_lots"]), ls: num(c[t + "_sold_lots"]) };
      });
      // Combrok's "CTC" auction totals match EATTA's all-teas totals, so they stand for all teas too.
      r.cb.all = r.cb.ctc;
      r.all = { p: r.cb.ctc.p, kg: r.cb.ctc.kg };
      r.ctc = { p: r.cb.ctc.p, kg: r.cb.ctc.kg };
      r.orthodox = { p: r.cb.orthodox.p, kg: r.cb.orthodox.kg };
    });
    (data.eatta || []).forEach(function (e) {
      var r = get(+e.year, +e.sale);
      r.src = "eatta"; r.date = e.auction_date || "";
      r.all = { p: num(e.avg_usd_kg), kg: num(e.sold_kg), off: num(e.offered_kg) };
      r.ctc = { p: num(e.ctc_avg_usd_kg), kg: num(e.ctc_sold_kg) };
      r.orthodox = { p: num(e.orthodox_avg_usd_kg), kg: num(e.orthodox_sold_kg) };
    });
    Object.keys(rows).map(function (k) { return rows[k]; }).filter(function (r) { return r.y && r.n; })
      .sort(function (a, b) { return a.y - b.y || a.n - b.n; })
      .forEach(function (r) { (byYear[r.y] = byYear[r.y] || []).push(r); });
    years = Object.keys(byYear).map(Number).sort();
    years.some(function (y) { return byYear[y].some(function (r) { return r.orthodox.p != null && (orthStart = r); }); });
    (data.highlights || []).forEach(function (h) { highlights[key(+h.year, +h.sale)] = h; });
  }
  // Figures for the chosen tea: price and kg sold from the main source, offered and lots from Combrok.
  // EATTA first for kg sold and offered, wherever it has the figure (bars, share sold, totals); Combrok only where EATTA's is missing.
  function pick(r, tea) {
    tea = tea || st.tea;
    var m = r[tea] || {}, cb = r.cb[tea] || {}, ea = r.src === "eatta";
    var sold = ea && m.kg != null ? m.kg : cb.kg;
    var off = ea && m.off ? m.off : cb.off;
    var abs = off && sold != null ? Math.min(1, sold / off) : null;
    return { p: m.p != null ? m.p : null, kg: m.kg || null, off: off || null, cbKg: sold, abs: abs, lo: cb.lo, ls: cb.ls };
  }
  function provisional(r) {
    if (!r.date || r.src !== "eatta") return false;
    var d = dateOf(r.date), add = (5 - d.getUTCDay() + 7) % 7;
    return Date.now() < d.getTime() + add * 864e5 + 9 * 36e5; // Friday noon Nairobi = 09:00 UTC
  }
  // The chosen run of sales. For orthodox, only the weeks it was sold: it runs every other week, so the rest are left out.
  var inRange = function (y) {
    return (byYear[y == null ? st.year : y] || []).filter(function (r) {
      return r.n >= st.from && r.n <= st.to && (st.tea !== "orthodox" || r.orthodox.p != null || r.orthodox.kg != null);
    });
  };
  function lastYear(n) {
    if (!st.cmp) return null;
    var prev = byYear[st.year - 1] || [];
    for (var i = 0; i < prev.length; i++) if (prev[i].n === n) return prev[i];
    return null;
  }
  var label = function (r) { return "Sale " + r.n + ", " + (r.date ? dShort(r.date) + " " : "") + r.y; };
  function totals(rows, tea) {
    var t = { n: 0, kg: 0, val: 0, pk: 0, off: 0, cbKg: 0, lo: 0, ls: 0 };
    rows.forEach(function (r) {
      var x = pick(r, tea);
      if (x.p != null) { t.n++; if (x.kg) { t.pk += x.kg; t.val += x.kg * x.p; } }
      if (x.kg) t.kg += x.kg;
      if (x.off && x.cbKg != null) { t.off += x.off; t.cbKg += x.cbKg; }
      if (x.lo) { t.lo += x.lo; t.ls += x.ls || 0; }
    });
    t.avg = t.pk ? t.val / t.pk : null;
    t.abs = t.off ? t.cbKg / t.off : null;
    return t;
  }

  /* ---------- controls ---------- */
  function fillSelect(sel, items, val) {
    sel.innerHTML = "";
    items.forEach(function (it) { var o = document.createElement("option"); o.value = it[0]; o.textContent = it[1]; sel.appendChild(o); });
    sel.value = val;
  }
  function syncControls() {
    fillSelect($("dash-year"), years.slice().reverse().map(function (y) { return [y, y]; }), st.year);
    var opts = byYear[st.year].map(function (r) { return [r.n, "Sale " + r.n + (r.date ? " · " + dShort(r.date) : "")]; });
    fillSelect($("dash-from"), opts, st.from);
    fillSelect($("dash-to"), opts, st.to);
    each("[data-tea]", function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-tea") === st.tea ? "true" : "false"); });
    var qk = quickOf();
    each("[data-last]", function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-last") === qk ? "true" : "false"); });
    var c = $("dash-cmp"), hasPrev = !!byYear[st.year - 1];
    c.checked = st.cmp && hasPrev; c.disabled = !hasPrev;
    $("dash-cmp-l").textContent = "Compare with " + (st.year - 1);
  }
  // Which quick pick matches the current range ("all", "4", "13"), or null for a hand-picked range.
  function quickOf() {
    var rows = byYear[st.year], n = rows.length, last = rows[n - 1].n;
    if (st.to !== last) return null;
    if (st.from === rows[0].n) return "all";
    if (n > 4 && st.from === rows[n - 4].n) return "4";
    if (n > 13 && st.from === rows[n - 13].n) return "13";
    return null;
  }
  function applyQuick(k) {
    var rows = byYear[st.year];
    st.to = rows[rows.length - 1].n;
    st.from = k === "all" ? rows[0].n : rows[Math.max(0, rows.length - +k)].n;
  }
  // A new year opens on its whole run of sales, or on the same quick pick (last 4, last 13) if one was on.
  function setYear(y) {
    var q = quickOf();
    st.year = y;
    applyQuick(q === "4" || q === "13" ? q : "all");
  }
  function saveUrl() {
    if (!window.history || !history.replaceState) return;
    var q = new URLSearchParams(location.search);
    q.set("year", st.year); q.set("from", st.from); q.set("to", st.to);
    if (st.tea === "all") q.delete("tea"); else q.set("tea", st.tea);
    if (st.cmp) q.delete("compare"); else q.set("compare", "no");
    history.replaceState(null, "", location.pathname + "?" + q.toString() + location.hash);
  }
  function wire() {
    $("dash-year").addEventListener("change", function () { setYear(+this.value); update(); });
    $("dash-from").addEventListener("change", function () { st.from = +this.value; if (st.to < st.from) st.to = st.from; update(); });
    $("dash-to").addEventListener("change", function () { st.to = +this.value; if (st.from > st.to) st.from = st.to; update(); });
    $("dash-cmp").addEventListener("change", function () { st.cmp = this.checked; update(); });
    each("[data-tea]", function (b) { b.addEventListener("click", function () { st.tea = b.getAttribute("data-tea"); update(); }); });
    each("[data-last]", function (b) {
      b.addEventListener("click", function () {
        applyQuick(b.getAttribute("data-last"));
        update();
      });
    });
    var t;
    window.addEventListener("resize", function () { clearTimeout(t); t = setTimeout(draw, 150); });
  }

  /* ---------- headline figures ---------- */
  function stats(rows) {
    var tile = function (lbl, value, note) {
      return '<div class="stat"><span class="stat-label">' + lbl + "</span><strong>" + value + '</strong><span class="stat-note">' + note + "</span></div>";
    };
    var t = totals(rows), withP = rows.filter(function (r) { return pick(r).p != null; });
    if (!withP.length) { $("dash-stats").innerHTML = tile("Average price", "None", noneText(TEA[st.tea] + " had no published average in these sales")); return; }
    var first = withP[0], last = withP[withP.length - 1];
    var span = withP.length === 1 ? "Sale " + first.n : "Sales " + first.n + " to " + last.n;
    var prev = st.cmp && byYear[st.year - 1] ? totals(inRange(st.year - 1)) : null;
    var vs = function (d, f) { return d == null ? "" : " · " + signed(d, f) + " on " + (st.year - 1); };
    var hi = withP.reduce(function (a, r) { return pick(r).p > pick(a).p ? r : a; });
    var lo = withP.reduce(function (a, r) { return pick(r).p < pick(a).p ? r : a; });
    $("dash-stats").innerHTML =
      tile("Average price", t.avg != null ? usd(t.avg) : "None", span + ", " + TEA[st.tea].toLowerCase() + (prev && prev.avg != null && t.avg != null ? vs(t.avg - prev.avg, usd) : "")) +
      tile("Tea sold", bigKg(t.kg), t.off ? "of " + bigKg(t.off).replace(/<[^>]+>/g, "") + " offered" : withP.length + " sales") +
      tile("Share sold", t.abs != null ? pct(t.abs) : "None", t.abs != null ? (t.lo ? kgFull(t.ls) + " of " + kgFull(t.lo) + " lots" : "") + (prev && prev.abs != null ? vs((t.abs - prev.abs) * 100, function (v) { return v.toFixed(1) + " pts"; }) : "") : "No offered figures for these sales") +
      tile("Highest sale", usd(pick(hi).p), "Sale " + hi.n + (hi.date ? ", " + dShort(hi.date) : "") + "; lowest " + usd(pick(lo).p) + " at sale " + lo.n);
  }

  /* ---------- chart helpers ---------- */
  var tip = $("dash-tip");
  function showTip(evt, html) {
    tip.innerHTML = html; tip.hidden = false;
    var r = root.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    var x = evt.clientX - r.left + 14, y = evt.clientY - r.top - h - 12;
    if (x + w > r.width - 8) x = evt.clientX - r.left - w - 14;
    if (y < 0) y = evt.clientY - r.top + 18;
    tip.style.left = Math.max(8, x) + "px"; tip.style.top = y + "px";
  }
  var hideTip = function () { tip.hidden = true; };
  var tipRow = function (cls, lbl, value) { return '<div class="dash-tip-row"><i class="' + cls + '"></i>' + lbl + "<b>" + value + "</b></div>"; };
  var tipHead = function (r) { return '<div class="dash-tip-h">' + label(r) + (provisional(r) ? " · provisional" : "") + "</div>"; };
  function frame(fig, H) {
    fig.innerHTML = "";
    var W = Math.max(280, Math.round(fig.clientWidth || 600));
    return { svg: el("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, "aria-hidden": "true" }, fig), W: W, H: H, P: { l: 46, r: 12, t: 10, b: 28 } };
  }
  function xTicks(f, rows, X) {
    var n = rows.length, step = Math.max(1, Math.ceil(n / Math.max(2, Math.floor((f.W - 60) / 52))));
    rows.forEach(function (r, i) {
      if ((i % step && i !== n - 1) || (i !== n - 1 && n - 1 - i < step * 0.6)) return;
      el("text", { x: X(i), y: f.H - 8, "class": "tick", "text-anchor": n === 1 ? "middle" : i === 0 ? "start" : i === n - 1 ? "end" : "middle" }, f.svg).textContent = r.n;
    });
    el("text", { x: f.P.l - 8, y: f.H - 8, "class": "tick", "text-anchor": "end" }, f.svg).textContent = "Sale";
  }
  function niceTicks(lo, hi, count) {
    var span = hi - lo || 1, raw = span / count, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var step = [1, 2, 2.5, 5, 10].map(function (m) { return m * mag; }).filter(function (s) { return s >= raw; })[0];
    var out = [], v = Math.floor(lo / step) * step;
    for (; v <= hi + step * 1e-3; v += step) out.push(+v.toFixed(6));
    if (out[out.length - 1] < hi) out.push(+(out[out.length - 1] + step).toFixed(6));
    return out;
  }
  function empty(f, text) { el("text", { x: f.W / 2, y: f.H / 2, "class": "tick", "text-anchor": "middle" }, f.svg).textContent = text; }
  function legend(id, show, items) {
    var l = $(id); l.hidden = !show;
    if (show) l.innerHTML = items.map(function (it) { return '<span><i class="' + it[0] + '"></i>' + it[1] + "</span>"; }).join("");
  }

  /* A line chart of one figure per sale, with the same sale last year dashed. */
  function lineChart(id, legendId, rows, valueOf, fmtAxis, fmtTip, emptyText, minPad) {
    var fig = $(id), f = frame(fig, fig.clientWidth < 520 ? 220 : 260), P = f.P;
    var cur = rows.map(valueOf);
    var prev = rows.map(function (r) { var o = lastYear(r.n); return o ? valueOf(o) : null; });
    var hasPrev = prev.some(function (v) { return v != null; });
    legend(legendId, hasPrev, [["k-cur", String(st.year)], ["k-prev", String(st.year - 1)]]);
    var all = cur.concat(prev).filter(function (v) { return v != null; });
    if (!all.length) return empty(f, emptyText);
    var lo = Math.min.apply(0, all), hi = Math.max.apply(0, all), pad = Math.max((hi - lo) * 0.12, minPad);
    var ticks = niceTicks(lo - pad, hi + pad, 4), y0 = ticks[0], y1 = ticks[ticks.length - 1];
    var n = rows.length, plotW = f.W - P.l - P.r;
    var X = function (i) { return n === 1 ? P.l + plotW / 2 : P.l + i / (n - 1) * plotW; };
    var Y = function (v) { return f.H - P.b - (v - y0) / (y1 - y0) * (f.H - P.t - P.b); };
    ticks.forEach(function (v) {
      el("line", { x1: P.l, x2: f.W - P.r, y1: Y(v), y2: Y(v), "class": "grid" }, f.svg);
      el("text", { x: P.l - 8, y: Y(v) + 4, "class": "tick", "text-anchor": "end" }, f.svg).textContent = fmtAxis(v);
    });
    xTicks(f, rows, X);
    var path = function (vals, cls) {
      var d = "", pen = false;
      vals.forEach(function (v, i) { if (v == null) return; d += (pen ? "L" : "M") + X(i).toFixed(1) + "," + Y(v).toFixed(1); pen = true; });
      if (d) el("path", { d: d, "class": cls }, f.svg);
    };
    if (hasPrev) path(prev, "dash-line-prev");
    path(cur, "dash-line");
    var dots = cur.filter(function (v) { return v != null; }).length <= 24;
    cur.forEach(function (v, i) { if (v != null && (dots || i === n - 1)) el("circle", { cx: X(i), cy: Y(v), r: i === n - 1 ? 5 : 4, "class": "dash-dot" + (i === n - 1 ? " last" : "") }, f.svg); });
    var li = -1; for (var k = n - 1; k >= 0; k--) if (cur[k] != null) { li = k; break; }
    if (li >= 0) el("text", { x: Math.min(X(li), f.W - P.r), y: Y(cur[li]) - 12, "class": "tick strong dash-halo", "text-anchor": n === 1 ? "middle" : "end" }, f.svg).textContent = fmtTip(cur[li]);
    var cross = el("line", { y1: P.t, y2: f.H - P.b, "class": "dash-cross", visibility: "hidden" }, f.svg);
    var ring = el("circle", { r: 6, "class": "dash-ring", visibility: "hidden" }, f.svg);
    var hit = el("rect", { x: P.l - 10, y: 0, width: plotW + 20, height: f.H, fill: "transparent" }, f.svg);
    var move = function (evt) {
      var b = f.svg.getBoundingClientRect(), x = (evt.clientX - b.left) * f.W / b.width;
      var i = n === 1 ? 0 : Math.max(0, Math.min(n - 1, Math.round((x - P.l) / plotW * (n - 1)))), r = rows[i], v = cur[i];
      cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.setAttribute("visibility", "visible");
      if (v != null) { ring.setAttribute("cx", X(i)); ring.setAttribute("cy", Y(v)); ring.setAttribute("visibility", "visible"); } else ring.setAttribute("visibility", "hidden");
      var html = tipHead(r) + tipRow("k-cur", hasPrev ? String(st.year) : TEA[st.tea], v != null ? fmtTip(v) : missing(r));
      if (hasPrev) html += tipRow("k-prev", String(st.year - 1), prev[i] != null ? fmtTip(prev[i]) : lastYear(r.n) ? missing(lastYear(r.n)) : "No sale " + r.n);
      var pj = i - 1; while (pj >= 0 && cur[pj] == null) pj--;
      if (pj >= 0 && v != null) { var c = v - cur[pj]; html += '<div class="dash-tip-note">' + (c ? (c > 0 ? "Up " : "Down ") + fmtTip(Math.abs(c)).replace("%", " pts") : "Level") + " on sale " + rows[pj].n + "</div>"; }
      showTip(evt, html);
    };
    hit.addEventListener("pointermove", move);
    hit.addEventListener("pointerdown", move);
    hit.addEventListener("pointerleave", function () { cross.setAttribute("visibility", "hidden"); ring.setAttribute("visibility", "hidden"); hideTip(); });
  }

  /* Offered (light) with sold (dark) drawn over it: the dark share of each bar is the share sold. */
  function kgChart(rows) {
    var fig = $("dash-kg"), f = frame(fig, fig.clientWidth < 520 ? 210 : 250), P = f.P;
    var xs = rows.map(function (r) { return pick(r); });
    var hasOff = xs.some(function (x) { return x.off; });
    // Last year's same sale: kg sold, drawn over the bars when "compare with last year" is on.
    var pv = rows.map(function (r) { var o = lastYear(r.n), x = o ? pick(o) : null; return x ? (x.cbKg != null ? x.cbKg : x.kg) || null : null; });
    var hasPv = pv.some(function (v) { return v != null; });
    legend("dash-kg-legend", hasOff || hasPv, (hasOff ? [["k-off", "Offered"]] : []).concat([["k-sold", "Sold"]],
      hasPv ? [["k-prev", "Sold " + (st.year - 1)]] : []));
    var max = Math.max.apply(0, xs.map(function (x) { return Math.max(x.kg || 0, x.off || 0); }).concat(pv.map(function (v) { return v || 0; }), [0]));
    if (!max) return empty(f, noneText("No " + TEA[st.tea] + " sold in these sales"));
    var U = max < 1e6 ? 1e3 : 1e6;
    $("dash-kg-u").textContent = U === 1e3 ? "thousand kg" : "million kg";
    var ticks = niceTicks(0, max / U, 4), top = ticks[ticks.length - 1] * U;
    var dp = ticks.reduce(function (m, t) { var s = String(t).split(".")[1]; return Math.max(m, s ? s.length : 0); }, 0);
    var n = rows.length, plotW = f.W - P.l - P.r, slot = plotW / n, bw = Math.max(2, Math.min(28, slot - 2));
    var X = function (i) { return P.l + slot * (i + 0.5); };
    var Y = function (v) { return f.H - P.b - v / top * (f.H - P.t - P.b); };
    ticks.forEach(function (t) {
      el("line", { x1: P.l, x2: f.W - P.r, y1: Y(t * U), y2: Y(t * U), "class": t === 0 ? "grid base" : "grid" }, f.svg);
      el("text", { x: P.l - 8, y: Y(t * U) + 4, "class": "tick", "text-anchor": "end" }, f.svg).textContent = t.toFixed(dp);
    });
    xTicks(f, rows, X);
    var bar = function (i, v, cls) {
      var y = Y(v), h = f.H - P.b - y, r = Math.min(4, bw / 2, h), x0 = X(i) - bw / 2, x1 = x0 + bw, yb = f.H - P.b;
      return el("path", { d: "M" + x0 + "," + yb + "V" + (y + r) + "Q" + x0 + "," + y + " " + (x0 + r) + "," + y + "H" + (x1 - r) + "Q" + x1 + "," + y + " " + x1 + "," + (y + r) + "V" + yb + "Z", "class": cls }, f.svg);
    };
    var groups = xs.map(function (x, i) {
      var g = [];
      if (x.off) g.push(bar(i, x.off, "dash-bar-off"));
      var sold = x.off && x.cbKg != null ? x.cbKg : x.kg;
      if (sold) g.push(bar(i, Math.min(sold, x.off || sold), "dash-bar" + (provisional(rows[i]) ? " prov" : "")));
      return g;
    });
    if (hasPv) {
      var d = "", pen = false;
      pv.forEach(function (v, i) { if (v == null) { pen = false; return; } d += (pen ? "L" : "M") + X(i).toFixed(1) + "," + Y(v).toFixed(1); pen = true; });
      el("path", { d: d, "class": "dash-line-prev" }, f.svg);
    }
    var hit = el("rect", { x: P.l, y: 0, width: plotW, height: f.H, fill: "transparent" }, f.svg), on = -1;
    var mark = function (i, add) { (groups[i] || []).forEach(function (b) { b.classList[add ? "add" : "remove"]("on"); }); };
    var move = function (evt) {
      var b = f.svg.getBoundingClientRect(), x = (evt.clientX - b.left) * f.W / b.width;
      var i = Math.max(0, Math.min(n - 1, Math.floor((x - P.l) / slot))), r = rows[i], v = xs[i];
      if (on !== i) { mark(on, false); mark(i, true); on = i; }
      var html = tipHead(r);
      if (v.off) html += tipRow("k-off", "Offered", kgFull(v.off) + " kg");
      var sold = v.off && v.cbKg != null ? v.cbKg : v.kg;
      html += tipRow("k-sold", "Sold", sold ? kgFull(sold) + " kg" : "None");
      if (v.abs != null) html += tipRow("", "Share sold", pct(v.abs));
      if (hasPv) html += tipRow("k-prev", "Sold " + (st.year - 1), pv[i] ? kgFull(pv[i]) + " kg" : "No sale " + r.n);
      showTip(evt, html);
    };
    hit.addEventListener("pointermove", move);
    hit.addEventListener("pointerdown", move);
    hit.addEventListener("pointerleave", function () { mark(on, false); on = -1; hideTip(); });
  }

  /* ---------- tables ---------- */
  var COLS = [
    { k: "sale", h: "Sale" }, { k: "date", h: "Date" }, { k: "p", h: "Avg.<br>US$/kg" }, { k: "ch", h: "Change" },
    { k: "off", h: "Offered<br>(kg)" }, { k: "kg", h: "Sold<br>(kg)" }, { k: "abs", h: "Share<br>sold" },
    { k: "prev", h: "Avg.<br>last yr", prev: true }, { k: "prevAbs", h: "Share sold<br>last yr", prev: true }
  ];
  function salesTable(rows) {
    var hasPrev = rows.some(function (r) { return lastYear(r.n); }), hasOff = rows.some(function (r) { return pick(r).off; });
    var cols = COLS.filter(function (c) { return (!c.prev || hasPrev) && ((c.k !== "off" && c.k !== "abs") || hasOff); });
    var data = rows.map(function (r, i) {
      var x = pick(r), j = i - 1, o = lastYear(r.n), ox = o ? pick(o) : {};
      while (j >= 0 && pick(rows[j]).p == null) j--;
      var before = j >= 0 ? pick(rows[j]).p : null;
      return { r: r, sale: r.n, date: r.date, p: x.p, kg: x.kg, off: x.off, abs: x.abs,
        ch: x.p != null && before != null ? x.p - before : null, prev: o ? ox.p : null, prevAbs: o ? ox.abs : null };
    });
    data.sort(function (a, b) {
      var A = a[st.sort], B = b[st.sort];
      if (A == null && B == null) return a.sale - b.sale;
      if (A == null || A === "") return 1; if (B == null || B === "") return -1;
      return (A < B ? -1 : A > B ? 1 : a.sale - b.sale) * st.dir;
    });
    var t = $("dash-table");
    $("dash-caption").textContent = TEA[st.tea] + ", " + st.year + ", sales " + st.from + " to " + st.to;
    t.tHead.innerHTML = "<tr>" + cols.map(function (c) {
      var s = st.sort === c.k ? (st.dir > 0 ? "ascending" : "descending") : "none";
      return '<th scope="col" aria-sort="' + s + '"><button type="button" class="dash-sort" data-k="' + c.k + '">' + '<span class="dash-h">' + c.h + "</span>" + '<span class="dash-arrow" aria-hidden="true">' + (s === "ascending" ? "▲" : s === "descending" ? "▼" : "") + "</span></button></th>";
    }).join("") + "</tr>";
    t.tBodies[0].innerHTML = !data.length ? '<tr><td colspan="' + cols.length + '" class="muted">' + noneText("No " + TEA[st.tea] + " sales in this run") + "</td></tr>" : data.map(function (d) {
      var cells = {
        sale: String(d.sale) + (provisional(d.r) ? '<sup class="dash-prov" title="Provisional: can change until Friday noon">*</sup>' : ""),
        date: d.date ? dShort(d.date) : "",
        p: d.p != null ? usd(d.p) : '<span class="muted">' + missing(d.r) + "</span>",
        ch: d.ch == null ? "" : '<span class="' + (d.ch > 0 ? "up" : d.ch < 0 ? "down" : "") + '">' + signed(d.ch, function (v) { return v.toFixed(2); }) + "</span>",
        off: d.off ? kgFull(d.off) : "", kg: d.kg ? kgFull(d.kg) : "", abs: d.abs != null ? pct(d.abs) : "",
        prev: d.prev != null ? usd(d.prev) : "", prevAbs: d.prevAbs != null ? pct(d.prevAbs) : ""
      };
      return "<tr>" + cols.map(function (c) { return "<td>" + cells[c.k] + "</td>"; }).join("") + "</tr>";
    }).join("");
    each("#dash-table .dash-sort", function (b) {
      b.addEventListener("click", function () {
        var k = b.getAttribute("data-k");
        if (st.sort === k) st.dir = -st.dir; else { st.sort = k; st.dir = k === "sale" || k === "date" ? 1 : -1; }
        salesTable(inRange());
        var nb = root.querySelector('#dash-table .dash-sort[data-k="' + k + '"]'); if (nb) nb.focus();
      });
    });
    $("dash-provisional").hidden = !rows.some(provisional);
  }

  /* The same run of sales in every year we hold. */
  function yearsTable() {
    $("dash-years-caption").textContent = TEA[st.tea] + ", sales " + st.from + " to " + st.to + " in each year";
    var out = [], prevAvg = null;
    years.forEach(function (y) {
      var rows = inRange(y);
      if (!rows.length) return;
      var t = totals(rows), ch = t.avg != null && prevAvg != null ? t.avg - prevAvg : null;
      out.push("<tr" + (y === st.year ? ' class="is-current"' : "") + "><td>" + y + (rows.length < st.to - st.from + 1 ? ' <span class="muted">(' + rows.length + " sales)</span>" : "") + "</td><td>" + (t.avg != null ? usd(t.avg) : "") +
        '</td><td><span class="' + (ch > 0 ? "up" : ch < 0 ? "down" : "") + '">' + (ch == null ? "" : signed(ch, function (v) { return v.toFixed(2); })) +
        "</span></td><td>" + (t.off ? mkg(t.off) : "") + "</td><td>" + (t.kg ? mkg(t.kg) : "") + "</td><td>" + (t.abs != null ? pct(t.abs) : "") + "</td></tr>");
      prevAvg = t.avg;
    });
    $("dash-years").tBodies[0].innerHTML = out.reverse().join("");
  }

  /* Top prices and grade averages for the last sale in the range, where Combrok's weekly report has them. */
  function highlightsPanel() {
    var box = $("dash-hl"), h = highlights[st.year + "-" + st.to];
    if (!h) { box.hidden = true; return; }
    box.hidden = false;
    var r = (byYear[st.year] || []).filter(function (x) { return x.n === st.to; })[0];
    $("dash-hl-h").textContent = "Sale " + st.to + ", " + (r && r.date ? dShort(r.date) + " " : "") + st.year + ": best prices and grade averages";
    var cents = function (v) { return v == null || v === "" ? "" : usd(+v / 100); };
    var top = (h.top_prices || []).map(function (t) {
      return "<li><b>" + cents(t.price_usc) + "</b> " + esc(t.mark || "") + " <span>" + esc([t.grade, t.country].filter(Boolean).join(", ")) + "</span></li>";
    }).join("");
    $("dash-hl-top").innerHTML = top || '<li class="muted">Not given for this sale</li>';
    var ga = h.grade_avgs || {}, groups = Object.keys(ga), grades = [];
    groups.forEach(function (g) { Object.keys(ga[g] || {}).forEach(function (k) { if (grades.indexOf(k) < 0) grades.push(k); }); });
    var nice = { EOR: "East of Rift", WOR: "West of Rift", KTDA: "KTDA factories", PLANTATIONS: "Plantations" };
    $("dash-hl-grades").innerHTML = groups.length ? "<thead><tr><th scope=\"col\">US$/kg</th>" + grades.map(function (g) { return '<th scope="col">' + esc(g) + "</th>"; }).join("") + "</tr></thead><tbody>" +
      groups.map(function (g) { return '<tr><th scope="row">' + esc(nice[g] || g.charAt(0) + g.slice(1).toLowerCase()) + "</th>" + grades.map(function (k) { return "<td>" + cents(ga[g][k]) + "</td>"; }).join("") + "</tr>"; }).join("") + "</tbody>" : "";
  }


  /* ---------- the long view since 1992: monthly averages to 2008, then every sale from 2009 ---------- */
  var wb = [], longSpan = "all";
  var mname = function (m) { return MON[+m.slice(5, 7) - 1] + " " + m.slice(0, 4); };
  // Points placed in time: months mid-month; sales by date, or by sale number (about one a week) where no date is saved.
  function longPts() {
    var out = wb.filter(function (d) { return d.m < "2009"; }).map(function (d) {
      return { t: +d.m.slice(0, 4) + (+d.m.slice(5, 7) - 0.5) / 12, v: d.v, y: +d.m.slice(0, 4), k: "m" + d.m.slice(5), lab: mname(d.m), kind: "Monthly average" };
    });
    years.forEach(function (y) {
      if (y < 2009) return;
      byYear[y].forEach(function (r) {
        if (r.all.p == null) return;
        var t = r.date ? y + (dateOf(r.date).getTime() - Date.UTC(y, 0, 1)) / (365.25 * 864e5) : y + (r.n - 0.5) / 52;
        out.push({ t: t, v: r.all.p, y: y, k: "s" + r.n, lab: label(r), kind: "Sale average" });
      });
    });
    return out.sort(function (a, b) { return a.t - b.t; });
  }
  function longChart() {
    var box = $("dash-long");
    if (!box) return;
    var every = longPts();
    if (every.length < 2) { box.hidden = true; return; }
    box.hidden = false;
    var lastYr = every[every.length - 1].y;
    var pts = longSpan === "all" ? every : every.filter(function (d) { return d.y > lastYr - +longSpan; });
    each("[data-span]", function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-span") === longSpan ? "true" : "false"); });
    var first = pts[0], last = pts[pts.length - 1];
    var hi = pts.reduce(function (a, d) { return d.v > a.v ? d : a; }), lo = pts.reduce(function (a, d) { return d.v < a.v ? d : a; });
    $("dash-long-stats").innerHTML =
      "<span><b>" + usd(last.v) + "</b> latest, " + last.lab + "</span>" +
      "<span><b>" + usd(first.v) + "</b> at the start, " + first.lab + "</span>" +
      "<span><b>" + usd(hi.v) + "</b> highest, " + hi.lab + "</span>" +
      "<span><b>" + usd(lo.v) + "</b> lowest, " + lo.lab + "</span>";
    var fig = $("dash-long-chart"), f = frame(fig, fig.clientWidth < 520 ? 220 : 280), P = f.P;
    var vs = pts.map(function (d) { return d.v; });
    var ticks = niceTicks(Math.min.apply(0, vs) - 0.05, Math.max.apply(0, vs) + 0.05, 5), y0 = ticks[0], y1 = ticks[ticks.length - 1];
    var n = pts.length, plotW = f.W - P.l - P.r, t0 = first.t, t1 = Math.max(last.t, t0 + 0.01);
    var X = function (t) { return P.l + (t - t0) / (t1 - t0) * plotW; };
    var Y = function (v) { return f.H - P.b - (v - y0) / (y1 - y0) * (f.H - P.t - P.b); };
    ticks.forEach(function (v) {
      el("line", { x1: P.l, x2: f.W - P.r, y1: Y(v), y2: Y(v), "class": "grid" }, f.svg);
      el("text", { x: P.l - 8, y: Y(v) + 4, "class": "tick", "text-anchor": "end" }, f.svg).textContent = "$" + v.toFixed(2);
    });
    var span = last.y - first.y, step = span > 24 ? 5 : span > 10 ? 2 : 1;
    for (var yr = Math.ceil(t0); yr <= t1; yr++) {
      if (yr % step) continue;
      var x = X(yr);
      if (x < P.l + 14 || x > f.W - P.r - 14) continue;
      el("line", { x1: x, x2: x, y1: f.H - P.b, y2: f.H - P.b + 4, "class": "grid" }, f.svg);
      el("text", { x: x, y: f.H - 8, "class": "tick", "text-anchor": "middle" }, f.svg).textContent = yr;
    }
    el("path", { d: pts.map(function (d, i) { return (i ? "L" : "M") + X(d.t).toFixed(1) + "," + Y(d.v).toFixed(1); }).join(""), "class": "dash-line thin" }, f.svg);
    el("circle", { cx: X(last.t), cy: Y(last.v), r: 4.5, "class": "dash-dot last" }, f.svg);
    var cross = el("line", { y1: P.t, y2: f.H - P.b, "class": "dash-cross", visibility: "hidden" }, f.svg);
    var ring = el("circle", { r: 5, "class": "dash-ring", visibility: "hidden" }, f.svg);
    var hit = el("rect", { x: P.l, y: 0, width: plotW, height: f.H, fill: "transparent" }, f.svg);
    var move = function (evt) {
      var b = f.svg.getBoundingClientRect(), x = (evt.clientX - b.left) * f.W / b.width, t = t0 + (x - P.l) / plotW * (t1 - t0);
      var i = 0; for (var j = 1; j < n; j++) if (Math.abs(pts[j].t - t) < Math.abs(pts[i].t - t)) i = j;
      var d = pts[i];
      cross.setAttribute("x1", X(d.t)); cross.setAttribute("x2", X(d.t)); cross.setAttribute("visibility", "visible");
      ring.setAttribute("cx", X(d.t)); ring.setAttribute("cy", Y(d.v)); ring.setAttribute("visibility", "visible");
      var yAgo = every.filter(function (o) { return o.y === d.y - 1 && o.k === d.k; })[0];
      showTip(evt, '<div class="dash-tip-h">' + d.lab + "</div>" + tipRow("k-cur", d.kind, usd(d.v) + "/kg") +
        (yAgo ? '<div class="dash-tip-note">' + signed(d.v - yAgo.v, usd) + " on " + yAgo.lab + "</div>" : ""));
    };
    hit.addEventListener("pointermove", move);
    hit.addEventListener("pointerdown", move);
    hit.addEventListener("pointerleave", function () { cross.setAttribute("visibility", "hidden"); ring.setAttribute("visibility", "hidden"); hideTip(); });
  }

  function draw() {
    longChart();
    var rows = inRange();
    lineChart("dash-price", "dash-legend", rows, function (r) { return pick(r).p; }, function (v) { return "$" + v.toFixed(2); }, function (v) { return usd(v) + (v > 0.5 ? "/kg" : ""); }, noneText("No published " + TEA[st.tea] + " average in these sales"), 0.03);
    lineChart("dash-abs", "dash-abs-legend", rows, function (r) { return pick(r).abs; }, function (v) { return Math.round(v * 100) + "%"; }, pct, noneText("No offered figures for these sales"), 0.02);
    kgChart(rows);
  }
  function update() {
    syncControls();
    var rows = inRange();
    stats(rows); draw(); salesTable(rows); yearsTable(); highlightsPanel(); saveUrl();
  }

  function start(data) {
    if (Array.isArray(data)) data = { eatta: data };
    build(data);
    wb = (data.worldbank || []).filter(function (d) { return d.month && d.usd_kg !== "" && d.usd_kg != null; })
      .map(function (d) { return { m: d.month, v: +d.usd_kg }; }).sort(function (a, b) { return a.m < b.m ? -1 : 1; });
    each("[data-span]", function (b) { b.addEventListener("click", function () { longSpan = b.getAttribute("data-span"); longChart(); }); });
    if (!years.length) throw new Error("no sales");
    var q = new URLSearchParams(location.search), y = +q.get("year");
    st.year = byYear[y] ? y : years[years.length - 1];
    var rows = byYear[st.year], nums = rows.map(function (r) { return r.n; });
    st.from = nums.indexOf(+q.get("from")) >= 0 ? +q.get("from") : rows[0].n;
    st.to = nums.indexOf(+q.get("to")) >= 0 ? +q.get("to") : rows[rows.length - 1].n;
    if (st.from > st.to) st.from = st.to;
    if (TEA[q.get("tea")]) st.tea = q.get("tea");
    st.cmp = q.get("compare") !== "no";
    wire(); update();
    root.classList.add("is-ready");
  }

  fetch(root.getAttribute("data-src"), { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(start)
    .catch(function () {
      $("dash-stats").innerHTML = '<p class="fine">The sales figures could not be loaded just now. Please refresh the page, or see the latest sales in the Mombasa section below.</p>';
    });
})();
