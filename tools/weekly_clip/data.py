"""Collects what the weekly clip shows from one issue: python3 tools/weekly_clip/data.py _posts/2026-11-25-issue-004.md > data.json"""
import csv
import datetime
import json
import pathlib
import sys

import yaml

post = pathlib.Path(sys.argv[1])
front = yaml.safe_load(post.read_text().split("---", 2)[1]) or {}
day = datetime.date.fromisoformat(post.name[:10])
sales = []
csv_path = pathlib.Path("_data/mombasa_eatta_sales.csv")
if csv_path.exists():
    for r in csv.DictReader(csv_path.open()):
        try:
            if int(r["year"]) == day.year and r["auction_date"] <= day.isoformat() and r["avg_usd_kg"]:
                sales.append([int(r["sale"]), float(r["avg_usd_kg"])])
        except (KeyError, ValueError):
            pass
sales.sort()
json.dump({
    "issue": front.get("issue"),
    "date": f"{day.day} {day.strftime('%B')} {day.year}",
    "title": front.get("title", ""),
    "deck": front.get("deck", ""),
    "snapshot": (front.get("snapshot") or [])[:4],
    "stories": [{"section": s.get("section", ""), "headline": s.get("headline", "")} for s in (front.get("stories") or [])[:5]],
    "sales": sales,
    "year": day.year,
}, sys.stdout, ensure_ascii=False)
