/* Mombasa auction dashboard (Markets page). Reads the EATTA sales saved in _data/mombasa_eatta_sales.csv,
   served as assets/data/mombasa-sales.json, and draws everything from it. Never estimates a missing figure. */
(function () {
  var root = document.getElementById("dashboard");
  if (!root) return;
  var NS = "http://www.w3.org/2000/svg";
  var $ = function (id) { return document.getElementById(id); };
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var TEA = { all: "All teas", ctc: "CTC", orthodox: "Orthodox" };
  var el = function (n, a, p) { var e = document.createElementNS(NS, n); for (var k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
  var usd = function (v) { return "$" + v.toFixed(2); };
  var mkg = function (kg) { return (kg / 1e6).toFixed(kg >= 1e7 ? 1 : 2); };
  var kgFull = function (kg) { return Math.round(kg).toLocaleString("en-GB"); };
  var dateOf = function (s) { var p = s.split("-"); return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])); };
  var dShort = function (s) { if (!s) return "Not given"; var d = dateOf(s); return d.getUTCDate() + " " + MON[d.getUTCMonth()]; };
  var dLong = function (s) { return s ? dShort(s) + " " + s.slice(0, 4) : "Not given"; };
  var num = function (v) { return v === "" || v == null ? null : +v; };

  var sales = [], byYear = {}, years = [];
  var st = { year: null, from: null, to: null, tea: "all", sort: "sale", dir: 1 };

  // Final after the Friday noon (Nairobi, 09:00 UTC) following the sale.
  function provisional(r) {
    if (!r.date) return false;
    var d = dateOf(r.date), add = (5 - d.getUTCDay() + 7) % 7;
    return Date.now() < d.getTime() + add * 864e5 + 9 * 36e5;
  }
  function pick(r) {
    if (st.tea === "ctc") return { p: r.ctcP, kg: r.ctcKg };
    if (st.tea === "orthodox") return { p: r.orP, kg: r.orKg };
    return { p: r.p, kg: r.kg };
  }
  function inRange() {
    return (byYear[st.year] || []).filter(function (r) { return r.n >= st.from && r.n <= st.to; });
  }
  function lastYear(n) {
    var prev = byYear[st.year - 1];
    if (!prev) return null;
    for (var i = 0; i < prev.length; i++) if (prev[i].n === n) return prev[i];
    return null;
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
    Array.prototype.forEach.call(root.querySelectorAll("[data-tea]"), function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-tea") === st.tea ? "true" : "false"); });
  }
  function setYear(y) {
    st.year = y;
    var rows = byYear[y];
    st.from = rows[0].n; st.to = rows[rows.length - 1].n;
  }
  function saveUrl() {
    if (!window.history || !history.replaceState) return;
    var q = new URLSearchParams(location.search);
    q.set("year", st.year); q.set("from", st.from); q.set("to", st.to);
    if (st.tea === "all") q.delete("tea"); else q.set("tea", st.tea);
    history.replaceState(null, "", location.pathname + "?" + q.toString() + location.hash);
  }
  function wire() {
    $("dash-year").addEventListener("change", function () { setYear(+this.value); update(); });
    $("dash-from").addEventListener("change", function () { st.from = +this.value; if (st.to < st.from) st.to = st.from; update(); });
    $("dash-to").addEventListener("change", function () { st.to = +this.value; if (st.from > st.to) st.from = st.to; update(); });
    Array.prototype.forEach.call(root.querySelectorAll("[data-tea]"), function (b) {
      b.addEventListener("click", function () { st.tea = b.getAttribute("data-tea"); update(); });
    });
    Array.prototype.forEach.call(root.querySelectorAll("[data-last]"), function (b) {
      b.addEventListener("click", function () {
        var rows = byYear[st.year], k = b.getAttribute("data-last");
        st.to = rows[rows.length - 1].n;
        st.from = k === "all" ? rows[0].n : rows[Math.max(0, rows.length - +k)].n;
        update();
      });
    });
    var resizeT;
    window.addEventListener("resize", function () { clearTimeout(resizeT); resizeT = setTimeout(draw, 150); });
  }

  /* ---------- headline figures ---------- */
  function stats(rows) {
    var box = $("dash-stats"), withP = rows.filter(function (r) { return pick(r).p != null; });
    var tile = function (label, value, note) {
      return '<div class="stat"><span class="stat-label">' + label + "</span><strong>" + value + '</strong><span class="stat-note">' + note + "</span></div>";
    };
    if (!withP.length) { box.innerHTML = tile("Average price", "None", TEA[st.tea] + " had no published average in these sales"); return; }
    var kg = 0, val = 0;
    withP.forEach(function (r) { var x = pick(r); if (x.kg) { kg += x.kg; val += x.kg * x.p; } });
    var avg = kg ? val / kg : withP.reduce(function (s, r) { return s + pick(r).p; }, 0) / withP.length;
    var hi = withP.reduce(function (a, r) { return pick(r).p > pick(a).p ? r : a; });
    var lo = withP.reduce(function (a, r) { return pick(r).p < pick(a).p ? r : a; });
    var first = withP[0], last = withP[withP.length - 1], ch = pick(last).p - pick(first).p;
    var span = withP.length === 1 ? "Sale " + first.n : "Sales " + first.n + " to " + last.n;
    var cmp = "";
    var prevRows = withP.map(function (r) { return lastYear(r.n); }).filter(function (r) { return r && pick(r).p != null; });
    if (prevRows.length === withP.length) {
      var pk = 0, pv = 0;
      prevRows.forEach(function (r) { var x = pick(r); pk += x.kg || 0; pv += (x.kg || 0) * x.p; });
      if (pk) { var d = avg - pv / pk; cmp = ", " + (d >= 0 ? "up " : "down ") + usd(Math.abs(d)) + " on the same sales in " + (st.year - 1); }
    }
    box.innerHTML =
      tile("Average price", usd(avg), span + ", " + TEA[st.tea].toLowerCase() + cmp) +
      tile("Tea sold", kg >= 1e6 ? mkg(kg) + "<small> m kg</small>" : Math.round(kg / 1e3).toLocaleString("en-GB") + "<small> thousand kg</small>", withP.length + (withP.length === 1 ? " sale" : " sales")) +
      tile("Highest sale", usd(pick(hi).p), "Sale " + hi.n + ", " + dLong(hi.date) + "; lowest " + usd(pick(lo).p) + " at sale " + lo.n) +
      tile(ch > 0 ? "Up over the run" : ch < 0 ? "Down over the run" : "Change over the run", usd(Math.abs(ch)), "From " + usd(pick(first).p) + " at sale " + first.n + " to " + usd(pick(last).p) + " at sale " + last.n);
  }

  /* ---------- charts ---------- */
  var tip = $("dash-tip");
  tip.setAttribute("aria-hidden", "true");
  tip.removeAttribute("role");
  function showTip(evt, html) {
    tip.innerHTML = html; tip.hidden = false;
    var r = root.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    var x = evt.clientX - r.left + 14, y = evt.clientY - r.top - h - 12;
    if (x + w > r.width - 8) x = evt.clientX - r.left - w - 14;
    if (y < 0) y = evt.clientY - r.top + 18;
    tip.style.left = Math.max(8, x) + "px"; tip.style.top = y + "px";
  }
  var hideTip = function () { tip.hidden = true; };
  var tipRow = function (cls, label, value) { return '<div class="dash-tip-row"><i class="' + cls + '"></i>' + label + "<b>" + value + "</b></div>"; };

  function frame(fig, H) {
    fig.innerHTML = "";
    var W = Math.max(300, Math.round(fig.clientWidth || 600));
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, "aria-hidden": "true" }, fig);
    return { svg: svg, W: W, H: H, P: { l: 46, r: 12, t: 10, b: 28 } };
  }
  function xTicks(f, rows, X) {
    var n = rows.length, step = Math.max(1, Math.ceil(n / Math.max(2, Math.floor((f.W - 60) / 56))));
    rows.forEach(function (r, i) {
      if (i % step && i !== n - 1) return;
      if (i !== n - 1 && n - 1 - i < step * 0.6) return;
      el("text", { x: X(i), y: f.H - 8, "class": "tick", "text-anchor": n === 1 ? "middle" : i === 0 ? "start" : i === n - 1 ? "end" : "middle" }, f.svg).textContent = r.n;
    });
    el("text", { x: f.P.l - 8, y: f.H - 8, "class": "tick", "text-anchor": "end" }, f.svg).textContent = "Sale";
  }
  function niceTicks(lo, hi, count) {
    var span = hi - lo || 1, raw = span / count, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var step = [1, 2, 2.5, 5, 10].map(function (m) { return m * mag; }).filter(function (s) { return s >= raw; })[0];
    var out = [], v = Math.floor(lo / step) * step;
    for (; v <= hi + step * 0.001; v += step) out.push(+v.toFixed(6));
    if (out[out.length - 1] < hi) out.push(+(out[out.length - 1] + step).toFixed(6));
    return out;
  }

  function priceChart(rows) {
    var fig = $("dash-price"), f = frame(fig, fig.clientWidth < 520 ? 230 : 280), P = f.P;
    var cur = rows.map(function (r) { return pick(r).p; });
    var prev = rows.map(function (r) { var o = lastYear(r.n); return o ? pick(o).p : null; });
    var hasPrev = prev.some(function (v) { return v != null; });
    var all = cur.concat(prev).filter(function (v) { return v != null; });
    var leg = $("dash-legend");
    leg.hidden = !hasPrev;
    if (hasPrev) leg.innerHTML = '<span><i class="k-cur"></i>' + st.year + '</span><span><i class="k-prev"></i>' + (st.year - 1) + ", same sale</span>";
    if (!all.length) { el("text", { x: f.W / 2, y: f.H / 2, "class": "tick", "text-anchor": "middle" }, f.svg).textContent = "No published " + TEA[st.tea] + " average in these sales"; return; }
    var lo = Math.min.apply(0, all), hi = Math.max.apply(0, all), pad = Math.max((hi - lo) * 0.12, 0.03);
    var ticks = niceTicks(lo - pad, hi + pad, 4), y0 = ticks[0], y1 = ticks[ticks.length - 1];
    var n = rows.length, plotW = f.W - P.l - P.r;
    var X = function (i) { return n === 1 ? P.l + plotW / 2 : P.l + i / (n - 1) * plotW; };
    var Y = function (v) { return f.H - P.b - (v - y0) / (y1 - y0) * (f.H - P.t - P.b); };
    ticks.forEach(function (v) {
      el("line", { x1: P.l, x2: f.W - P.r, y1: Y(v), y2: Y(v), "class": "grid" }, f.svg);
      el("text", { x: P.l - 8, y: Y(v) + 4, "class": "tick", "text-anchor": "end" }, f.svg).textContent = "$" + v.toFixed(2);
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
    cur.forEach(function (v, i) {
      if (v == null) return;
      if (dots || i === n - 1) el("circle", { cx: X(i), cy: Y(v), r: i === n - 1 ? 5 : 4, "class": "dash-dot" + (i === n - 1 ? " last" : "") }, f.svg);
    });
    var li = -1; for (var k = n - 1; k >= 0; k--) if (cur[k] != null) { li = k; break; }
    if (li >= 0) el("text", { x: Math.min(X(li), f.W - P.r), y: Y(cur[li]) - 12, "class": "tick strong dash-halo", "text-anchor": n === 1 ? "middle" : "end" }, f.svg).textContent = usd(cur[li]);
    // Hover: crosshair snaps to the nearest sale.
    var cross = el("line", { y1: P.t, y2: f.H - P.b, "class": "dash-cross", visibility: "hidden" }, f.svg);
    var ring = el("circle", { r: 6, "class": "dash-ring", visibility: "hidden" }, f.svg);
    var hit = el("rect", { x: P.l - 10, y: 0, width: plotW + 20, height: f.H, fill: "transparent" }, f.svg);
    var move = function (evt) {
      var b = f.svg.getBoundingClientRect(), x = (evt.clientX - b.left) * f.W / b.width;
      var i = n === 1 ? 0 : Math.max(0, Math.min(n - 1, Math.round((x - P.l) / plotW * (n - 1))));
      var r = rows[i], v = cur[i];
      cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.setAttribute("visibility", "visible");
      if (v != null) { ring.setAttribute("cx", X(i)); ring.setAttribute("cy", Y(v)); ring.setAttribute("visibility", "visible"); } else ring.setAttribute("visibility", "hidden");
      var html = '<div class="dash-tip-h">Sale ' + r.n + " · " + dLong(r.date) + (provisional(r) ? " · provisional" : "") + "</div>" +
        tipRow("k-cur", hasPrev ? String(st.year) : TEA[st.tea], v != null ? usd(v) + "/kg" : "Not published");
      if (hasPrev) html += tipRow("k-prev", String(st.year - 1), prev[i] != null ? usd(prev[i]) + "/kg" : "No sale " + r.n);
      var pj = i - 1; while (pj >= 0 && cur[pj] == null) pj--;
      if (pj >= 0 && v != null) { var c = v - cur[pj]; html += '<div class="dash-tip-note">' + (c > 0 ? "Up " : c < 0 ? "Down " : "Level, ") + (c ? usd(Math.abs(c)) : "") + " on sale " + rows[pj].n + "</div>"; }
      showTip(evt, html);
    };
    hit.addEventListener("pointermove", move);
    hit.addEventListener("pointerdown", move);
    hit.addEventListener("pointerleave", function () { cross.setAttribute("visibility", "hidden"); ring.setAttribute("visibility", "hidden"); hideTip(); });
  }

  function kgChart(rows) {
    var fig = $("dash-kg"), f = frame(fig, fig.clientWidth < 520 ? 200 : 240), P = f.P;
    var vals = rows.map(function (r) { return pick(r).kg; });
    var max = Math.max.apply(0, vals.filter(function (v) { return v != null; }).concat([0]));
    if (!max) { el("text", { x: f.W / 2, y: f.H / 2, "class": "tick", "text-anchor": "middle" }, f.svg).textContent = "No " + TEA[st.tea] + " sold in these sales"; return; }
    var U = max < 1e6 ? 1e3 : 1e6;
    $("dash-kg-u").textContent = U === 1e3 ? "thousand kg" : "million kg";
    var ticks = niceTicks(0, max / U, 4), top = ticks[ticks.length - 1] * U, dp = ticks.reduce(function (m, t) { var f = String(t).split(".")[1]; return Math.max(m, f ? f.length : 0); }, 0);
    var n = rows.length, plotW = f.W - P.l - P.r, slot = plotW / n, bw = Math.max(2, Math.min(28, slot - 2));
    var X = function (i) { return P.l + slot * (i + 0.5); };
    var Y = function (v) { return f.H - P.b - v / top * (f.H - P.t - P.b); };
    ticks.forEach(function (t) {
      el("line", { x1: P.l, x2: f.W - P.r, y1: Y(t * U), y2: Y(t * U), "class": t === 0 ? "grid base" : "grid" }, f.svg);
      el("text", { x: P.l - 8, y: Y(t * U) + 4, "class": "tick", "text-anchor": "end" }, f.svg).textContent = t.toFixed(dp);
    });
    xTicks(f, rows, X);
    var bars = vals.map(function (v, i) {
      if (!v) return null;
      var y = Y(v), h = f.H - P.b - y, r = Math.min(4, bw / 2, h);
      var x0 = X(i) - bw / 2, x1 = x0 + bw, yb = f.H - P.b;
      // Rounded at the data end only, square on the baseline.
      var d = "M" + x0 + "," + yb + "V" + (y + r) + "Q" + x0 + "," + y + " " + (x0 + r) + "," + y + "H" + (x1 - r) + "Q" + x1 + "," + y + " " + x1 + "," + (y + r) + "V" + yb + "Z";
      return el("path", { d: d, "class": "dash-bar" + (provisional(rows[i]) ? " prov" : "") }, f.svg);
    });
    var hit = el("rect", { x: P.l, y: 0, width: plotW, height: f.H, fill: "transparent" }, f.svg), on = -1;
    var move = function (evt) {
      var b = f.svg.getBoundingClientRect(), x = (evt.clientX - b.left) * f.W / b.width;
      var i = Math.max(0, Math.min(n - 1, Math.floor((x - P.l) / slot))), r = rows[i];
      if (on !== i) { if (bars[on]) bars[on].classList.remove("on"); if (bars[i]) bars[i].classList.add("on"); on = i; }
      showTip(evt, '<div class="dash-tip-h">Sale ' + r.n + " · " + dLong(r.date) + (provisional(r) ? " · provisional" : "") + "</div>" +
        tipRow("k-bar", TEA[st.tea] + " sold", vals[i] ? kgFull(vals[i]) + " kg" : "None"));
    };
    hit.addEventListener("pointermove", move);
    hit.addEventListener("pointerdown", move);
    hit.addEventListener("pointerleave", function () { if (bars[on]) bars[on].classList.remove("on"); on = -1; hideTip(); });
  }

  /* ---------- table ---------- */
  var COLS = [
    { k: "sale", h: "Sale" }, { k: "date", h: "Date" }, { k: "p", h: "Average US$/kg" },
    { k: "ch", h: "Change" }, { k: "kg", h: "Sold (kg)" }, { k: "prev", h: "Same sale last year", prev: true }
  ];
  function table(rows) {
    var hasPrev = rows.some(function (r) { return lastYear(r.n); });
    var cols = COLS.filter(function (c) { return !c.prev || hasPrev; });
    var data = rows.map(function (r, i) {
      var x = pick(r), j = i - 1, o = lastYear(r.n);
      while (j >= 0 && pick(rows[j]).p == null) j--;
      var before = j >= 0 ? pick(rows[j]).p : null;
      return { r: r, sale: r.n, date: r.date, p: x.p, kg: x.kg, ch: x.p != null && before != null ? x.p - before : null, prev: o ? pick(o).p : null };
    });
    data.sort(function (a, b) {
      var A = a[st.sort], B = b[st.sort];
      if (A == null && B == null) return a.sale - b.sale;
      if (A == null) return 1; if (B == null) return -1;
      return (A < B ? -1 : A > B ? 1 : a.sale - b.sale) * st.dir;
    });
    var t = $("dash-table");
    $("dash-caption").textContent = TEA[st.tea] + ", " + st.year + ", sales " + st.from + " to " + st.to;
    t.tHead.innerHTML = "<tr>" + cols.map(function (c) {
      var s = st.sort === c.k ? (st.dir > 0 ? "ascending" : "descending") : "none";
      return '<th scope="col" aria-sort="' + s + '"><button type="button" class="dash-sort" data-k="' + c.k + '">' + c.h + '<span class="dash-arrow" aria-hidden="true">' + (s === "ascending" ? "▲" : s === "descending" ? "▼" : "") + "</span></button></th>";
    }).join("") + "</tr>";
    t.tBodies[0].innerHTML = data.map(function (d) {
      var cells = {
        sale: String(d.sale) + (provisional(d.r) ? ' <span class="dash-badge">Provisional</span>' : ""),
        date: dShort(d.date),
        p: d.p != null ? usd(d.p) : '<span class="muted">Not published</span>',
        ch: d.ch == null ? "" : '<span class="' + (d.ch > 0 ? "up" : d.ch < 0 ? "down" : "") + '">' + (d.ch > 0 ? "+" : d.ch < 0 ? "−" : "") + Math.abs(d.ch).toFixed(2) + "</span>",
        kg: d.kg ? kgFull(d.kg) : "",
        prev: d.prev != null ? usd(d.prev) : ""
      };
      return "<tr>" + cols.map(function (c) { return "<td>" + cells[c.k] + "</td>"; }).join("") + "</tr>";
    }).join("");
    Array.prototype.forEach.call(t.querySelectorAll(".dash-sort"), function (b) {
      b.addEventListener("click", function () {
        var k = b.getAttribute("data-k");
        if (st.sort === k) st.dir = -st.dir; else { st.sort = k; st.dir = k === "sale" || k === "date" ? 1 : -1; }
        table(inRange());
        var nb = t.querySelector('.dash-sort[data-k="' + k + '"]'); if (nb) nb.focus();
      });
    });
    $("dash-provisional").hidden = !rows.some(provisional);
  }

  function draw() { var rows = inRange(); priceChart(rows); kgChart(rows); }
  function update() { syncControls(); var rows = inRange(); stats(rows); draw(); table(rows); saveUrl(); }

  function start(raw) {
    sales = raw.map(function (r) {
      return { y: +r.year, n: +r.sale, date: r.auction_date || "", p: num(r.avg_usd_kg), kg: num(r.sold_kg),
        ctcP: num(r.ctc_avg_usd_kg), ctcKg: num(r.ctc_sold_kg), orP: num(r.orthodox_avg_usd_kg), orKg: num(r.orthodox_sold_kg) };
    }).filter(function (r) { return r.y && r.n; }).sort(function (a, b) { return a.y - b.y || a.n - b.n; });
    if (!sales.length) throw new Error("no sales");
    sales.forEach(function (r) { (byYear[r.y] = byYear[r.y] || []).push(r); });
    years = Object.keys(byYear).map(Number).sort();
    var q = new URLSearchParams(location.search), y = +q.get("year");
    setYear(byYear[y] ? y : years[years.length - 1]);
    var nums = byYear[st.year].map(function (r) { return r.n; });
    if (nums.indexOf(+q.get("from")) >= 0) st.from = +q.get("from");
    if (nums.indexOf(+q.get("to")) >= 0) st.to = +q.get("to");
    if (st.from > st.to) st.from = st.to;
    if (TEA[q.get("tea")]) st.tea = q.get("tea");
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
