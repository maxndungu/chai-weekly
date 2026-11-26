"""Builds _data/tea_production.csv (made tea, tonnes, country by year) from tools/production-raw/.

Made tea is processed tea as sold (the figure the trade uses). Sources, in order of preference:
  1961-2015  FAO's former "Tea" item (made tea), fao_tea_made_1961_2020.csv. For the countries in
             FAO_FRESH_LEAF, FAO's 1991-2015 figures run 2.5 to 10 times the made-tea figures and are left out
             (they count fresh leaf); the world total for those years has their FAO values taken off.
  2016-2025  International Tea Committee, Supplement to the Annual Bulletin 2025 (Table B, every producer
             and the world). The ITC file is subscriber-only and copyright, so it is NOT in this repo:
             pass its path as ITC_SUPPLEMENT=/path/itc_supplement_2025_production_t.csv. Without it the
             2016+ rows already in _data/tea_production.csv are kept as they are.
  2019-2025  national tea boards win over ITC where published (Kenya, India, Sri Lanka); the world total
             takes the difference so it still equals the sum of countries.
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
 'Vietnam':('Vietnam','VNM'),'Zambia':('Zambia','ZMB'),'Zimbabwe':('Zimbabwe','ZWE'),'DR Congo':('DR Congo','COD'),'Australia':('Australia','AUS'),'World':('World','WLD'),
}

rows = {}
def put(name, year, tonnes, src):
    site, iso = NAMES[name]
    rows[(site, year)] = [site, iso, year, round(tonnes), src]

FAO_FRESH_LEAF = {'Iran', 'Malaysia', 'Myanmar', 'Thailand', 'Burundi', 'Mozambique'}
ITC_FROM = 2016
fao = {}
for r in csv.reader(open(os.path.join(RAW, 'fao_tea_made_1961_2020.csv'), encoding='utf-8')):
    if r[0] == 'Entity' or r[0] not in NAMES or not r[3]: continue   # skips regions such as Africa, Asia
    fao[(r[0], int(r[2]))] = float(r[3])

itc_path = os.environ.get('ITC_SUPPLEMENT')
if itc_path:
    for (c, y), t in fao.items():
        if y >= ITC_FROM: continue
        if c in FAO_FRESH_LEAF and 1991 <= y: continue
        if c == 'World' and y >= 1991:
            t -= sum(fao.get((b, y), 0) for b in FAO_FRESH_LEAF)
        put(c, y, t, 'fao')
    for r in csv.DictReader(open(itc_path, encoding='utf-8')):
        for y in range(ITC_FROM, 2026):
            v = r.get(str(y), '').strip()
            if v and v != '-': put(r['country'], y, float(v), 'itc')
else:   # keep the 2016+ rows already built (ITC figures are not in the repo)
    old = list(csv.DictReader(open(os.path.join(ROOT, '_data', 'tea_production.csv'), encoding='utf-8')))
    for r in old:
        rows[(r['country'], int(r['year']))] = [r['country'], r['iso3'], int(r['year']), int(r['made_tea_t']), r['source']]

def override(name, year, tonnes, src):
    site = NAMES[name][0]
    prev = rows.get((site, year)); w = rows.get(('World', year))
    if itc_path and prev and w and prev[4] == 'itc': w[3] += round(tonnes) - prev[3]
    put(name, year, tonnes, src)

for r in csv.DictReader(open(os.path.join(RAW, 'national_calendar_mkg.csv'), encoding='utf-8')):
    override(r['country'], int(r['year']), float(r['million_kg']) * 1000, r['source'])   # national boards win over ITC

for r in csv.DictReader(open(os.path.join(RAW, 'tbk_kenya_annual_kg.csv'))):
    override('Kenya', int(r['year']), int(r['total']) / 1000, 'tbk')

with open(os.path.join(ROOT, '_data', 'tea_production.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['country', 'iso3', 'year', 'made_tea_t', 'source'])
    for k in sorted(rows, key=lambda k: (k[0] == 'World', k[0], k[1])): w.writerow(rows[k])
print(len(rows), 'rows')
