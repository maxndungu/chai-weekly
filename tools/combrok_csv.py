"""Save Combrok's per-sale Mombasa auction figures into _data/mombasa_combrok_sales.csv.

Combrok Limited (a Mombasa tea broker) publishes per-sale figures built from the public Mombasa auction results
on https://combrok.co.ke/market-reports, including what EATTA's statistics page leaves out: kg and lots offered
(so the share sold, "absorption", can be worked out) and every sale back to 2020. The dashboard uses these for
offered kg, absorption and the years before 2026, with a credit line; for 2026 on, prices and kg sold stay EATTA's.

Each run adds new sales and updates revised ones; rows are never deleted. Stdlib only.

    python tools/combrok_csv.py                    # fetch live
    python tools/combrok_csv.py ctc.json orth.json # use saved files (for testing)
"""
import csv, json, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

FEEDS = {"ctc": "https://combrok.co.ke/assets/data/ctc-auction.json",
         "orthodox": "https://combrok.co.ke/assets/data/orthodox-auction.json"}
OUT = Path(__file__).resolve().parent.parent / "_data" / "mombasa_combrok_sales.csv"
FIELDS = ["offered_lots", "sold_lots", "offered_kg", "sold_kg", "avg_usd_kg"]
COLS = ["year", "sale"] + [f"{k}_{f}" for k in FEEDS for f in FIELDS] + ["first_saved", "last_checked"]
SRC = {"offered_lots": "offered_lots", "sold_lots": "sold_lots", "offered_kg": "qty_offered",
       "sold_kg": "qty_sold", "avg_usd_kg": "avg_prc"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (chai-weekly collector)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def val(v, field):
    if v is None or v == "":
        return ""
    return f"{float(v):.2f}" if field == "avg_usd_kg" else str(int(round(float(v))))


def merge(existing, feeds, today):
    """existing: {(year, sale): row}. feeds: {"ctc": [...], "orthodox": [...]}. Returns (added, revised)."""
    added = revised = 0
    for kind, items in feeds.items():
        for it in items or []:
            try:
                key = (str(int(it["year"])), str(int(it["sale"])))
            except (KeyError, TypeError, ValueError):
                continue
            new = {f"{kind}_{f}": val(it.get(SRC[f]), f) for f in FIELDS}
            row = existing.get(key)
            if row is None:
                row = existing[key] = {c: "" for c in COLS}
                row.update(year=key[0], sale=key[1], first_saved=today)
                added += 1
            elif any(new[c] and row.get(c) and new[c] != row[c] for c in new):
                revised += 1
            row.update({c: v for c, v in new.items() if v})
            row["last_checked"] = today
    return added, revised


def main():
    if len(sys.argv) > 2:
        feeds = {"ctc": json.load(open(sys.argv[1])), "orthodox": json.load(open(sys.argv[2]))}
    else:
        feeds = {k: fetch(u) for k, u in FEEDS.items()}
    if not feeds.get("ctc"):
        sys.exit("Combrok returned no CTC sales")
    existing = {}
    if OUT.exists():
        with OUT.open(newline="") as f:
            existing = {(r["year"], r["sale"]): r for r in csv.DictReader(f)}
    added, revised = merge(existing, feeds, datetime.now(timezone.utc).date().isoformat())
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(existing.values(), key=lambda r: (int(r["year"]), int(r["sale"]))))
    print(f"{OUT.name}: {len(existing)} sales ({added} new, {revised} revised)")


if __name__ == "__main__":
    main()
