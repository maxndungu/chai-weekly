"""Builds _data/tea_production.csv (made tea, tonnes, country by year) from tools/production-raw/.

Made tea is processed tea as sold (the figure the trade uses). Sources, in order of preference:
  1961-2020  FAO's former "Tea" item (made tea), fao_tea_made_1961_2020.csv
  2019-2024  Tea Board of Kenya annual totals for Kenya (replace FAO for Kenya)
  2021-2024  International Tea Committee figures for the seven largest producers
FAO's current "Tea leaves" series switched to green leaf from 1991, so it is kept separately in
_data/tea_production_fao.csv and is not mixed in here.
Run: python3 -I tools/production_build.py
"""
import csv, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'tools', 'production-raw')

NAMES = {  # source name -> (name on site, ISO3)
 'Argentina':('Argentina','ARG'),'Azerbaijan':('Azerbaijan','AZE'),'Bangladesh':('Bangladesh','BGD'),
 'Bolivia':('Bolivia','BOL'),'Brazil':('Brazil','BRA'),'Burundi':('Burundi','BDI'),'Cameroon':('Cameroon','CMR'),
 'China':('China','CHN'),'Colombia':('Colombia','COL'),'Democratic Republic of Congo':('DR Congo','COD'),
 'Ecuador':('Ecuador','ECU'),'El Salvador':('El Salvador','SLV'),'Eritrea and Ethiopia':('Ethiopia (with Eritrea, to 1992)','ETH_ERI'),
 'Ethiopia':('Ethiopia','ETH'),'Georgia':('Georgia','GEO'),'Guatemala':('Guatemala','GTM'),'India':('India','IND'),
 'Indonesia':('Indonesia','IDN'),'Iran':('Iran','IRN'),'Japan':('Japan','JPN'),'Kenya':('Kenya','KEN'),'Laos':('Laos','LAO'),
 'Madagascar':('Madagascar','MDG'),'Malawi':('Malawi','MWI'),'Malaysia':('Malaysia','MYS'),'Mali':('Mali','MLI'),
 'Mauritius':('Mauritius','MUS'),'Montenegro':('Montenegro','MNE'),'Mozambique':('Mozambique','MOZ'),'Myanmar':('Myanmar','MMR'),
 'Nepal':('Nepal','NPL'),'Panama':('Panama','PAN'),'Papua New Guinea':('Papua New Guinea','PNG'),'Peru':('Peru','PER'),
 'Portugal':('Portugal','PRT'),'Reunion':('Réunion','REU'),'Russia':('Russia','RUS'),'Rwanda':('Rwanda','RWA'),
 'Seychelles':('Seychelles','SYC'),'South Africa':('South Africa','ZAF'),'South Korea':('South Korea','KOR'),
 'Sri Lanka':('Sri Lanka','LKA'),'Taiwan':('Taiwan','TWN'),'Tanzania':('Tanzania','TZA'),'Thailand':('Thailand','THA'),
 'Turkey':('Türkiye','TUR'),'Türkiye':('Türkiye','TUR'),'USSR':('USSR (to 1991)','SUN'),'Uganda':('Uganda','UGA'),
 'Vietnam':('Vietnam','VNM'),'Zambia':('Zambia','ZMB'),'Zimbabwe':('Zimbabwe','ZWE'),'World':('World','WLD'),
}

rows = {}
def put(name, year, tonnes, src):
    site, iso = NAMES[name]
    rows[(site, year)] = [site, iso, year, round(tonnes), src]

for r in csv.reader(open(os.path.join(RAW, 'fao_tea_made_1961_2020.csv'), encoding='utf-8')):
    if r[0] == 'Entity' or r[0] not in NAMES: continue   # skips regions such as Africa, Asia
    if r[3]: put(r[0], int(r[2]), float(r[3]), 'fao')

with open(os.path.join(RAW, 'itc_2020_2024_mkg.csv'), encoding='utf-8') as f:
    rd = csv.reader(f); years = [int(y) for y in next(rd)[1:]]
    for r in rd:
        if r[0] in ('Others', 'World'): continue   # world totals differ in basis from FAO's; not spliced
        for y, v in zip(years, r[1:]):
            if y >= 2021: put(r[0], y, float(v) * 1000, 'itc')

for r in csv.DictReader(open(os.path.join(RAW, 'tbk_kenya_annual_kg.csv'))):
    put('Kenya', int(r['year']), int(r['total']) / 1000, 'tbk')

with open(os.path.join(ROOT, '_data', 'tea_production.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['country', 'iso3', 'year', 'made_tea_t', 'source'])
    for k in sorted(rows, key=lambda k: (k[0] == 'World', k[0], k[1])): w.writerow(rows[k])
print(len(rows), 'rows')
