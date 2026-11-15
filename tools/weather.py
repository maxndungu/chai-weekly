"""Weekly weather snapshot for the tea-growing areas in _data/tea_areas.json (stdlib only).

Uses the free Open-Meteo API (no key; data CC BY 4.0, credit Open-Meteo.com). Writes:
  - _data/weather_snapshot.json  (the Weather page shows this if the live forecast can't load)
  - a markdown table on stdout, which the collector appends to the week's sources file
"""
import json, pathlib, sys, urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
AREAS = json.loads((ROOT / "_data" / "tea_areas.json").read_text())
URL = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
       "&daily=precipitation_sum,temperature_2m_max,temperature_2m_min&past_days=7&forecast_days=7&timezone=Africa%2FNairobi")


def summarise(d):
    rain, tmax, tmin, days = d["precipitation_sum"], d["temperature_2m_max"], d["temperature_2m_min"], d["time"]
    past, nxt = slice(0, 7), slice(7, 14)
    r = lambda xs: round(sum(x or 0 for x in xs), 1)
    wet_i = max(range(7, 14), key=lambda i: rain[i] or 0)
    flags = []
    if max(rain[nxt]) >= 50: flags.append("Heavy rain")
    elif max(rain[nxt]) >= 20: flags.append("Wet days")
    if r(rain[nxt]) < 5: flags.append("Dry week")
    if min(tmin[nxt]) <= 3: flags.append("Frost risk")
    elif min(tmin[nxt]) <= 8: flags.append("Cold nights")
    return {"rain_past7": r(rain[past]), "rain_next7": r(rain[nxt]), "wettest_day": days[wet_i], "wettest_mm": rain[wet_i] or 0,
            "min_night": min(tmin[nxt]), "max_day": max(tmax[nxt]), "flags": flags,
            "days": [{"date": days[i], "rain": rain[i] or 0, "tmin": tmin[i], "tmax": tmax[i]} for i in range(7, 14)]}


def main():
    lat = ",".join(str(a["lat"]) for a in AREAS); lon = ",".join(str(a["lon"]) for a in AREAS)
    req = urllib.request.Request(URL.format(lat=lat, lon=lon), headers={"User-Agent": "chai-weekly collector"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    if isinstance(data, dict):
        data = [data]
    rows = [{**a, **summarise(d["daily"])} for a, d in zip(AREAS, data)]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (ROOT / "_data" / "weather_snapshot.json").write_text(json.dumps({"updated": stamp, "areas": rows}, indent=1))
    print(f"\n## Weather in the tea areas (Open-Meteo model, {stamp}) <https://open-meteo.com/>\n")
    print("| Area | Rain last 7 days | Rain next 7 days | Wettest day ahead | Coldest night | Watch |\n|---|---|---|---|---|---|")
    for x in rows:
        print(f"| {x['name']} | {x['rain_past7']} mm | {x['rain_next7']} mm | {x['wettest_day']}: {x['wettest_mm']} mm | {x['min_night']}°C | {', '.join(x['flags']) or '–'} |")
    print("\nModel estimates, not station readings. Check Kenya Met (meteo.go.ke) warnings before quoting.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break the collector
        print(f"\n## Weather in the tea areas\n\n- Could not fetch Open-Meteo ({e}); use https://meteo.go.ke/")
        sys.exit(0)
