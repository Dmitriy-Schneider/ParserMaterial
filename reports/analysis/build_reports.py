import csv
import re
import sqlite3
from collections import defaultdict, Counter
from html.parser import HTMLParser
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.fill_standards_with_ai import detect_standard_pattern, normalize_standard_prefix, STANDARD_COUNTRIES

OUTPUT_DIR = Path('reports/analysis')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path('database/steel_database.db')

COMPOSITION_KEYS = ['c','cr','mo','v','w','co','ni','mn','si','s','p','cu','nb','n','tech']


def clean_text(v):
    if v is None:
        return ''
    return ' '.join(str(v).replace('\xa0', ' ').split())


def norm_grade(v):
    if v is None:
        return None
    text = clean_text(v).strip()
    if text in ('', '-', '—', '–'):
        return None
    return text


def norm_value(v):
    if v is None:
        return None
    text = clean_text(v)
    if text in ('', '-', '—', '–', '?'):
        return None
    return text


def has_qualifier(v):
    if not v:
        return False
    return bool(re.search(r'\bдо\b|\bmin\b|\bмакс\b|\bmax\b|<=|>=|≤|≥', str(v), re.IGNORECASE))


def has_range(v):
    if not v:
        return False
    s = str(v)
    return '-' in s and not s.strip().startswith('-')


def has_comma(v):
    if not v:
        return False
    return ',' in str(v)


def split_analogues(raw, source):
    if not raw:
        return []
    if source == 'splav':
        return [tok for tok in re.split(r'\s+', raw) if tok]
    return [tok for tok in raw.split('|') if tok]


CC_COUNTRY_MAP = {
    'AT': 'Австрия',
    'BE': 'Бельгия',
    'BR': 'Бразилия',
    'CH': 'Швейцария',
    'CN': 'Китай',
    'CZ': 'Чехия',
    'DE': 'Германия',
    'EN': 'Европа',
    'ES': 'Испания',
    'EU': 'Европа',
    'FN': 'Финляндия',
    'FR': 'Франция',
    'IT': 'Италия',
    'JP': 'Япония',
    'LU': 'Люксембург',
    'NO': 'Норвегия',
    'PL': 'Польша',
    'RU': 'Россия',
    'SE': 'Швеция',
    'SI': 'Словения',
    'UA': 'Украина',
    'UK': 'Великобритания',
    'US': 'США',
    'SW': 'Швеция',
    'GR': 'Греция',
}

CSV_STANDARD_MAP = {
    'Bohler': ('Bohler', 'Австрия'),
    'Uddeholm': ('Uddeholm', 'Швеция'),
    'Buderus': ('Buderus', 'Германия'),
    'EN': ('EN', 'Европа'),
    'AISI': ('AISI', 'США'),
    'UNS': ('UNS', 'США'),
}

print('[INFO] Loading DB...')
conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
cur = conn.cursor()
cur.execute('SELECT grade, standard, manufacturer, link FROM steel_grades')
rows = cur.fetchall()

DB_GRADES = set()
DB_SPLAV = {}
DB_ZKNIVES = {}
DB_BY_GRADE_LINK = {}

for grade, standard, manufacturer, link in rows:
    g = norm_grade(grade)
    if not g:
        continue
    DB_GRADES.add(g)
    rec = {
        'grade': grade,
        'standard': standard or '',
        'manufacturer': manufacturer or '',
        'link': link or '',
    }
    DB_BY_GRADE_LINK[(g, link or '')] = rec
    if link and 'splav-kharkov.com' in link:
        DB_SPLAV[g] = rec
    if link and 'zknives.com' in link:
        DB_ZKNIVES[g] = rec

conn.close()
print(f'[INFO] DB grades: {len(DB_GRADES)}')
print('[INFO] Parsing splav_ru_grades.csv...')
splav_path = Path('reports/splav_ru_grades.csv')
SPLAV_RECORDS = {}
if splav_path.exists():
    with splav_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            grade_raw = row.get('grade')
            grade = norm_grade(grade_raw)
            if not grade:
                continue
            link = (row.get('link') or '').strip()
            db_rec = DB_SPLAV.get(grade)
            db_std = db_rec['standard'] if db_rec else ''
            record = {
                'grade_raw': grade_raw,
                'grade_norm': grade,
                'source': 'splav',
                'link': link,
                'standard_expected': db_std or (row.get('standard') or ''),
                'standard_source': 'db' if db_std else 'splav_csv',
                'manufacturer_expected': row.get('manufacturer') or '',
                'country_expected': 'Россия' if (db_std or row.get('standard')) else '',
                'standard_db': db_std,
                'manufacturer_db': db_rec['manufacturer'] if db_rec else '',
                'cc': '',
                'country_cc': '',
                'country_card': '',
                'maker_card': '',
                'maker_table': '',
                'standard_expected_source': 'db' if db_std else 'splav_csv',
                'analogues': row.get('analogues') or '',
            }
            for key in COMPOSITION_KEYS:
                record[key] = norm_value(row.get(key))
            SPLAV_RECORDS[grade] = record
            if idx % 500 == 0:
                print(f'[INFO] Splav rows processed: {idx}')
else:
    print('[WARN] splav_ru_grades.csv not found')

print(f'[INFO] Splav records: {len(SPLAV_RECORDS)}')


class ZParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.in_name_cell = False
        self.in_anchor = False
        self.cell_index = -1
        self.current_cell = []
        self.current_cells = []
        self.current_anchor = []
        self.current_anchor_href = None
        self.anchor_items = []
        self.entries = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'table' and attrs_dict.get('id') == 'steelData':
            self.in_table = True
        if self.in_table and tag == 'tr':
            self.in_row = True
            self.cell_index = -1
            self.current_cells = []
            self.anchor_items = []
        if self.in_row and tag in ('td', 'th'):
            self.in_cell = True
            self.cell_index += 1
            self.current_cell = []
            if self.cell_index == 1:
                self.in_name_cell = True
        if self.in_name_cell and tag == 'a':
            self.in_anchor = True
            self.current_anchor = []
            self.current_anchor_href = attrs_dict.get('href')

    def handle_endtag(self, tag):
        if self.in_anchor and tag == 'a':
            text = clean_text(''.join(self.current_anchor))
            if text:
                self.anchor_items.append({'text': text, 'href': self.current_anchor_href})
            self.in_anchor = False
            self.current_anchor_href = None
        if self.in_cell and tag in ('td', 'th'):
            text = clean_text(''.join(self.current_cell))
            self.current_cells.append(text)
            self.in_cell = False
            if self.cell_index == 1:
                self.in_name_cell = False
        if self.in_row and tag == 'tr':
            if self.current_cells:
                self.entries.append({'anchors': list(self.anchor_items), 'cells': list(self.current_cells)})
            self.in_row = False
            self.anchor_items = []
        if tag == 'table' and self.in_table:
            self.in_table = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)
        if self.in_anchor:
            self.current_anchor.append(data)


print('[INFO] Parsing zknives_steelchart.html...')
page_info = {}
page_info_path = Path('reports/zknives_page_info.csv')
if page_info_path.exists():
    with page_info_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            link = (row.get('link') or '').strip()
            if not link:
                continue
            page_info[link] = {
                'maker': clean_text(row.get('maker')),
                'country': clean_text(row.get('country')),
                'cc': clean_text(row.get('cc')).upper(),
                'title': clean_text(row.get('title')),
                'country_raw': clean_text(row.get('country_raw')),
            }

ZKNIVES_RECORDS = {}
zknives_html = Path('reports/zknives_steelchart.html')
if zknives_html.exists():
    html = zknives_html.read_text(encoding='iso-8859-1', errors='replace')
    parser = ZParser()
    parser.feed(html)

    index_map = {
        2: 'base',
        3: 'c',
        4: 'cr',
        5: 'mo',
        6: 'v',
        7: 'w',
        8: 'co',
        9: 'ni',
        10: 'mn',
        11: 'si',
        12: 's',
        13: 'p',
        14: 'cu',
        15: 'nb',
        16: 'n',
        17: 'tech',
        18: 'maker_table',
        19: 'cc',
    }

    for idx, entry in enumerate(parser.entries, start=1):
        anchors = entry.get('anchors') or []
        if not anchors:
            continue
        cells = entry.get('cells') or []
        row_data = {}
        for col_idx, key in index_map.items():
            value = cells[col_idx] if col_idx < len(cells) else ''
            row_data[key] = norm_value(value)

        cc = (row_data.get('cc') or '').upper()
        country_cc = CC_COUNTRY_MAP.get(cc, '')
        anchor_names = [clean_text(a.get('text')) for a in anchors if clean_text(a.get('text'))]

        for a in anchors:
            grade_raw = clean_text(a.get('text'))
            if not grade_raw:
                continue
            grade = norm_grade(grade_raw)
            href = (a.get('href') or '').strip()
            link = href
            if link and not link.startswith('http'):
                link = f"https://zknives.com/knives/steels/{link.lstrip('/')}"

            analogues_list = [g for g in anchor_names if g and g != grade_raw]
            analogues_str = '|'.join(analogues_list)

            card = page_info.get(link, {}) if link else {}
            maker_card = card.get('maker', '')
            country_card = card.get('country', '')
            cc_card = card.get('cc', '')

            maker_table = row_data.get('maker_table') or ''
            maker = maker_card or maker_table

            country_expected = country_cc or CC_COUNTRY_MAP.get(cc_card, '') or country_card

            expected_standard = ''
            expected_source = ''
            if maker:
                if country_expected:
                    expected_standard = f"{maker}, {country_expected}"
                else:
                    expected_standard = maker
                expected_source = 'card_maker' if maker_card else 'table_maker'
            else:
                detection = detect_standard_pattern(grade_raw, None, None)
                if detection.get('type') == 'government':
                    prefix = normalize_standard_prefix(detection.get('standard_prefix'))
                    number = detection.get('standard_number')
                    country = country_expected or STANDARD_COUNTRIES.get(prefix)
                    if prefix and country:
                        expected_standard = f"{prefix} {number}, {country}" if number else f"{prefix}, {country}"
                        expected_source = 'pattern'
                elif detection.get('type') == 'proprietary':
                    mfr = detection.get('manufacturer')
                    country = country_expected or detection.get('country')
                    if mfr and country:
                        expected_standard = f"{mfr}, {country}"
                        expected_source = 'pattern'

            db_rec = DB_ZKNIVES.get(grade) or DB_BY_GRADE_LINK.get((grade, link or ''))
            db_std = db_rec['standard'] if db_rec else ''
            db_mfr = db_rec['manufacturer'] if db_rec else ''

            record = {
                'grade_raw': grade_raw,
                'grade_norm': grade,
                'source': 'zknives',
                'link': link,
                'standard_expected': expected_standard,
                'standard_source': expected_source,
                'manufacturer_expected': maker,
                'country_expected': country_expected,
                'standard_db': db_std,
                'manufacturer_db': db_mfr,
                'cc': cc or cc_card,
                'country_cc': country_cc,
                'country_card': country_card,
                'maker_card': maker_card,
                'maker_table': maker_table,
                'standard_expected_source': expected_source,
                'analogues': analogues_str,
            }

            for key in COMPOSITION_KEYS:
                record[key] = row_data.get(key)

            ZKNIVES_RECORDS[grade] = record

        if idx % 500 == 0:
            print(f'[INFO] ZKnives rows processed: {idx}')
else:
    print('[WARN] zknives_steelchart.html not found')

print(f'[INFO] ZKnives records: {len(ZKNIVES_RECORDS)}')
ZKNIVES_MISSING = sorted([g for g in ZKNIVES_RECORDS if g not in DB_GRADES])
print('[INFO] Parsing CSV sources (unique only)...')

def parse_marki_vem(path):
    lines = Path(path).read_text(encoding='utf-8-sig').splitlines()
    header = None
    data_lines = []
    for i, line in enumerate(lines):
        if 'Bohler' in line and 'Uddeholm' in line and 'Buderus' in line:
            header = line.split(';')
            data_lines = lines[i+1:]
            break
    if not header:
        return []
    reader = csv.DictReader(data_lines, fieldnames=header, delimiter=';')
    records = []
    for row in reader:
        grades = {}
        for key in ['Bohler', 'Uddeholm', 'Buderus', 'EN']:
            val = row.get(key)
            if val and val.strip():
                grades[key] = val.strip().replace('~', '').strip()
        if not grades:
            continue
        comp = {
            'c': row.get('C'),
            'si': row.get('Si'),
            'mn': row.get('Mn'),
            'cr': row.get('Cr'),
            'mo': row.get('Mo'),
            'ni': row.get('Ni'),
            'v': row.get('V'),
            'w': row.get('W'),
            'co': None,
            'cu': None,
            'nb': None,
            'n': None,
            's': None,
            'p': None,
            'tech': row.get('проч'),
        }
        all_grade_names = list(grades.values())
        for std, grade in grades.items():
            g = norm_grade(grade)
            if not g:
                continue
            analogues = [a for a in all_grade_names if a != grade]
            prefix, country = CSV_STANDARD_MAP.get(std, (std, ''))
            manufacturer = prefix if std in ['Bohler', 'Uddeholm', 'Buderus'] else ''
            standard = f"{prefix}, {country}" if country else prefix
            records.append({
                'grade_norm': g,
                'grade_raw': grade,
                'source': Path(path).name,
                'standard_expected': standard,
                'manufacturer_expected': manufacturer,
                'country_expected': country,
                'analogues': '|'.join(analogues),
                'composition': comp,
            })
    return records


def parse_stainless(path, first_col_label, other_col_name):
    records = []
    with Path(path).open('r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            first = row.get(first_col_label)
            if not first or first.strip() in ['Аустенитные', 'Дуплексные', 'Мартенситные', 'Ферритные', 'Спец сплавы']:
                continue
            grades = {}
            if first and first.strip():
                grades['AISI'] = first.strip()
            if row.get('UNS') and row['UNS'].strip():
                grades['UNS'] = row['UNS'].strip()
            if row.get('EN') and row['EN'].strip() and row['EN'].strip() not in ['-', '—']:
                grades['EN'] = row['EN'].strip()
            if not grades:
                continue
            comp = {
                'c': row.get('C'),
                'mn': row.get('Mn'),
                'si': row.get('Si'),
                'cr': row.get('Cr'),
                'ni': row.get('Ni'),
                'p': row.get('P'),
                's': row.get('S'),
                'mo': row.get('Mo'),
                'n': row.get('N'),
                'cu': row.get('Cu'),
                'v': row.get('V'),
                'w': row.get('W'),
                'co': row.get('Co'),
                'nb': row.get('Nb'),
                'tech': row.get(other_col_name),
            }
            all_grade_names = list(grades.values())
            for std, grade in grades.items():
                g = norm_grade(grade)
                if not g:
                    continue
                analogues = [a for a in all_grade_names if a != grade]
                prefix, country = CSV_STANDARD_MAP.get(std, (std, ''))
                standard = f"{prefix}, {country}" if country else prefix
                records.append({
                    'grade_norm': g,
                    'grade_raw': grade,
                    'source': Path(path).name,
                    'standard_expected': standard,
                    'manufacturer_expected': '',
                    'country_expected': country,
                    'analogues': '|'.join(analogues),
                    'composition': comp,
                })
    return records


def parse_duplex(path):
    records = []
    with Path(path).open('r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            first = row.get('Марка AISI брендовые') or row.get('Марка AISI и брендовые')
            if not first:
                continue
            grades = {}
            if first and first.strip():
                grades['AISI'] = first.strip()
            if row.get('UNS') and row['UNS'].strip():
                grades['UNS'] = row['UNS'].strip()
            if row.get('EN') and row['EN'].strip() and row['EN'].strip() not in ['-', '—']:
                grades['EN'] = row['EN'].strip()
            if not grades:
                continue
            comp = {
                'c': row.get('C'),
                'cr': row.get('Cr'),
                'ni': row.get('Ni'),
                'mo': row.get('Mo'),
                'n': row.get('N'),
                'mn': row.get('Mn'),
                'cu': row.get('Cu'),
                'w': row.get('W'),
                'tech': row.get('Другие'),
            }
            all_grade_names = list(grades.values())
            for std, grade in grades.items():
                g = norm_grade(grade)
                if not g:
                    continue
                analogues = [a for a in all_grade_names if a != grade]
                prefix, country = CSV_STANDARD_MAP.get(std, (std, ''))
                standard = f"{prefix}, {country}" if country else prefix
                records.append({
                    'grade_norm': g,
                    'grade_raw': grade,
                    'source': Path(path).name,
                    'standard_expected': standard,
                    'manufacturer_expected': '',
                    'country_expected': country,
                    'analogues': '|'.join(analogues),
                    'composition': comp,
                })
    return records


def parse_special_alloys(path):
    records = []
    with Path(path).open('r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            grades = {}
            if row.get('Сплавы') and row['Сплавы'].strip():
                grades['Сплавы'] = row['Сплавы'].strip()
            if row.get('UNS') and row['UNS'].strip() and row['UNS'].strip() not in ['-', '—']:
                grades['UNS'] = row['UNS'].strip()
            if row.get('EN') and row['EN'].strip() and row['EN'].strip() not in ['-', '—']:
                grades['EN'] = row['EN'].strip()
            if not grades:
                continue
            other_parts = []
            for key in ['Fe', 'Al', 'Ti']:
                val = row.get(key)
                if val and val.strip() and val.strip() not in ['-', '—']:
                    other_parts.append(f"{key} {val.strip()}")
            if row.get('Прочие элементы') and row['Прочие элементы'].strip() and row['Прочие элементы'].strip() not in ['-', '—']:
                other_parts.append(row['Прочие элементы'].strip())
            tech = '; '.join(other_parts) if other_parts else None
            comp = {
                'ni': row.get('Ni'),
                'c': row.get('C'),
                'mn': row.get('Mn'),
                's': row.get('S'),
                'si': row.get('Si'),
                'cu': row.get('Cu'),
                'cr': row.get('Cr'),
                'co': row.get('Co'),
                'mo': row.get('Mo'),
                'tech': tech,
            }
            all_grade_names = list(grades.values())
            for std, grade in grades.items():
                g = norm_grade(grade)
                if not g:
                    continue
                analogues = [a for a in all_grade_names if a != grade]
                prefix, country = CSV_STANDARD_MAP.get(std, ('', ''))
                standard = f"{prefix}, {country}" if country else ''
                records.append({
                    'grade_norm': g,
                    'grade_raw': grade,
                    'source': Path(path).name,
                    'standard_expected': standard,
                    'manufacturer_expected': '',
                    'country_expected': country,
                    'analogues': '|'.join(analogues),
                    'composition': comp,
                })
    return records


CSV_RECORDS = {}
CSV_FILES = [
    ('Марки ВЭМ.csv', parse_marki_vem),
    ('Аустенитные стали.csv', lambda p: parse_stainless(p, 'Марка AISI и брендовые', 'Прочие элементы')),
    ('Дуплексные стали.csv', parse_duplex),
    ('Мартенситные.csv', lambda p: parse_stainless(p, 'Марки AISI и брендовые', 'Прочие элементы')),
    ('Спец сплавы.csv', parse_special_alloys),
    ('Ферритные стали.csv', lambda p: parse_stainless(p, 'Марки AISI и брендовые', 'Other Elements (прочие элементы)')),
]

splav_set = set(SPLAV_RECORDS.keys())
zknives_set = set(ZKNIVES_RECORDS.keys())

for file_name, parser in CSV_FILES:
    path = Path(file_name)
    if not path.exists():
        continue
    parsed = parser(file_name)
    for rec in parsed:
        grade = rec['grade_norm']
        if not grade:
            continue
        if grade in splav_set or grade in zknives_set:
            continue
        if grade in CSV_RECORDS:
            continue
        CSV_RECORDS[grade] = {
            'grade_raw': rec['grade_raw'],
            'grade_norm': grade,
            'source': f"csv:{rec['source']}",
            'link': '',
            'standard_expected': rec.get('standard_expected') or '',
            'standard_source': 'csv',
            'manufacturer_expected': rec.get('manufacturer_expected') or '',
            'country_expected': rec.get('country_expected') or '',
            'standard_db': '',
            'manufacturer_db': '',
            'cc': '',
            'country_cc': '',
            'country_card': '',
            'maker_card': '',
            'maker_table': '',
            'standard_expected_source': 'csv',
            'analogues': rec.get('analogues') or '',
        }
        comp = rec.get('composition', {})
        for key in COMPOSITION_KEYS:
            CSV_RECORDS[grade][key] = norm_value(comp.get(key))

print(f'[INFO] CSV unique records: {len(CSV_RECORDS)}')

MARKI_CHECK = {}
marki_path = Path('Марки сталей.csv')
if marki_path.exists():
    with marki_path.open('r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            grade_field = row.get('Grade')
            if not grade_field:
                continue
            parts = re.split(r'[\n\r\*]+', grade_field)
            maker = norm_value(row.get('Maker'))
            cc = norm_value(row.get('CC'))
            country = CC_COUNTRY_MAP.get(cc, '') if cc else ''
            standard = f"{maker}, {country}" if maker and country else ''
            comp = {k.lower(): row.get(k.upper()) for k in ['C','Cr','Mo','V','W','Co','Ni','Mn','Si','S','P','Cu','Nb','N']}
            comp['tech'] = row.get('Tech')
            for part in parts:
                g = norm_grade(part)
                if not g:
                    continue
                if g in splav_set or g in zknives_set:
                    continue
                if g in MARKI_CHECK:
                    continue
                MARKI_CHECK[g] = {
                    'grade_raw': part,
                    'grade_norm': g,
                    'source': 'marki_stalei_check',
                    'link': '',
                    'standard_expected': standard,
                    'standard_source': 'marki_stalei',
                    'manufacturer_expected': maker or '',
                    'country_expected': country or '',
                    'standard_db': '',
                    'manufacturer_db': '',
                    'cc': cc or '',
                    'country_cc': country or '',
                    'country_card': '',
                    'maker_card': '',
                    'maker_table': '',
                    'standard_expected_source': 'marki_stalei',
                    'analogues': '',
                    'check_only': '1',
                }
                for key in COMPOSITION_KEYS:
                    MARKI_CHECK[g][key] = norm_value(comp.get(key))

print(f'[INFO] Марки сталей check-only records: {len(MARKI_CHECK)}')
print('[INFO] Building master dataset...')
SOURCE_MAP = defaultdict(set)
for grade in SPLAV_RECORDS:
    SOURCE_MAP[grade].add('splav')
for grade in ZKNIVES_RECORDS:
    SOURCE_MAP[grade].add('zknives')
for grade in CSV_RECORDS:
    SOURCE_MAP[grade].add('csv')
for grade in MARKI_CHECK:
    SOURCE_MAP[grade].add('marki')

MASTER = {}
all_grades = set(SOURCE_MAP.keys())
for grade in all_grades:
    if grade in SPLAV_RECORDS:
        rec = SPLAV_RECORDS[grade].copy()
        primary = 'splav'
    elif grade in ZKNIVES_RECORDS:
        rec = ZKNIVES_RECORDS[grade].copy()
        primary = 'zknives'
    elif grade in CSV_RECORDS:
        rec = CSV_RECORDS[grade].copy()
        primary = 'csv'
    else:
        rec = MARKI_CHECK[grade].copy()
        primary = 'marki'
    rec['primary_source'] = primary
    rec['sources'] = '|'.join(sorted(SOURCE_MAP[grade]))
    rec.setdefault('check_only', '1' if primary == 'marki' else '')
    MASTER[grade] = rec

master_set = set(MASTER.keys())

for grade, rec in MASTER.items():
    analogues_raw = rec.get('analogues') or ''
    analogues_list = split_analogues(analogues_raw, rec.get('primary_source') or '')
    present = 0
    missing = []
    for a in analogues_list:
        gnorm = norm_grade(a)
        if not gnorm:
            continue
        if gnorm in master_set:
            present += 1
        else:
            if len(missing) < 5:
                missing.append(gnorm)
    rec['analogues_count'] = len(analogues_list)
    rec['analogues_present_count'] = present
    rec['analogues_missing_count'] = len(analogues_list) - present
    rec['analogues_missing_examples'] = '|'.join(missing)

    values = [rec.get(k) for k in COMPOSITION_KEYS]
    any_comp = any(v for v in values)
    rec['composition_any'] = '1' if any_comp else '0'
    rec['composition_all_empty'] = '0' if any_comp else '1'
    rec['composition_has_range'] = '1' if any(has_range(v) for v in values) else '0'
    rec['composition_has_qualifier'] = '1' if any(has_qualifier(v) for v in values) else '0'
    rec['composition_has_comma'] = '1' if any(has_comma(v) for v in values) else '0'


print('[INFO] Preparing report rows...')
# ZKnives standard review
zknives_standard_rows = []
for grade, rec in ZKNIVES_RECORDS.items():
    db_std = rec.get('standard_db') or ''
    expected = rec.get('standard_expected') or ''
    if db_std and 'zknives.com' in db_std.lower():
        status = 'placeholder'
    elif expected and db_std:
        status = 'match' if clean_text(db_std).lower() == clean_text(expected).lower() else 'mismatch'
    elif expected and not db_std:
        status = 'missing_db'
    else:
        status = 'unknown'
    zknives_standard_rows.append({
        'grade': rec.get('grade_raw') or rec.get('grade_norm'),
        'link': rec.get('link') or '',
        'db_standard': db_std,
        'expected_standard': expected,
        'standard_expected_source': rec.get('standard_expected_source') or '',
        'maker_card': rec.get('maker_card') or '',
        'maker_table': rec.get('maker_table') or '',
        'cc': rec.get('cc') or '',
        'country_cc': rec.get('country_cc') or '',
        'country_card': rec.get('country_card') or '',
        'status': status,
    })

zknives_missing_rows = [{'grade': g} for g in sorted([g for g in ZKNIVES_RECORDS if g not in DB_GRADES])]

splav_missing_rows = []
for g in sorted(SPLAV_RECORDS.keys()):
    if g not in DB_GRADES:
        splav_missing_rows.append({'grade': g})

csv_unique_rows = []
for grade, rec in CSV_RECORDS.items():
    row = {
        'grade': rec.get('grade_raw') or grade,
        'standard': rec.get('standard_expected') or '',
        'manufacturer': rec.get('manufacturer_expected') or '',
        'country': rec.get('country_expected') or '',
        'source': rec.get('source') or '',
        'analogues': rec.get('analogues') or '',
    }
    for key in COMPOSITION_KEYS:
        row[key] = rec.get(key) or ''
    csv_unique_rows.append(row)

marki_rows = []
for grade, rec in MARKI_CHECK.items():
    row = {
        'grade': rec.get('grade_raw') or grade,
        'standard': rec.get('standard_expected') or '',
        'manufacturer': rec.get('manufacturer_expected') or '',
        'country': rec.get('country_expected') or '',
        'source': rec.get('source') or '',
    }
    for key in COMPOSITION_KEYS:
        row[key] = rec.get(key) or ''
    marki_rows.append(row)

orphan_rows = []
for grade, rec in MASTER.items():
    analogues_raw = rec.get('analogues') or ''
    analogues_list = split_analogues(analogues_raw, rec.get('primary_source') or '')
    for a in analogues_list:
        gnorm = norm_grade(a)
        if gnorm and gnorm not in master_set:
            orphan_rows.append({
                'grade': rec.get('grade_raw') or grade,
                'source': rec.get('primary_source') or '',
                'analogue': a,
                'analogue_norm': gnorm,
                'analogues_raw': analogues_raw,
            })

empty_rows = []
for grade, rec in MASTER.items():
    if rec.get('composition_all_empty') == '1':
        empty_rows.append({
            'grade': rec.get('grade_raw') or grade,
            'source': rec.get('primary_source') or '',
            'link': rec.get('link') or '',
        })

summary_rows = [
    {'metric': 'splav_records', 'value': len(SPLAV_RECORDS)},
    {'metric': 'zknives_records', 'value': len(ZKNIVES_RECORDS)},
    {'metric': 'csv_unique_records', 'value': len(CSV_RECORDS)},
    {'metric': 'marki_check_records', 'value': len(MARKI_CHECK)},
    {'metric': 'master_total', 'value': len(MASTER)},
    {'metric': 'zknives_missing_in_db', 'value': len(zknives_missing_rows)},
    {'metric': 'splav_missing_in_db', 'value': len(splav_missing_rows)},
    {'metric': 'empty_composition_total', 'value': len(empty_rows)},
]


def write_csv(path, rows, fieldnames):
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, '') for k in fieldnames})


print('[INFO] Writing CSV reports...')
write_csv(OUTPUT_DIR / 'zknives_standard_review.csv', zknives_standard_rows,
          ['grade','link','db_standard','expected_standard','standard_expected_source','maker_card','maker_table','cc','country_cc','country_card','status'])
write_csv(OUTPUT_DIR / 'zknives_missing_grades.csv', zknives_missing_rows, ['grade'])
write_csv(OUTPUT_DIR / 'splav_missing_grades.csv', splav_missing_rows, ['grade'])
write_csv(OUTPUT_DIR / 'csv_unique_grades.csv', csv_unique_rows,
          ['grade','standard','manufacturer','country','source','analogues'] + COMPOSITION_KEYS)
write_csv(OUTPUT_DIR / 'marki_stalei_check.csv', marki_rows,
          ['grade','standard','manufacturer','country','source'] + COMPOSITION_KEYS)
write_csv(OUTPUT_DIR / 'analogues_orphan_tokens.csv', orphan_rows,
          ['grade','source','analogue','analogue_norm','analogues_raw'])
write_csv(OUTPUT_DIR / 'empty_composition.csv', empty_rows, ['grade','source','link'])
write_csv(OUTPUT_DIR / 'summary_counts.csv', summary_rows, ['metric','value'])

master_fields = [
    'grade_norm','grade_raw','primary_source','sources','link',
    'standard_expected','manufacturer_expected','country_expected',
    'standard_db','manufacturer_db','cc','country_cc','country_card','maker_card','maker_table',
    'standard_expected_source','analogues','analogues_count','analogues_present_count','analogues_missing_count','analogues_missing_examples',
    'composition_any','composition_all_empty','composition_has_range','composition_has_qualifier','composition_has_comma','check_only'
] + COMPOSITION_KEYS

master_rows = []
for grade, rec in MASTER.items():
    row = {
        'grade_norm': grade,
        'grade_raw': rec.get('grade_raw') or '',
        'primary_source': rec.get('primary_source') or '',
        'sources': rec.get('sources') or '',
        'link': rec.get('link') or '',
        'standard_expected': rec.get('standard_expected') or '',
        'manufacturer_expected': rec.get('manufacturer_expected') or '',
        'country_expected': rec.get('country_expected') or '',
        'standard_db': rec.get('standard_db') or '',
        'manufacturer_db': rec.get('manufacturer_db') or '',
        'cc': rec.get('cc') or '',
        'country_cc': rec.get('country_cc') or '',
        'country_card': rec.get('country_card') or '',
        'maker_card': rec.get('maker_card') or '',
        'maker_table': rec.get('maker_table') or '',
        'standard_expected_source': rec.get('standard_expected_source') or '',
        'analogues': rec.get('analogues') or '',
        'analogues_count': rec.get('analogues_count') or 0,
        'analogues_present_count': rec.get('analogues_present_count') or 0,
        'analogues_missing_count': rec.get('analogues_missing_count') or 0,
        'analogues_missing_examples': rec.get('analogues_missing_examples') or '',
        'composition_any': rec.get('composition_any') or '0',
        'composition_all_empty': rec.get('composition_all_empty') or '0',
        'composition_has_range': rec.get('composition_has_range') or '0',
        'composition_has_qualifier': rec.get('composition_has_qualifier') or '0',
        'composition_has_comma': rec.get('composition_has_comma') or '0',
        'check_only': rec.get('check_only') or '',
    }
    for key in COMPOSITION_KEYS:
        row[key] = rec.get(key) or ''
    master_rows.append(row)

write_csv(OUTPUT_DIR / 'master_grades_review.csv', master_rows, master_fields)

print('[OK] Reports written to reports/analysis')
print('[OK] Master CSV:', OUTPUT_DIR / 'master_grades_review.csv')
