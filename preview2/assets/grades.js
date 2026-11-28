/* Detailed statistics: average price by grade and origin at each Mombasa sale (Auctions page, behind the free sign-up).
   Data: assets/data/grades/<year>.json, rows [sale, date, origin, grade, sold_kg, avg_usc|null, offered_kg]. */
(function () {
  var root = document.getElementById("grades");
  if (!root) return;
  var base = root.dataset.base, years = root.dataset.years.split(",").sort();
  var ORIGINS = [["KE", "Kenya, all"], ["KE-E", "East of Rift, small-scale"], ["KE-W", "West of Rift, small-scale"],
    ["KE-P", "Plantations"], ["UG", "Uganda"], ["RW", "Rwanda"], ["TZ", "Tanzania"], ["BI", "Burundi"], ["OTHER", "Other origins"]];
  var SHORT = { "KE-E": "Kenya east", "KE-W": "Kenya west", "KE-P": "Plantations", UG: "Uganda", RW: "Rwanda" };
  var LINES = [["KE-E", "#257de0"], ["KE-W", "#f47230"], ["KE-P", "#00b894"], ["UG", "#f2a600"], ["RW", "#ee7fac"]];
  var SETS = { main: ["BP1", "PF1", "PD", "DUST1"], other: ["BP", "PF", "DUST", "FNGS1", "FNGS", "BMF"] };
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var cache = {}, state = { year: years[years.length - 1], sale: null, set: "main", grade: "PF1" };
  var $ = function (s) { return root.querySelector(s); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); };
  var day = function (d) { var p = d.split("-"); return +p[2] + " " + MONTHS[+p[1] - 1]; };
  var usd = function (c) { return "$" + (c / 100).toFixed(2); };
  var kg = function (k) { return k >= 1e6 ? (k / 1e6).toFixed(2) + "M kg" : Math.round(k / 1000) + "k kg"; };

  function load(y) {
    if (cache[y]) return Promise.resolve(cache[y]);
    return fetch(base + y + ".json").then(function (r) { return r.json(); }).then(function (rows) {
      var sales = {}, order = [];
      rows.forEach(function (r) {
        var s = sales[r[0]] || (sales[r[0]] = { sale: r[0], date: r[1], p: {} });
        if (order.indexOf(r[0]) < 0) order.push(r[0]);
        s.p[r[2] + "|" + r[3]] = { kg: r[4], usc: r[5], off: r[6] };
      });
      order.sort(function (a, b) { return a - b; });
      return (cache[y] = order.map(function (n) { return sales[n]; }));
    });
  }

  function fillSelect(sel, items, value) {
    sel.innerHTML = items.map(function (i) { return '<option value="' + i[0] + '"' + (String(i[0]) === String(value) ? " selected" : "") + ">" + esc(i[1]) + "</option>"; }).join("");
  }

  function table(sales) {
    var i = sales.findIndex(function (s) { return s.sale === state.sale; }), s = sales[i], prev = sales[i - 1], grades = SETS[state.set];
    var h = '<table class="data-table grade-table"><caption>Sale ' + s.sale + ", " + day(s.date) + " " + state.year + ": average price, US$ per kg</caption><thead><tr><th>Origin</th>" +
      grades.map(function (g) { return "<th>" + g + "</th>"; }).join("") + "</tr></thead><tbody>";
    ORIGINS.forEach(function (o) {
      var cells = grades.map(function (g) {
        var c = s.p[o[0] + "|" + g], p = prev && prev.p[o[0] + "|" + g];
        if (!c || c.usc == null) return '<td class="nil">–</td>';
        var ch = "";
        if (p && p.usc != null) {
          var d = Math.round(c.usc - p.usc);
          ch = d === 0 ? '<small class="flat">no change</small>' : '<small class="' + (d > 0 ? "up" : "down") + '">' + (d > 0 ? "▲ " : "▼ ") + Math.abs(d) + "¢</small>";
        }
        return '<td title="' + kg(c.kg) + " sold of " + kg(c.off) + ' offered">' + usd(c.usc) + ch + "</td>";
      }).join("");
      h += '<tr class="' + (o[0] === "KE" ? "total" : o[0].indexOf("KE-") === 0 ? "sub" : "") + '"><th scope="row">' + esc(o[1]) + "</th>" + cells + "</tr>";
    });
    $(".grade-table-wrap").innerHTML = h + "</tbody></table>";
    $(".grade-table-note").textContent = prev ? "Arrows show the change since sale " + prev.sale + ". Hover a price for the kilos sold and offered." : "Hover a price for the kilos sold and offered.";
  }

  function chart(sales) {
    var W = 720, H = 300, L = 44, R = 92, T = 12, B = 28, g = state.grade;
    var pts = LINES.map(function (l) { return { o: l[0], c: l[1], v: sales.map(function (s) { var c = s.p[l[0] + "|" + g]; return c && c.usc != null ? c.usc : null; }) }; });
    var all = [].concat.apply([], pts.map(function (p) { return p.v; })).filter(function (v) { return v != null; });
    if (!all.length) { $(".grade-chart").innerHTML = '<p class="chart-note">No ' + g + " sold this year.</p>"; return; }
    var lo = Math.floor(Math.min.apply(null, all) / 25) * 25, hi = Math.ceil(Math.max.apply(null, all) / 25) * 25;
    var x = function (i) { return L + (sales.length < 2 ? 0 : i * (W - L - R) / (sales.length - 1)); };
    var y = function (v) { return T + (hi - v) * (H - T - B) / (hi - lo || 1); };
    var step = (hi - lo) > 200 ? 50 : 25, svg = "";
    for (var v = lo; v <= hi; v += step) svg += '<line class="grid" x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '"/><text class="tick" x="' + (L - 6) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + usd(v) + "</text>";
    sales.forEach(function (s, i) { if (i === 0 || i === sales.length - 1 || i % 8 === 0) svg += '<text class="tick" x="' + x(i) + '" y="' + (H - 8) + '" text-anchor="middle">' + s.sale + "</text>"; });
    var labels = [];
    pts.forEach(function (p) {
      var d = "", pen = false;
      p.v.forEach(function (v, i) { if (v == null) { pen = false; return; } d += (pen ? "L" : "M") + x(i).toFixed(1) + " " + y(v).toFixed(1); pen = true; });
      svg += '<path d="' + d + '" fill="none" stroke="' + p.c + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>';
      for (var i = p.v.length - 1; i >= 0; i--) if (p.v[i] != null) { labels.push({ y: y(p.v[i]), t: SHORT[p.o], c: p.c }); break; }
    });
    labels.sort(function (a, b) { return a.y - b.y; });
    for (var k = 1; k < labels.length; k++) if (labels[k].y - labels[k - 1].y < 14) labels[k].y = labels[k - 1].y + 14;
    labels.forEach(function (l) { svg += '<text class="tick strong dash-halo" x="' + (W - R + 8) + '" y="' + (l.y + 4) + '">' + l.t + "</text>"; });
    svg += '<line class="dash-cross" x1="0" x2="0" y1="' + T + '" y2="' + (H - B) + '" visibility="hidden"/><rect class="hit" x="' + L + '" y="0" width="' + (W - L - R) + '" height="' + H + '" fill="transparent"/>';
    var fig = $(".grade-chart");
    fig.innerHTML = '<div class="dash-legend">' + LINES.map(function (l) { return '<span><i class="k-line" style="border-top-color:' + l[1] + '"></i>' + SHORT[l[0]] + "</span>"; }).join("") +
      '</div><svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + g + ' average price at each sale in ' + state.year + ' by origin">' + svg + '</svg><div class="dash-tip" hidden></div>';
    var el = fig.querySelector("svg"), tip = fig.querySelector(".dash-tip"), cross = el.querySelector(".dash-cross");
    el.querySelector(".hit").addEventListener("pointermove", function (e) {
      var r = el.getBoundingClientRect(), px = (e.clientX - r.left) * W / r.width;
      var i = Math.max(0, Math.min(sales.length - 1, Math.round((px - L) / ((W - L - R) / Math.max(1, sales.length - 1)))));
      cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("visibility", "visible");
      tip.innerHTML = '<div class="dash-tip-h">Sale ' + sales[i].sale + ", " + day(sales[i].date) + "</div>" + pts.map(function (p) {
        return '<div class="dash-tip-row"><i class="k-line" style="border-top-color:' + p.c + '"></i>' + SHORT[p.o] + " <b>" + (p.v[i] == null ? "–" : usd(p.v[i])) + "</b></div>"; }).join("");
      tip.hidden = false;
      var left = x(i) * r.width / W; tip.style.left = Math.min(left + 12, r.width - 170) + "px"; tip.style.top = "40px";
    });
    el.querySelector(".hit").addEventListener("pointerleave", function () { tip.hidden = true; cross.setAttribute("visibility", "hidden"); });
  }

  function draw() {
    load(state.year).then(function (sales) {
      if (!sales.some(function (s) { return s.sale === state.sale; })) state.sale = sales[sales.length - 1].sale;
      fillSelect($("[name=g-sale]"), sales.map(function (s) { return [s.sale, "Sale " + s.sale + " · " + day(s.date)]; }), state.sale);
      root.querySelectorAll("[data-set]").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.set === state.set); });
      table(sales);
      $(".grade-chart-h").textContent = state.grade + " through " + state.year;
      chart(sales);
    });
  }

  fillSelect($("[name=g-year]"), years.slice().reverse().map(function (y) { return [y, y]; }), state.year);
  fillSelect($("[name=g-grade]"), SETS.main.concat(SETS.other).map(function (g) { return [g, g]; }), state.grade);
  $("[name=g-year]").addEventListener("change", function (e) { state.year = e.target.value; state.sale = null; draw(); });
  $("[name=g-sale]").addEventListener("change", function (e) { state.sale = +e.target.value; draw(); });
  $("[name=g-grade]").addEventListener("change", function (e) { state.grade = e.target.value; draw(); });
  root.querySelectorAll("[data-set]").forEach(function (b) { b.addEventListener("click", function () { state.set = b.dataset.set; draw(); }); });
  draw();
})();
