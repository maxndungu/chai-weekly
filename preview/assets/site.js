/* Chai Weekly: small enhancements. Every page works without this file. */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  function say(el, text, kind) {
    if (!el) return;
    el.textContent = text;
    el.className = el.className.replace(/\bis-(ok|error|info)\b/g, "").trim() + (kind ? " is-" + kind : "");
  }

  /* Mobile menu */
  var toggle = $(".nav-toggle"), nav = $("#site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      nav.classList.toggle("is-open", !open);
      if (!open) { var first = $("a", nav); if (first) first.focus(); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) {
        toggle.setAttribute("aria-expanded", "false"); nav.classList.toggle("is-open", false); toggle.focus();
      }
    });
  }

  /* Subscribe form: check the address, then hand over to the mailing-list provider in a new tab.
     We never claim someone is subscribed: the provider confirms that by email. */
  $$(".subscribe-form").forEach(function (form) {
    var input = $("input[type=email]", form), msg = $(".form-msg", form), provider = form.getAttribute("data-provider");
    input.addEventListener("input", function () { input.setAttribute("aria-invalid", "false"); say(msg, ""); });
    form.addEventListener("submit", function (e) {
      var v = input.value.trim();
      if (!v) { e.preventDefault(); input.setAttribute("aria-invalid", "true"); say(msg, "Please enter your email address.", "error"); input.focus(); return; }
      if (!EMAIL.test(v)) { e.preventDefault(); input.setAttribute("aria-invalid", "true"); say(msg, "That doesn't look like a full email address. Please check it, for example name@example.com.", "error"); input.focus(); return; }
      if (provider === "none") {
        e.preventDefault();
        say(msg, "Sign-up isn't open yet, so your address has not been saved. Please check back soon.", "info");
        return;
      }
      input.value = v;
      var name = provider === "buttondown" ? "Buttondown" : provider === "substack" ? "Substack" : "Our mailing list";
      say(msg, "Almost done: " + name + " has opened in a new tab. To finish, confirm there, then click the link in the email it sends you.", "ok");
    });
  });

  /* Contact and story form */
  var sf = $("#story-form");
  if (sf) {
    var smsg = $("#sf-msg");
    var label = function (f) { var l = sf.querySelector("label[for='" + f.id + "']"); return l ? l.childNodes[0].textContent.trim() : "this field"; };
    sf.addEventListener("submit", function (e) {
      var bad = null, why = "";
      $$("[required]", sf).forEach(function (f) {
        var ok = f.type === "checkbox" ? f.checked : f.value.trim().length >= (+f.getAttribute("minlength") || 1);
        if (f.id === "sf-contact" && ok) { var v = f.value.trim(); ok = EMAIL.test(v) || /^[+\d][\d\s()-]{6,}$/.test(v); }
        f.setAttribute("aria-invalid", ok ? "false" : "true");
        if (!ok && !bad) bad = f;
      });
      var link = $("#sf-link");
      if (link && link.value && !/^https?:\/\/\S+\.\S+/.test(link.value)) { link.setAttribute("aria-invalid", "true"); if (!bad) { bad = link; } }
      var file = $("#sf-photo");
      if (!bad && file && file.files && file.files[0] && file.files[0].size > 5 * 1024 * 1024) { file.setAttribute("aria-invalid", "true"); bad = file; why = "That file is over 5 MB. Please send a smaller photo, or a link to it."; }
      if (bad) {
        e.preventDefault();
        if (!why) {
          why = bad.type === "checkbox" ? "Please tick the box to confirm the message is your own." :
            "Please check: " + label(bad) + (bad.id === "sf-contact" ? " (an email address or a phone number)" : bad.id === "sf-story" ? " (at least a sentence or two)" : bad.id === "sf-link" ? " (a full link starting with https://)" : "") + ".";
        }
        say(smsg, why, "error"); bad.focus(); return;
      }
      if (sf.getAttribute("data-configured") !== "yes") {
        e.preventDefault();
        say(smsg, "The form isn't connected yet, so this message has not been sent. Please reply to any Chai Weekly email instead.", "info");
        return;
      }
      say(smsg, "Sending…", "info");
    });
    $$("input, textarea, select", sf).forEach(function (f) { f.addEventListener("input", function () { f.setAttribute("aria-invalid", "false"); }); });
  }

  /* Share buttons */
  $$(".share").forEach(function (box) {
    var m = $(".share-msg", box), copy = $(".share-copy", box), nat = $(".share-native", box);
    if (copy) copy.addEventListener("click", function () {
      var url = copy.getAttribute("data-url");
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { say(m, "Link copied.", "ok"); }, function () { say(m, url, "info"); });
      else say(m, url, "info");
    });
    if (nat && navigator.share) {
      nat.parentNode.hidden = false;
      nat.addEventListener("click", function () { navigator.share({ title: nat.getAttribute("data-title"), url: nat.getAttribute("data-url") }).catch(function () {}); });
    }
  });

  /* Archive search and filters */
  var grid = $("#archive-grid");
  if (grid) {
    var q = $("#archive-q"), year = $("#archive-year"), count = $("#archive-count"), empty = $("#archive-empty"), cat = "";
    var cards = $$(".edition-card", grid);
    var norm = function (s) { return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); };
    var run = function () {
      var words = norm(q.value).split(/\s+/).filter(Boolean), y = year.value, n = 0;
      cards.forEach(function (c) {
        var text = norm(c.getAttribute("data-search"));
        var ok = words.every(function (w) { return text.indexOf(w) !== -1; }) &&
          (!y || c.getAttribute("data-year") === y) &&
          (!cat || (" " + c.getAttribute("data-cats") + " ").indexOf(" " + cat + " ") !== -1);
        c.hidden = !ok; if (ok) n++;
      });
      empty.hidden = n > 0;
      count.textContent = n === cards.length ? "Showing all " + n + " editions" : "Showing " + n + " of " + cards.length + " editions";
    };
    q.addEventListener("input", run); year.addEventListener("change", run);
    $$(".chip").forEach(function (b) {
      b.addEventListener("click", function () {
        $$(".chip").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
        b.setAttribute("aria-pressed", "true"); cat = b.getAttribute("data-cat"); run();
      });
    });
    var pre = new URLSearchParams(location.search).get("q"); if (pre) q.value = pre;
    run();
  }

  /* Price charts on the Markets page, drawn only from the published data */
  var md = $("#market-data");
  if (md) {
    var data = JSON.parse(md.textContent), NS = "http://www.w3.org/2000/svg";
    var el = function (n, a, p) { var e = document.createElementNS(NS, n); for (var k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
    $$("[data-chart]").forEach(function (fig) {
      var id = fig.getAttribute("data-chart"), pts, usd = true;
      if (id === "mombasa") {
        var rows = data.mombasa.map(function (r) { return { y: +r.year, n: +r.sale, v: +r.avg_usd_kg }; }).sort(function (a, b) { return a.y - b.y || a.n - b.n; });
        var yr = rows[rows.length - 1].y;
        pts = rows.filter(function (r) { return r.y === yr; }).map(function (r) { return { x: r.n, v: r.v, l: "Sale " + r.n }; });
      } else {
        var src = data[id].filter(function (r) { return r.source_url && (r.avg_usd_kg || r.avg_local); });
        usd = src.every(function (r) { return r.avg_usd_kg; });
        pts = src.map(function (r) { return { x: +r.sale, v: +(usd ? r.avg_usd_kg : r.avg_local), l: "Sale " + r.sale }; });
      }
      if (pts.length < 2) return;
      var W = fig.clientWidth < 480 ? 360 : 640, H = 220, P = { l: 48, r: 14, t: 12, b: 26 };
      var vs = pts.map(function (p) { return p.v; }), lo = Math.min.apply(0, vs), hi = Math.max.apply(0, vs), pad = (hi - lo) * 0.15 || 0.05;
      var x0 = pts[0].x, x1 = pts[pts.length - 1].x;
      var X = function (x) { return P.l + (x - x0) / ((x1 - x0) || 1) * (W - P.l - P.r); };
      var Y = function (v) { return H - P.b - (v - lo + pad) / (hi - lo + 2 * pad) * (H - P.t - P.b); };
      var svg = el("svg", { viewBox: "0 0 " + W + " " + H, "aria-hidden": "true" }, fig);
      for (var i = 0; i <= 4; i++) {
        var v = lo - pad + i * (hi - lo + 2 * pad) / 4;
        el("line", { x1: P.l, x2: W - P.r, y1: Y(v), y2: Y(v), "class": "grid" }, svg);
        el("text", { x: P.l - 8, y: Y(v) + 4, "class": "tick", "text-anchor": "end" }, svg).textContent = (usd ? "$" : "") + v.toFixed(2);
      }
      [pts[0], pts[Math.floor(pts.length / 2)], pts[pts.length - 1]].forEach(function (p, k) {
        el("text", { x: X(p.x), y: H - 6, "class": "tick", "text-anchor": k === 0 ? "start" : k === 2 ? "end" : "middle" }, svg).textContent = p.l;
      });
      el("path", { d: pts.map(function (p, i) { return (i ? "L" : "M") + X(p.x).toFixed(1) + "," + Y(p.v).toFixed(1); }).join(""), "class": "line-main" }, svg);
      var lp = pts[pts.length - 1];
      el("circle", { cx: X(lp.x), cy: Y(lp.v), r: 4.5, "class": "pt pt-last" }, svg);
    });
  }
})();
