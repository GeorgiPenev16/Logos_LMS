#!/usr/bin/env python3
"""
scripts/build_bg_address.py
────────────────────────────
Builds Bulgarian address reference data by merging:
  - ekatte/ek_obl.xlsx          → 28 oblasts  (official NSI, EKATTE)
  - ekatte/ek_atte.xlsx         → 5,256 settlements (NSI, EKATTE codes)
  - ekatte/ek_obst.xlsx         → 265 municipalities (NSI)
  - bgplaces_PostgreSQL.sql     → postcodes + coordinates

Outputs (stdlib only — no pip required):
  - data/res_country_state_bg.xml   28 oblasts as res.country.state records
  - data/bg_settlement_data.csv     full merged settlement table

Usage (run from project root):
    python3 scripts/build_bg_address.py
"""

import os
import re
import csv
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter

# ─────────────────────────────────────────────────────────────────────────────
# Paths  (resolve relative to this script's location)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BASE        = os.path.dirname(SCRIPT_DIR)          # project root
EKATTE_DIR  = os.path.join(BASE, 'ekatte')
SQL_PATH    = os.path.join(BASE, 'bgplaces_PostgreSQL.sql')
OUT_DIR     = os.path.join(BASE, 'data')
OUT_XML     = os.path.join(OUT_DIR, 'res_country_state_bg.xml')
OUT_CSV     = os.path.join(OUT_DIR, 'bg_settlement_data.csv')

CSV_FIELDS = [
    'ekatte', 'name_bg', 'name_en', 'type_prefix',
    'obl_code', 'mun_code', 'mun_name', 'nuts3',
    'postcode', 'lat', 'lng', 'match_source',
]

# ─────────────────────────────────────────────────────────────────────────────
# XLSX reader  (stdlib: zipfile + xml.etree)
# ─────────────────────────────────────────────────────────────────────────────

def read_xlsx(path):
    """
    Read first worksheet of an xlsx file.
    Returns a list-of-lists (all rows, including header rows).
    No pip required — uses only zipfile + xml.etree.
    """
    NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    ns = {'ns': NS}

    with zipfile.ZipFile(path) as z:
        # ── Shared strings table ──────────────────────────────────────────────
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            tree = ET.parse(z.open('xl/sharedStrings.xml'))
            for si in tree.findall('.//ns:si', ns):
                parts = si.findall('.//ns:t', ns)
                shared.append(''.join(p.text or '' for p in parts))

        # ── Worksheet data ────────────────────────────────────────────────────
        sheet_path = 'xl/worksheets/sheet1.xml'
        tree = ET.parse(z.open(sheet_path))
        rows = []
        for row_el in tree.findall('.//ns:row', ns):
            row_vals = []
            for c in row_el.findall('ns:c', ns):
                cell_type = c.get('t', '')
                v_el = c.find('ns:v', ns)
                val  = v_el.text if v_el is not None else None
                if cell_type == 's' and val is not None:
                    val = shared[int(val)]
                row_vals.append(val)
            rows.append(row_vals)
    return rows


def get_data_rows(rows):
    """
    Skip NSI metadata header (3 rows) and column-header row.
    Row layout in all EKATTE files:
      [0]  generation timestamp
      [1]  data currency date
      [2]  empty
      [3]  column names
      [4+] data
    """
    return rows[4:]


def safe(val):
    """Return stripped string or empty string for None."""
    return (val or '').strip()


# ─────────────────────────────────────────────────────────────────────────────
# XML helper
# ─────────────────────────────────────────────────────────────────────────────

def xml_escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Load oblasts from ek_obl.xlsx
# ─────────────────────────────────────────────────────────────────────────────
#
# Columns (data rows):
#   [0] centre_ekatte   [1] centre_name   [2] obl_code   [3] name_bg
#   [4] name_en         [5] NUTS1         [6] NUTS2       [7] NUTS3
#   [8] doc_code        [9] seq
#
# Special cases:
#   SOF = "София (столица)"  — capital / Sofia City Province
#   SFO = "София (област)"  — Sofia Province (rest of the region)

def load_oblasts():
    rows = get_data_rows(read_xlsx(os.path.join(EKATTE_DIR, 'ek_obl.xlsx')))
    oblasts = []
    for r in rows:
        if not r or not safe(r[2]):
            continue
        code    = safe(r[2])
        name_bg = safe(r[3])
        name_en = safe(r[4])
        nuts3   = safe(r[7]) if len(r) > 7 else ''
        centre  = safe(r[0])

        # Disambiguate Sofia — both have name_bg="София" in NSI source
        if code == 'SOF':
            name_bg = 'София (столица)'
            name_en = 'Sofia (stolitsa)'
        elif code == 'SFO':
            name_bg = 'София (област)'
            name_en = 'Sofia (oblast)'

        oblasts.append({
            'obl_code':      code,
            'name_bg':       name_bg,
            'name_en':       name_en,
            'nuts3':         nuts3,
            'ekatte_center': centre,
        })
    return oblasts


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Load municipalities from ek_obst.xlsx
# ─────────────────────────────────────────────────────────────────────────────
#
# Columns:
#   [0] mun_code   [1] centre_ekatte   [2] centre_name   [3] name_bg
#   [4] name_en    [5] NUTS1           [6] NUTS2          [7] NUTS3
#   [8] category   [9] doc_code        [10] seq

def load_municipalities():
    rows = get_data_rows(read_xlsx(os.path.join(EKATTE_DIR, 'ek_obst.xlsx')))
    munis = {}
    for r in rows:
        if not r or not safe(r[0]):
            continue
        mun_code = safe(r[0])
        munis[mun_code] = {
            'mun_code': mun_code,
            'name_bg':  safe(r[3]),
            'name_en':  safe(r[4]),
            'obl_code': mun_code[:3],   # first 3 chars = oblast code
        }
    return munis


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Load settlements from ek_atte.xlsx
# ─────────────────────────────────────────────────────────────────────────────
#
# Columns:
#   [0] EKATTE     [1] вид (type prefix)    [2] name_bg    [3] name_en
#   [4] obl_code   [5] obl_name (с обл.)    [6] mun_code   [7] mun_name
#   [8] кметство   [9] NUTS1   [10] NUTS2   [11] NUTS3
#   [12] type_code [13] category  [14] alt_code  [15] alt_text
#   [16] doc_code  [17] seq

def load_settlements():
    rows = get_data_rows(read_xlsx(os.path.join(EKATTE_DIR, 'ek_atte.xlsx')))
    settlements = []
    for r in rows:
        if not r or not safe(r[0]):
            continue
        settlements.append({
            'ekatte':      safe(r[0]),
            'type_prefix': safe(r[1]),
            'name_bg':     safe(r[2]),
            'name_en':     safe(r[3]),
            'obl_code':    safe(r[4]),
            'mun_code':    safe(r[6]),
            'mun_name':    safe(r[7]),
            'nuts3':       safe(r[11]) if len(r) > 11 else '',
        })
    return settlements


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Parse bgplaces SQL (stdlib: re only)
# ─────────────────────────────────────────────────────────────────────────────
#
# Extracts:
#   basemap.region  → {region_id: name_bg}
#   basemap.city    → list of dicts {name_bg, name_en, lat, lng, postcode, region_id}
#
# City row format:
#   (id, 'name_bg', 'name_en', 'slug', 'lat', 'lng', postcode|NULL, region_id, mun_id, type_id)
#
# Region row format:
#   (id, 'name_bg', 'name_en', 'slug')

CITY_RE = re.compile(
    r'^\('
    r'(\d+),\s*'            # id
    r"'([^']*)'"            # name_bg  (Cyrillic — no apostrophes)
    r",\s*'([^']*)'"        # name_en
    r",\s*'([^']*)'"        # slug
    r",\s*'([^']*)'"        # lat
    r",\s*'([^']*)'"        # lng
    r',\s*(NULL|\d+)'       # postcode (may be NULL)
    r',\s*(\d+)'            # region_id
    r',\s*(\d+)'            # municipality_id
    r',\s*(\d+)\)'          # type_id
)

REGION_RE = re.compile(
    r"^\((\d+),\s*'([^']+)',\s*'([^']+)',\s*'([^']+)'\)"
)


def parse_bgplaces_sql():
    """Return (regions_dict, cities_list)."""
    regions = {}
    cities  = []
    mode    = None   # 'city' | 'region' | None

    with open(SQL_PATH, encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.rstrip()

            # ── Detect section transitions ────────────────────────────────────
            if 'INSERT INTO basemap.city' in line:
                mode = 'city'
                continue
            elif 'INSERT INTO basemap.region' in line:
                mode = 'region'
                continue
            elif line.startswith('CREATE TABLE') or line.startswith('ALTER TABLE'):
                mode = None
                continue

            # ── Parse data lines ─────────────────────────────────────────────
            if mode == 'city' and line.startswith('('):
                clean = line.strip().rstrip(',').rstrip(';').strip()
                m = CITY_RE.match(clean)
                if m:
                    cities.append({
                        'name_bg':   m.group(2),
                        'name_en':   m.group(3),
                        'lat':       m.group(5),
                        'lng':       m.group(6),
                        'postcode':  None if m.group(7) == 'NULL' else m.group(7),
                        'region_id': int(m.group(8)),
                    })

            elif mode == 'region' and line.startswith('('):
                clean = line.strip().rstrip(',').rstrip(';').strip()
                m = REGION_RE.match(clean)
                if m:
                    regions[int(m.group(1))] = m.group(2)

    return regions, cities


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Build obl_code → bgplaces region_id mapping
# ─────────────────────────────────────────────────────────────────────────────
#
# bgplaces region table:
#   13 = "София"         ← SFO (Sofia Province)
#   14 = "София Столица" ← SOF (Sofia City)
#
# All 27 other oblasts match exactly by name_bg.

def build_obl_to_region(oblasts, bg_regions):
    """Return dict {obl_code: bgplaces_region_id}."""
    bg_name_to_id = {name: rid for rid, name in bg_regions.items()}

    obl_to_region = {}
    for obl in oblasts:
        code    = obl['obl_code']
        name_bg = obl['name_bg']

        # Hard-code Sofia ambiguity
        if code == 'SOF':
            obl_to_region[code] = bg_name_to_id.get('София Столица', 14)
            continue
        if code == 'SFO':
            obl_to_region[code] = bg_name_to_id.get('София', 13)
            continue

        # Exact name match
        rid = bg_name_to_id.get(name_bg)
        if not rid:
            # Fallback: case-insensitive
            nlow = name_bg.lower()
            for bg_name, bg_id in bg_name_to_id.items():
                if bg_name.lower() == nlow:
                    rid = bg_id
                    break

        obl_to_region[code] = rid

    return obl_to_region


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Build bgplaces lookup indexes
# ─────────────────────────────────────────────────────────────────────────────

def build_indexes(bg_cities):
    """
    Build four indexes for the waterfall match:
      by_name_region    (name_bg_lower, region_id) → [city, ...]
      by_en_region      (name_en_lower, region_id) → [city, ...]
      by_name_any       name_bg_lower              → [city, ...]
      by_en_any         name_en_lower              → [city, ...]
    """
    by_name_region = defaultdict(list)
    by_en_region   = defaultdict(list)
    by_name_any    = defaultdict(list)
    by_en_any      = defaultdict(list)

    for c in bg_cities:
        name_low = c['name_bg'].strip().lower()
        en_low   = c['name_en'].strip().lower() if c['name_en'] else ''
        rid      = c['region_id']

        by_name_region[(name_low, rid)].append(c)
        by_name_any[name_low].append(c)
        if en_low:
            by_en_region[(en_low, rid)].append(c)
            by_en_any[en_low].append(c)

    return by_name_region, by_en_region, by_name_any, by_en_any


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Match settlements (waterfall)
# ─────────────────────────────────────────────────────────────────────────────
#
# Pass 1: name_bg + same oblast          → 'exact'  / 'exact_multi'
# Pass 2: name_en + same oblast          → 'name_en' / 'name_en_multi'
# Pass 3: name_bg across all oblasts     → 'cross_obl_bg'
# Pass 4: name_en across all oblasts     → 'cross_obl_en'
# Fallback:                              → 'no_match'
#
# For multi-hits we take the first entry (closest is indeterminate without
# coordinates on the EKATTE side).  The match_source suffix '_multi' flags
# these for manual review.

def _pick(hits):
    """Return (city_dict, is_multi)."""
    if not hits:
        return None, False
    return hits[0], len(hits) > 1


def match_settlements(settlements, obl_to_region,
                      by_name_region, by_en_region,
                      by_name_any, by_en_any):
    result = []

    for s in settlements:
        obl_code  = s['obl_code']
        region_id = obl_to_region.get(obl_code)
        nb        = s['name_bg'].lower()
        ne        = s['name_en'].lower()

        postcode = lat = lng = None
        match_source = None

        # Pass 1 — name_bg + same oblast
        if region_id:
            hits = by_name_region.get((nb, region_id), [])
            city, is_multi = _pick(hits)
            if city:
                postcode     = city['postcode']
                lat          = city['lat']
                lng          = city['lng']
                match_source = 'exact_multi' if is_multi else 'exact'

        # Pass 2 — name_en + same oblast
        if not match_source and region_id and ne:
            hits = by_en_region.get((ne, region_id), [])
            city, is_multi = _pick(hits)
            if city:
                postcode     = city['postcode']
                lat          = city['lat']
                lng          = city['lng']
                match_source = 'name_en_multi' if is_multi else 'name_en'

        # Pass 3 — name_bg any oblast (cross-region)
        if not match_source:
            hits = by_name_any.get(nb, [])
            city, is_multi = _pick(hits)
            if city:
                postcode     = city['postcode']
                lat          = city['lat']
                lng          = city['lng']
                match_source = 'cross_obl_bg_multi' if is_multi else 'cross_obl_bg'

        # Pass 4 — name_en any oblast
        if not match_source and ne:
            hits = by_en_any.get(ne, [])
            city, is_multi = _pick(hits)
            if city:
                postcode     = city['postcode']
                lat          = city['lat']
                lng          = city['lng']
                match_source = 'cross_obl_en_multi' if is_multi else 'cross_obl_en'

        if not match_source:
            match_source = 'no_match'

        result.append({
            'ekatte':       s['ekatte'],
            'name_bg':      s['name_bg'],
            'name_en':      s['name_en'],
            'type_prefix':  s['type_prefix'],
            'obl_code':     obl_code,
            'mun_code':     s['mun_code'],
            'mun_name':     s['mun_name'],
            'nuts3':        s['nuts3'],
            'postcode':     postcode or '',
            'lat':          lat or '',
            'lng':          lng or '',
            'match_source': match_source,
        })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — Write res_country_state_bg.xml
# ─────────────────────────────────────────────────────────────────────────────

def write_xml(oblasts, out_path):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<odoo>',
        '    <data noupdate="1">',
        '        <!--',
        '            Bulgarian oblasts (28) → res.country.state',
        '            Source: NSI EKATTE ek_obl.xlsx',
        '            Generated by: scripts/build_bg_address.py',
        '        -->',
        '',
    ]

    for obl in oblasts:
        xml_id   = f"state_bg_{obl['obl_code']}"
        name_esc = xml_escape(obl['name_bg'])
        code     = xml_escape(obl['obl_code'])
        lines += [
            f'        <record id="{xml_id}" model="res.country.state">',
            f'            <field name="country_id" ref="base.bg"/>',
            f'            <field name="name">{name_esc}</field>',
            f'            <field name="code">{code}</field>',
            f'        </record>',
            '',
        ]

    lines += [
        '    </data>',
        '</odoo>',
    ]

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — Write bg_settlement_data.csv
# ─────────────────────────────────────────────────────────────────────────────

def write_csv(settlements, out_path):
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(settlements)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 10 — Print merge report
# ─────────────────────────────────────────────────────────────────────────────

def print_report(oblasts, munis, enriched):
    total     = len(enriched)
    mc        = Counter(s['match_source'] for s in enriched)
    w_post    = sum(1 for s in enriched if s['postcode'])

    exact     = mc['exact'] + mc['exact_multi']
    name_en_m = mc['name_en'] + mc['name_en_multi']
    cross_bg  = mc['cross_obl_bg'] + mc['cross_obl_bg_multi']
    cross_en  = mc['cross_obl_en'] + mc['cross_obl_en_multi']
    no_match  = mc['no_match']

    def pct(n): return f"{100*n//total}%" if total else "0%"

    print()
    print("=" * 55)
    print("  MERGE REPORT")
    print("=" * 55)
    print(f"  Oblasts:              {len(oblasts)}")
    print(f"  Municipalities:       {len(munis)}")
    print(f"  Settlements (total):  {total}")
    print(f"    - Exact match:      {exact:5d}  ({pct(exact)})")
    print(f"    - Name_en match:    {name_en_m:5d}  ({pct(name_en_m)})")
    print(f"    - Cross-obl BG:     {cross_bg:5d}  ({pct(cross_bg)})")
    print(f"    - Cross-obl EN:     {cross_en:5d}  ({pct(cross_en)})")
    print(f"    - No match:         {no_match:5d}  ({pct(no_match)})")
    print(f"    - With postcode:    {w_post:5d}  ({pct(w_post)})")
    print("=" * 55)
    print(f"  Output: data/res_country_state_bg.xml")
    print(f"  Output: data/bg_settlement_data.csv")
    print("=" * 55)

    # Detailed breakdown of unmatched (for visibility)
    if no_match:
        print(f"\n  No-match settlements ({no_match} total — sample 15):")
        count = 0
        for s in enriched:
            if s['match_source'] == 'no_match' and count < 15:
                print(f"    {s['ekatte']}  {s['type_prefix']:<5} {s['name_bg']:<30} obl={s['obl_code']}")
                count += 1


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("build_bg_address.py — Bulgarian address reference builder")
    print(f"Base: {BASE}")
    print()

    os.makedirs(OUT_DIR, exist_ok=True)

    # ── Load sources ──────────────────────────────────────────────────────────
    print("  Loading ek_obl.xlsx  ...", end='', flush=True)
    oblasts = load_oblasts()
    print(f" {len(oblasts)} oblasts")

    print("  Loading ek_obst.xlsx ...", end='', flush=True)
    munis = load_municipalities()
    print(f" {len(munis)} municipalities")

    print("  Loading ek_atte.xlsx ...", end='', flush=True)
    settlements = load_settlements()
    print(f" {len(settlements)} settlements")

    print("  Parsing bgplaces SQL ...", end='', flush=True)
    bg_regions, bg_cities = parse_bgplaces_sql()
    print(f" {len(bg_regions)} regions, {len(bg_cities)} cities")

    # ── Build mapping and indexes ─────────────────────────────────────────────
    print("  Building indexes     ...", end='', flush=True)
    obl_to_region = build_obl_to_region(oblasts, bg_regions)
    by_name_region, by_en_region, by_name_any, by_en_any = build_indexes(bg_cities)
    print(" done")

    # ── Match ─────────────────────────────────────────────────────────────────
    print("  Matching EKATTE ↔ bgplaces ...", end='', flush=True)
    enriched = match_settlements(
        settlements, obl_to_region,
        by_name_region, by_en_region,
        by_name_any, by_en_any,
    )
    print(" done")

    # ── Write outputs ─────────────────────────────────────────────────────────
    print(f"  Writing XML ...", end='', flush=True)
    write_xml(oblasts, OUT_XML)
    print(" done")

    print(f"  Writing CSV ...", end='', flush=True)
    write_csv(enriched, OUT_CSV)
    print(" done")

    # ── Report ────────────────────────────────────────────────────────────────
    print_report(oblasts, munis, enriched)

    # ── CSV preview ───────────────────────────────────────────────────────────
    print("\nFirst 5 rows of bg_settlement_data.csv:")
    print(",".join(CSV_FIELDS))
    for row in enriched[:5]:
        print(",".join(str(row[f]) for f in CSV_FIELDS))
    print()


if __name__ == '__main__':
    main()
