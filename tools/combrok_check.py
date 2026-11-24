"""Cross-check our EATTA figures against Combrok's Mombasa auction figures, for Maxwell's eyes only.

Combrok Limited (a Mombasa tea broker) publishes per-sale figures on https://combrok.co.ke/market-reports,
marked "All rights reserved". We do NOT publish them or save them in _data/: this script only prints the
sales where the two sources differ, for the reviewer notes. Our published figures stay EATTA's.

Combrok's "CTC" auction figures track EATTA's all-teas totals (e.g. sale 40/2026: $2.22, 6.52m kg on both),
so they are compared with the all-teas columns; orthodox is compared with orthodox.
EATTA adds late sales until Friday noon, so a difference on the newest sale is expected on Wednesday.

    python tools/combrok_check.py                      # fetch live, compare with _data/mombasa_eatta_sales.csv
    python tools/combrok_check.py ctc.json orth.json   # use saved files (for testing)
Stdlib only. Always exits 0 unless the comparison itself crashes: a fetch failure prints a "check by hand" line.
"""
import csv, json, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

PAGE = "https://combrok.co.ke/market-reports"
FEEDS = {"ctc": "https://combrok.co.ke/assets/data/ctc-auction.json",
         "orthodox": "https://combrok.co.ke/assets/data/orthodox-auction.json"}
CSV = Path(__file__).resolve().parent.parent / "_data" / "mombasa_eatta_sales.csv"
PRICE_GAP = 0.02   # US$/kg; both sources round to cents, so one cent is rounding
KG_GAP = 0.02      # 2% of kg sold
LOOK_BACK = 8      # newest sales to compare
NAIROBI = timezone(timedelta(hours=3))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (chai-weekly cross-check)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def final(auction_date, now):
    """EATTA figures are final after the Friday noon (Nairobi) following the sale."""
    if not auction_date:
        return True
    d = datetime.strptime(auction_date, "%Y-%m-%d")
    friday = d + timedelta(days=(4 - d.weekday()) % 7)
    return now >= friday.replace(hour=12, tzinfo=NAIROBI)


def compare(eatta_rows, combrok, now=None):
    """Return (lines, flagged_count). eatta_rows: CSV dicts. combrok: {"ctc": [...], "orthodox": [...]}."""
    now = now or datetime.now(NAIROBI)
    pairs = {"ctc": ("avg_usd_kg", "sold_kg", "all teas"), "orthodox": ("orthodox_avg_usd_kg", "orthodox_sold_kg", "orthodox")}
    years = sorted({int(r["year"]) for r in eatta_rows})
    if not years:
        return ["- No EATTA sales saved yet, nothing to compare."], 0
    year = years[-1]
    ours = sorted((r for r in eatta_rows if int(r["year"]) == year), key=lambda r: int(r["sale"]))[-LOOK_BACK:]
    lines, flagged = [], 0
    for kind, (pcol, kcol, label) in pairs.items():
        theirs = {int(c["sale"]): c for c in combrok.get(kind) or [] if int(c.get("year", 0)) == year}
        for r in ours:
            n, c = int(r["sale"]), theirs.get(int(r["sale"]))
            p, kg = r.get(pcol) or "", r.get(kcol) or ""
            if not p and not kg:
                continue  # EATTA published no figure of this kind for the sale
            if c is None:
                lines.append(f"- Sale {n} ({label}): not in Combrok's figures yet.")
                continue
            notes = []
            if p and c.get("avg_prc") is not None and abs(float(p) - float(c["avg_prc"])) >= PRICE_GAP - 1e-9:
                notes.append(f"average EATTA ${float(p):.2f} vs Combrok ${float(c['avg_prc']):.2f}")
            if kg and c.get("qty_sold") and abs(float(kg) - float(c["qty_sold"])) / float(kg) >= KG_GAP:
                notes.append(f"sold EATTA {int(float(kg)):,} kg vs Combrok {int(float(c['qty_sold'])):,} kg "
                             f"({(float(c['qty_sold']) / float(kg) - 1) * 100:+.1f}%)")
            if notes:
                flagged += 1
                why = ("expected: EATTA's figures for this sale are provisional until Friday noon"
                       if not final(r.get("auction_date"), now) else "**check**: EATTA's figures for this sale are final")
                lines.append(f"- Sale {n} ({label}): " + "; ".join(notes) + f". {why}.")
    if not flagged:
        lines.append(f"- The last {len(ours)} sales of {year} agree within ${PRICE_GAP:.2f}/kg and {KG_GAP:.0%} of kg sold.")
    return lines, flagged


def main():
    today = datetime.now(NAIROBI).date().isoformat()
    print(f"\n## Cross-check: Combrok figures (internal, do not publish), {today} <{PAGE}>\n")
    print("Combrok's figures are copyright Combrok Limited. Use them only to spot a sale worth re-checking on "
          "<https://eatta.co.ke/statistics>; the issue and the site quote EATTA only.\n")
    try:
        if len(sys.argv) > 2:
            combrok = {"ctc": json.load(open(sys.argv[1])), "orthodox": json.load(open(sys.argv[2]))}
        else:
            combrok = {k: fetch(u) for k, u in FEEDS.items()}
    except Exception as e:  # network, JSON or layout change: say so, never fail the collector
        print(f"- Could not read Combrok's figures ({type(e).__name__}); compare by hand at <{PAGE}> if a figure looks odd.")
        return
    with CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))
    lines, _ = compare(rows, combrok)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
