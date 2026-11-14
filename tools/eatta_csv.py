"""Save every Mombasa auction sale from EATTA's statistics API into data/mombasa-eatta-sales.csv.

EATTA's API only serves the current year, so this file is our own long-run history: each run adds new
sales and updates any figure EATTA has revised, and never deletes old rows. Stdlib only.

    python tools/eatta_csv.py              # fetch live
    python tools/eatta_csv.py saved.json   # use a saved API response (for testing)
"""
import csv, json, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://eatta.co.ke/api/sales-report.php?year={year}"
OUT = Path(__file__).resolve().parent.parent / "data" / "mombasa-eatta-sales.csv"
COLS = ["year", "sale", "auction_date", "avg_usd_kg", "sold_kg", "ctc_avg_usd_kg", "ctc_sold_kg",
        "orthodox_avg_usd_kg", "orthodox_sold_kg", "offered_kg", "unsold_pct", "first_saved", "last_checked"]
VALUE_COLS = COLS[2:11]


def num(v, places=None):
    if v is None or v == "":
        return ""
    return f"{float(v):.{places}f}" if places is not None else str(int(round(float(v))))


def fetch(year):
    req = urllib.request.Request(API.format(year=year), headers={"User-Agent": "Mozilla/5.0 (chai-weekly collector)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def rows_from(data):
    year = str(data["year"])
    for s in data.get("sales", []):
        ctc, orth = s.get("ctc") or {}, s.get("orthodox") or {}
        yield {
            "year": year, "sale": str(s["saleNumber"]), "auction_date": s.get("auctionDate") or "",
            "avg_usd_kg": num(s.get("averagePriceUsd"), 2), "sold_kg": num(s.get("soldKg")),
            "ctc_avg_usd_kg": num(ctc.get("averagePriceUsd"), 2), "ctc_sold_kg": num(ctc.get("soldKg")),
            "orthodox_avg_usd_kg": num(orth.get("averagePriceUsd"), 2),
            "orthodox_sold_kg": num(orth.get("soldKg")) if orth.get("averagePriceUsd") is not None else "",
            "offered_kg": num(s.get("offeredKg")), "unsold_pct": num(s.get("unsoldPct"), 1),
        }


def main():
    data = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else fetch(datetime.now(timezone.utc).year)
    if not data.get("ok") or not data.get("sales"):
        sys.exit(f"EATTA API returned no sales: {str(data)[:200]}")
    today = datetime.now(timezone.utc).date().isoformat()
    existing = {}
    if OUT.exists():
        with OUT.open(newline="") as f:
            existing = {(r["year"], r["sale"]): r for r in csv.DictReader(f)}
    added = revised = 0
    for new in rows_from(data):
        key = (new["year"], new["sale"])
        old = existing.get(key)
        if old is None:
            existing[key] = {**new, "first_saved": today, "last_checked": today}
            added += 1
            continue
        changes = [f"{c} {old[c]}->{new[c]}" for c in VALUE_COLS if new[c] and new[c] != old[c]]
        if changes:
            revised += 1
            print(f"Sale {key[1]}/{key[0]} revised by EATTA: " + ", ".join(changes))
        old.update({c: new[c] for c in VALUE_COLS if new[c]}, last_checked=today)
    # Sanity check: flag odd prices so a human looks before the figure is used.
    for r in existing.values():
        if r["avg_usd_kg"] and not 1.0 <= float(r["avg_usd_kg"]) <= 6.0:
            print(f"CHECK: sale {r['sale']}/{r['year']} average ${r['avg_usd_kg']} looks out of range")
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(sorted(existing.values(), key=lambda r: (int(r["year"]), int(r["sale"]))))
    print(f"{OUT.name}: {len(existing)} sales ({added} new, {revised} revised)")


if __name__ == "__main__":
    main()
