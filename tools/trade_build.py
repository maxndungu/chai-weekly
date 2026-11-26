"""Builds the tea trade and consumption files from tools/production-raw/:
  _data/tea_trade.csv   country, iso3, year, exports_t, imports_t, consumption_t, source (tonnes)
  _data/tea_trade_series.json  the same, compact, for the preview Production tab and Tea map (served as assets/data/tea-trade.json)

What the figures mean (one definition across all years):
  exports      tea exported by the countries that grow it. Re-exports by countries that grow no tea (the UK,
               Germany, the UAE...) are not counted, so the world total is tea leaving the producing countries.
               Kenya's exports include tea of other East African origins sold through Mombasa.
  imports      tea imported for drinking: for countries that grow no tea, imports less re-exports;
               for tea-growing countries, all imports.
  consumption  production + imports - exports for tea-growing countries; imports (as above) for the rest.
               Left blank where it comes out below zero (Kenya most years: its exports include re-exported tea).

Sources:
  1961-2015  FAO, FAOSTAT trade (item "Tea leaves", export and import quantity), fao_tea_trade_1961_2024.csv.
  2016-2025  International Tea Committee, Supplement to the Annual Bulletin 2025 (Tables C and D). Subscriber-only
             and copyright, so NOT in this repo: pass ITC_DIR=/folder/with/itc_supplement_2025_*_t.csv. Without it
             the 2016+ rows already in _data/tea_trade.csv are kept. Countries the ITC tables only show inside a group
             (Kazakhstan in "Other CIS", Costa Rica in "Central America"...) keep FAO figures to 2024; the world
             totals are the ITC totals.
  Production comes from _data/tea_production.csv (build that first with tools/production_build.py).
Run: python3 -I tools/trade_build.py
"""
import csv, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'tools', 'production-raw')
ITC_FROM, LAST = 2016, 2025

# ---- places: ISO3, M49 (the map's shape id), sub-region ----
iso = {}
for r in csv.DictReader(open(os.path.join(RAW, 'iso3166.csv'), encoding='utf-8')):
    iso[r['country-code']] = (r['alpha-3'], r['sub-region'], r['intermediate-region'])
OLD = {'810': ('SUN', 'Eastern Europe'), '890': ('YUG', 'Southern Europe'), '200': ('CSK', 'Eastern Europe'),
       '891': ('SCG', 'Southern Europe'), '230': ('ETH_ERI', 'Sub-Saharan Africa'), '736': ('SDN_OLD', 'Northern Africa'),
       '058': ('BLX', 'Western Europe'), '530': ('ANT', 'Latin America and the Caribbean'), '158': ('TWN', 'Eastern Asia'),
       '156': ('CHN', 'Eastern Asia')}
SKIP_M49 = {'159'}  # FAO "China" = mainland + Hong Kong + Macao + Taiwan; the parts are counted on their own
SITE = {'United Republic of Tanzania': 'Tanzania', 'Democratic Republic of the Congo': 'DR Congo', 'Ethiopia PDR': 'Ethiopia (with Eritrea, to 1992)',
        'Viet Nam': 'Vietnam', 'Iran (Islamic Republic of)': 'Iran', "Lao People's Democratic Republic": 'Laos', 'Republic of Korea': 'South Korea',
        "Democratic People's Republic of Korea": 'North Korea', 'China, mainland': 'China', 'China, Taiwan Province of': 'Taiwan',
        'China, Hong Kong SAR': 'Hong Kong', 'China, Macao SAR': 'Macao', 'Russian Federation': 'Russia', 'Bolivia (Plurinational State of)': 'Bolivia',
        'Venezuela (Bolivarian Republic of)': 'Venezuela', 'Syrian Arab Republic': 'Syria', 'Republic of Moldova': 'Moldova', 'Türkiye': 'Türkiye',
        'United Kingdom of Great Britain and Northern Ireland': 'United Kingdom', 'United States of America': 'United States', 'Netherlands (Kingdom of the)': 'Netherlands',
        'USSR': 'USSR (to 1991)', 'Czechoslovakia': 'Czechoslovakia (to 1992)', 'Yugoslav SFR': 'Yugoslavia (to 1991)', 'Serbia and Montenegro': 'Serbia and Montenegro (to 2005)',
        'Sudan (former)': 'Sudan (to 2011)', 'Belgium-Luxembourg': 'Belgium-Luxembourg (to 1999)', 'Netherlands Antilles (former)': 'Netherlands Antilles',
        "Côte d'Ivoire": 'Ivory Coast', 'Eswatini': 'Eswatini', 'Micronesia (Federated States of)': 'Micronesia', 'Palestine': 'Palestine',
        'Réunion': 'Réunion', 'Cabo Verde': 'Cape Verde', 'Czechia': 'Czechia', 'Brunei Darussalam': 'Brunei', 'Lao People\'s Democratic Republic': 'Laos'}

def region(iso3, sub, inter):
    """Map region for countries that are not in _data/tea_map.yml (the tea-growing ones are placed there)."""
    if iso3 in ('TUR', 'GEO', 'AZE', 'ARM', 'CYP', 'RUS', 'SUN'): return 'europe-west-asia'
    if sub in ('Northern Africa', 'Western Asia'): return 'middle-east-north-africa'
    if sub == 'Sub-Saharan Africa': return 'eastern-africa' if inter == 'Eastern Africa' and iso3 not in ('SOM', 'DJI', 'ERI', 'SSD') else 'rest-of-africa'
    if sub in ('Southern Asia',): return 'south-asia'
    if sub == 'Eastern Asia': return 'east-asia'
    if sub in ('South-eastern Asia', 'Australia and New Zealand', 'Melanesia', 'Micronesia', 'Polynesia'): return 'southeast-asia'
    if sub in ('Latin America and the Caribbean', 'Northern America'): return 'americas'
    return 'europe-west-asia'   # Europe and Central Asia

place = {}   # iso3 -> {name, map, region}
def add_place(m49, fao_name):
    if m49 in OLD: i3, sub = OLD[m49]; inter = ''
    elif m49 in iso: i3, sub, inter = iso[m49]
    else: return None
    if i3 not in place:
        place[i3] = {'name': SITE.get(fao_name, fao_name), 'map': m49 if m49 not in OLD or m49 in ('158', '156') else None, 'region': region(i3, sub, inter)}
    return i3

# ---- production (made tea) ----
prod, prod_names = {}, {}
for r in csv.DictReader(open(os.path.join(ROOT, '_data', 'tea_production.csv'), encoding='utf-8')):
    if r['iso3'] == 'WLD': continue
    prod.setdefault(r['iso3'], {})[int(r['year'])] = float(r['made_tea_t']); prod_names[r['iso3']] = r['country']
growers = set(prod)

# ---- FAO trade ----
fx, fm = {}, {}
# FAOSTAT TCL, item 667 "Tea leaves", export and import quantity (t), read 2026-11-26. For countries that grow no tea
# the file holds net imports (imports less exports, not below zero), which is all this build uses for them.
for r in csv.DictReader(open(os.path.join(RAW, 'fao_tea_trade_1961_2024.csv'), encoding='utf-8')):
    if r['m49'] in SKIP_M49: continue
    i3 = add_place(r['m49'], r['area'])
    if not i3: continue
    (fx if r['element'] == 'export' else fm).setdefault(i3, {})[int(r['year'])] = float(r['tonnes'])
for k, n in prod_names.items():
    if k in place: place[k]['name'] = n

rows = {}   # (iso3, year) -> [exports, imports, source]
def fao_row(i3, y):
    x, m = fx.get(i3, {}).get(y), fm.get(i3, {}).get(y)
    if x is None and m is None: return None
    if i3 in growers: return [x, m]
    return [None, m]   # net imports already; re-exports are not exports of tea grown there

itc_dir = os.environ.get('ITC_DIR')
ITC = {  # ITC table name -> ISO3 (groups such as "Other CIS" are left out of the country rows)
 'India': 'IND', 'Bangladesh': 'BGD', 'Sri Lanka': 'LKA', 'Indonesia': 'IDN', 'China (Mainland)': 'CHN', 'China': 'CHN', 'Taiwan': 'TWN', 'Iran': 'IRN',
 'Korea Rep.': 'KOR', 'Korea, South': 'KOR', 'Japan': 'JPN', 'Malaysia': 'MYS', 'Nepal': 'NPL', 'Thailand': 'THA', 'Türkiye': 'TUR', 'Vietnam': 'VNM',
 'Burundi': 'BDI', 'Cameroon': 'CMR', 'Congo, DRC': 'COD', 'Ethiopia': 'ETH', 'Kenya': 'KEN', 'Malawi': 'MWI', 'Mauritius': 'MUS', 'Mozambique': 'MOZ',
 'Rwanda': 'RWA', 'South Africa': 'ZAF', 'Tanzania': 'TZA', 'Uganda': 'UGA', 'Zimbabwe': 'ZWE', 'Georgia': 'GEO', 'Argentina': 'ARG', 'Brazil': 'BRA',
 'Ecuador': 'ECU', 'Peru': 'PER', 'Papua New Guinea': 'PNG',
 'United Kingdom': 'GBR', 'Russian Federation': 'RUS', 'Austria': 'AUT', 'Belgium': 'BEL', 'Bulgaria': 'BGR', 'Croatia': 'HRV', 'Cyprus Rep.': 'CYP',
 'Czech Rep.': 'CZE', 'Denmark': 'DNK', 'Faroe Islands': 'FRO', 'Finland': 'FIN', 'France': 'FRA', 'Germany': 'DEU', 'Gibraltar': 'GIB', 'Greece': 'GRC',
 'Hungary': 'HUN', 'Iceland': 'ISL', 'Ireland (Republic)': 'IRL', 'Italy': 'ITA', 'Luxembourg': 'LUX', 'Malta': 'MLT', 'Montenegro': 'MNE',
 'Netherlands': 'NLD', 'Norway': 'NOR', 'Poland': 'POL', 'Portugal': 'PRT', 'Romania': 'ROU', 'Serbia': 'SRB', 'Slovakia': 'SVK', 'Slovenia': 'SVN',
 'Spain': 'ESP', 'Sweden': 'SWE', 'Switzerland': 'CHE', 'Ukraine': 'UKR', 'Canada': 'CAN', 'USA': 'USA', 'Bahamas': 'BHS', 'Barbados': 'BRB',
 'Bermuda': 'BMU', 'Belize': 'BLZ', 'Jamaica': 'JAM', 'Trinidad & Tobago': 'TTO', 'Netherlands Antilles': 'ANT', 'Mexico': 'MEX', 'Bolivia': 'BOL',
 'Chile': 'CHL', 'Paraguay': 'PRY', 'Uruguay': 'URY', 'Venezuela': 'VEN', 'Abu Dhabi': 'ARE', 'UAE': 'ARE', 'Bahrain': 'BHR', 'Kuwait': 'KWT',
 'Oman': 'OMN', 'Qatar': 'QAT', 'Saudi Arabia': 'SAU', 'Afghanistan': 'AFG', 'Bhutan': 'BTN', 'Hong Kong': 'HKG', 'Iraq': 'IRQ', 'Israel': 'ISR',
 'Jordan': 'JOR', 'Lebanon': 'LBN', 'Macau': 'MAC', 'Maldives': 'MDV', 'Mongolia': 'MNG', 'Pakistan': 'PAK', 'Philippines': 'PHL', 'Singapore': 'SGP',
 'Syria': 'SYR', 'Yemen': 'YEM', 'Algeria': 'DZA', 'Angola': 'AGO', 'Benin': 'BEN', 'Botswana': 'BWA', 'Burkina Faso': 'BFA', 'Central African Rep': 'CAF',
 'Chad': 'TCD', 'Congo Rep.': 'COG', 'Djibouti': 'DJI', 'Egypt': 'EGY', 'Eritrea': 'ERI', 'Gabon': 'GAB', 'Gambia': 'GMB', 'Ghana': 'GHA', 'Guinea': 'GIN',
 'Ivory Coast': 'CIV', 'Lesotho': 'LSO', 'Liberia': 'LBR', 'Libya': 'LBY', 'Madagascar': 'MDG', 'Mali': 'MLI', 'Mauritania': 'MRT', 'Morocco': 'MAR',
 'Namibia': 'NAM', 'Niger': 'NER', 'Nigeria': 'NGA', 'Reunion': 'REU', 'Senegal': 'SEN', 'Seychelles': 'SYC', 'Sierra Leone': 'SLE', 'Somalia': 'SOM',
 'Sudan': 'SDN', 'Swaziland': 'SWZ', 'Togo': 'TGO', 'Tunisia': 'TUN', 'Zambia': 'ZMB', 'Australia': 'AUS', 'Fiji': 'FJI', 'New Zealand': 'NZL',
}
GROUPS = {'Other C I S', 'Baltic States', 'Central America', 'Other Arab. States', 'Canary Islands', 'Ceuta', 'Melilla'}
world = {}
if itc_dir:
    ix, im = {}, {}
    for fn, tgt, el in (('itc_supplement_2025_exports_t.csv', ix, 'x'), ('itc_supplement_2025_imports_t.csv', im, 'm')):
        for r in csv.DictReader(open(os.path.join(itc_dir, fn), encoding='utf-8')):
            n = r['country'].replace(' (producer)', '')
            for y in range(ITC_FROM, LAST + 1):
                v = float(r[str(y)])
                if n == 'World': world.setdefault(y, {})[el] = v; continue
                if n in GROUPS or n.startswith('Other countries'): continue
                i3 = ITC[n]; d = tgt.setdefault(i3, {}); d[y] = d.get(y, 0) + v
    for i3 in set(fx) | set(fm) | set(ix) | set(im):
        for y in range(1961, LAST + 1):
            if y < ITC_FROM:
                v = fao_row(i3, y)
            elif i3 in ix or i3 in im:
                x, m = ix.get(i3, {}).get(y), im.get(i3, {}).get(y)
                v = [x, m] if x is not None or m is not None else None
                if v: rows[(i3, y)] = v + ['itc']; continue
            else:
                v = fao_row(i3, y)
            if v and (v[0] or v[1]): rows[(i3, y)] = v + ['fao']
    for i3 in set(ix) | set(im):
        if i3 not in place:   # in the ITC tables but not in FAO's trade list
            extra = {'GIB': ('Gibraltar', '292', 'europe-west-asia'), 'BMU': ('Bermuda', '060', 'americas'),
                     'ANT': ('Netherlands Antilles', None, 'americas'), 'REU': ('Réunion', None, 'eastern-africa')}
            n, m, rg = extra.get(i3, (i3, None, 'rest-of-africa'))
            place[i3] = {'name': prod_names.get(i3, n), 'map': m, 'region': rg}
else:
    for r in csv.DictReader(open(os.path.join(ROOT, '_data', 'tea_trade.csv'), encoding='utf-8')):
        y = int(r['year'])
        if r['iso3'] == 'WLD':
            if y >= ITC_FROM: world[y] = {'x': float(r['exports_t']), 'm': float(r['imports_t'])}
            continue
        if y >= ITC_FROM or True:
            f = lambda s: float(s) if s else None
            rows[(r['iso3'], y)] = [f(r['exports_t']), f(r['imports_t']), r['source']]

# ---- consumption, world totals ----
out = []
years = range(1961, LAST + 1)
for (i3, y), (x, m, src) in sorted(rows.items(), key=lambda kv: (place[kv[0][0]]['name'], kv[0][1])):
    p = prod.get(i3, {}).get(y)
    if i3 in growers:
        c = p + (m or 0) - (x or 0) if p is not None else None   # no production figure that year: no consumption
    else:
        c = m
    if c is not None and c <= 0: c = None
    if i3 == 'KEN': c = None   # Kenya's exports include tea grown in neighbouring countries, so the sum means nothing
    out.append([place[i3]['name'], i3, y, x, m, c, src])
W = []
for y in years:
    sx = sum(r[3] or 0 for r in out if r[2] == y); sm = sum(r[4] or 0 for r in out if r[2] == y); sc = sum(r[5] or 0 for r in out if r[2] == y)
    wx, wm = (world[y]['x'], world[y]['m']) if y in world else (sx, sm)
    W.append(['World', 'WLD', y, wx, wm, sc, 'itc' if y in world else 'fao'])
r0 = lambda v: '' if v is None else str(round(v))
with open(os.path.join(ROOT, '_data', 'tea_trade.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['country', 'iso3', 'year', 'exports_t', 'imports_t', 'consumption_t', 'source'])
    for r in out + W: w.writerow(r[:3] + [r0(v) for v in r[3:6]] + [r[6]])

# compact JSON: series by country, years from 1961
idx = lambda y: y - 1961
J = {'from': 1961, 'to': LAST, 'places': {}, 'exports': {}, 'imports': {}, 'consumption': {}, 'world': {'exports': [], 'imports': [], 'consumption': []}}
for r in out:
    i3 = r[1]
    if i3 not in J['places']: J['places'][i3] = [place[i3]['name'], place[i3]['map'], place[i3]['region']]
    for k, v in (('exports', r[3]), ('imports', r[4]), ('consumption', r[5])):
        if v is None or v <= 0: continue
        a = J[k].setdefault(i3, [None] * (LAST - 1960)); a[idx(r[2])] = round(v)
for r in W:
    for k, v in (('exports', r[3]), ('imports', r[4]), ('consumption', r[5])): J['world'][k].append(round(v) if v else None)
json.dump(J, open(os.path.join(ROOT, '_data', 'tea_trade_series.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(len(out), 'rows;', len(J['places']), 'places')
