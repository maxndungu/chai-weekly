"""Average CTC price by grade and origin at every Mombasa sale, from Maxwell's lot-by-lot workbooks
("Auction Data YYYY.xlsx"), into _data/mombasa_grade_prices.csv. Feeds the detailed statistics.

Origins: Kenya small-scale east of the Rift, small-scale west of the Rift, plantations, all of Kenya, Uganda,
Rwanda, Tanzania, Burundi and other origins together. Grades: the main and secondary CTC grades listed in GRADES.
Average = sale value / kg sold for that origin and grade (lots with nothing sold count towards offered only).
The workbooks stay with Maxwell; only these averages are kept. Needs openpyxl (pip install openpyxl).

    python tools/lots_to_grades.py "Auction Data 2009.xlsx" "Auction Data 2010.xlsx" ...
Re-running a year replaces that year's rows; other years are kept.
"""
import csv, sys
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "_data" / "mombasa_grade_prices.csv"
GRADES = ["BP1", "PF1", "PD", "DUST1", "BP", "PF", "DUST", "FNGS1", "FNGS", "BMF"]
KENYA = {"KTDA EOR": "KE-E", "KTDA WOR": "KE-W", "PLANTATIONS": "KE-P"}
COUNTRIES = {"UGANDA": "UG", "RWANDA": "RW", "TANZANIA": "TZ", "BURUNDI": "BI"}
COLS = ["year", "sale", "date", "origin", "grade", "offered_kg", "sold_kg", "avg_usc"]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def origins(country, sector):
    country, sector = (country or "").strip().upper(), (sector or "").strip().upper()
    if country == "KENYA":
        return [KENYA.get(sector, "KE-P"), "KE"]
    return [COUNTRIES.get(country, "OTHER")]


def read(path):
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    hdr, dates, agg = None, {}, defaultdict(lambda: [0.0, 0.0, 0.0])
    for row in ws.iter_rows(values_only=True):
        if hdr is None:
            if row and row[0] == "Auction Year":
                hdr = {k: i for i, k in enumerate(row) if k}
            continue
        if not row or row[hdr["Auction No"]] is None:
            continue
        get = lambda k: row[hdr[k]] if k in hdr else None
        if str(get("TeaType") or "CTC").strip().upper() != "CTC":
            continue
        grade = str(get("Grade") or "").strip().upper()
        if grade not in GRADES:
            continue
        year, sale = int(get("Auction Year")), int(str(get("Auction No")).split("/")[-1])
        dates.setdefault((year, sale), str(get("Sale date"))[:10])
        sold = num(get("Weight Sold"))
        for o in origins(get("Country"), get("Sector")):
            a = agg[(year, sale, o, grade)]
            a[0] += num(get("Weight Kgs")); a[1] += sold; a[2] += num(get("Sale Value")) if sold > 0 else 0
    return [{"year": y, "sale": s, "date": dates[(y, s)], "origin": o, "grade": g, "offered_kg": round(a[0]),
             "sold_kg": round(a[1]), "avg_usc": round(a[2] / a[1] * 100, 1) if a[1] else ""}
            for (y, s, o, g), a in agg.items()]


def main(paths):
    rows = list(csv.DictReader(OUT.open())) if OUT.exists() else []
    for p in paths:
        new = read(p)
        years = {str(r["year"]) for r in new}
        rows = [r for r in rows if r["year"] not in years] + new
        print(f"{Path(p).name}: {len(new)} rows, years {', '.join(sorted(years))}")
    order = {o: i for i, o in enumerate(["KE", "KE-E", "KE-W", "KE-P", "UG", "RW", "TZ", "BI", "OTHER"])}
    rows.sort(key=lambda r: (int(r["year"]), int(r["sale"]), order[r["origin"]], GRADES.index(r["grade"])))
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, COLS); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1:] or sys.exit(__doc__))
