"""Turn Maxwell's lot-by-lot Mombasa auction workbooks ("Auction Data YYYY.xlsx", one row per lot: broker, producer,
mark, grade, kg offered, price, buyer, kg sold, value...) into per-sale totals in _data/mombasa_history_sales.csv.

The workbooks are too big for the repo (about 25 MB a year) and stay with Maxwell; only the totals are kept here.
Offered = every lot catalogued for the sale (re-offered lots count again); sold = lots with kg sold > 0;
average = sale value / kg sold. Needs openpyxl (pip install openpyxl), unlike the weekly collector.

    python tools/lots_to_sales.py "Auction Data 2009.xlsx" "Auction Data 2010.xlsx" ...
Re-running a year replaces that year's rows; other years are kept.
"""
import csv, sys
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "_data" / "mombasa_history_sales.csv"
# No orthodox totals: the workbooks hold only a few lots tagged ORTHODOX (Rwandan BOPF1 and similar, about $0.80/kg),
# not the orthodox catalogue, so they would misstate orthodox prices. Those lots still count in "all".
TEAS = {"all": None, "ctc": "CTC"}
COLS = ["year", "sale", "auction_date"] + [f"{t}_{f}" for t in TEAS for f in
        ("offered_lots", "sold_lots", "offered_kg", "sold_kg", "avg_usd_kg")]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def read(path):
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    hdr, sales = None, defaultdict(lambda: {"date": "", **{t: [0, 0, 0.0, 0.0, 0.0] for t in TEAS}})
    for row in ws.iter_rows(values_only=True):
        if hdr is None:
            if row and row[0] == "Auction Year":
                hdr = {k: i for i, k in enumerate(row) if k}
            continue
        if not row or row[hdr["Auction No"]] is None:
            continue
        s = sales[str(row[hdr["Auction No"]])]
        if not s["date"] and row[hdr["Sale date"]]:
            s["date"] = str(row[hdr["Sale date"]])[:10]
        off, kg, val = num(row[hdr["Weight Kgs"]]), num(row[hdr["Weight Sold"]]), num(row[hdr["Sale Value"]])
        if kg and not val:
            val = kg * num(row[hdr["Sale Price"]])
        tt = str(row[hdr["TeaType"]] or "").strip().upper()
        for t, want in TEAS.items():
            if want and tt != want:
                continue
            a = s[t]
            a[0] += 1; a[2] += off
            if kg > 0:
                a[1] += 1; a[3] += kg; a[4] += val
    if hdr is None:
        sys.exit(f"{path}: no 'Auction Year' header row found")
    return sales


def rows(sales):
    for no, s in sales.items():
        year, sale = no.split("/")
        r = {"year": str(int(year)), "sale": str(int(sale)), "auction_date": s["date"]}
        for t in TEAS:
            lo, ls, off, kg, val = s[t]
            r.update({f"{t}_offered_lots": lo or "", f"{t}_sold_lots": ls if lo else "",
                      f"{t}_offered_kg": round(off) if lo else "", f"{t}_sold_kg": round(kg) if lo else "",
                      f"{t}_avg_usd_kg": f"{val / kg:.2f}" if kg else ""})
        yield r


def main():
    keep = {}
    if OUT.exists():
        with OUT.open(newline="") as f:
            keep = {(r["year"], r["sale"]): r for r in csv.DictReader(f)}
    for path in sys.argv[1:]:
        new = list(rows(read(path)))
        years = {r["year"] for r in new}
        keep = {k: v for k, v in keep.items() if k[0] not in years}
        keep.update({(r["year"], r["sale"]): r for r in new})
        print(f"{Path(path).name}: {len(new)} sales")
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(sorted(keep.values(), key=lambda r: (int(r["year"]), int(r["sale"]))))
    print(f"{OUT.name}: {len(keep)} sales")


if __name__ == "__main__":
    main()
