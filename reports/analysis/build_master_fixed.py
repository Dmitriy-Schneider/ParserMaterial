
# -*- coding: utf-8 -*-
import csv
import re
import sqlite3
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

try:
    from utils.fill_standards_with_ai import detect_standard_pattern, normalize_standard_prefix
except Exception:
    detect_standard_pattern = None
    normalize_standard_prefix = None

OUTPUT_DIR = Path('reports/analysis')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path('database/steel_database.db')
SPLAV_PATH = Path('reports/splav_ru_grades.csv')
ZKNIVES_HTML = Path('reports/zknives_steelchart.html')
ZKNIVES_PAGE_INFO = Path('reports/zknives_page_info.csv')
MARKI_PATH = Path('Марки сталей.csv')

CSV_FILES = [
    'Марки ВЭМ.csv',
    'Аустенитные стали.csv',
    'Дуплексные стали.csv',
    'Мартенситные.csv',
    'Спец сплавы.csv',
    'Ферритные стали.csv',
]

COMPOSITION_KEYS = ['c', 'cr', 'mo', 'v', 'w', 'co', 'ni', 'mn', 'si', 's', 'p', 'cu', 'nb', 'n']

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

COUNTRY_STANDARD_DEFAULT = {
    'Россия': 'ГОСТ',
    'Китай': 'GB',
    'Япония': 'JIS',
    'США': 'AISI',
    'Германия': 'DIN',
    'Франция': 'AFNOR',
    'Италия': 'UNI',
    'Польша': 'PN',
    'Чехия': 'CSN',
    'Великобритания': 'BS',
    'Швеция': 'SS',
    'Европа': 'EN',
}

STANDARD_PREFIXES = [
    'BS EN',
    'GB/T',
    'GOST R',
    'AISI',
    'ASTM',
    'UNS',
    'SAE',
    'GOST',
    'DIN',
    'EN',
    'ISO',
    'JIS',
    'GB',
    'BS',
    'AFNOR',
    'NF',
    'UNI',
    'SIS',
    'SS',
    'PN',
    'CSN',
    'KS',
    'AS',
    'SABS',
    'W-NR',
    'W-NR (DIN)',
]

CSV_STANDARD_MAP = {
    'Bohler': ('Bohler', 'Австрия'),
    'Uddeholm': ('Uddeholm', 'Швеция'),
    'Buderus': ('Buderus', 'Германия'),
    'EN': ('W-Nr (DIN)', 'Германия'),
    'AISI': ('AISI', 'США'),
    'UNS': ('UNS', 'США'),
}


def clean_text(value):
    if value is None:
        return ''
    text = str(value)
    text = text.replace('\xa0', ' ').replace('&nbsp;', ' ')
    text = ' '.join(text.split())
    return text.strip()


def strip_trademark(value):
    if not value:
        return ''
    text = clean_text(value)
    text = text.replace('\u00ae', '').replace('\u2122', '')
    text = re.sub(r'\((?:R|TM)\)', '', text, flags=re.IGNORECASE)
    return clean_text(text)

def norm_grade(value):
    if value is None:
        return ''
    text = clean_text(value)
    return text



def norm_grade_key(value):
    if value is None:
        return ''
    text = clean_text(value)
    if not text:
        return ''
    return re.sub(r'[^0-9A-Za-zА-Яа-я]+', '', text).upper()

def normalize_range(text, decimal=','):
    if not text:
        return ''
    text = text.replace(',', '.')
    text = text.replace('–', '-').replace('—', '-')
    text = re.sub(r'\s*-\s*', '-', text)
    return text


def normalize_limit_value(value, decimal=','):
    if value is None:
        return ''
    text = clean_text(value)
    if not text or text in ['-', "—"]:
        return ''
    if '?' in text:
        return ''
    text = text.replace('≤', '<=')
    text = text.replace('≥', '>=')
    text_lower = text.lower()

    nums = re.findall(r'\d+(?:[.,]\d+)?', text)
    if not nums:
        return ''
    nums = [n.replace(',', '.') for n in nums]

    has_max = any(x in text_lower for x in ['max', 'макс', 'не более', '<=', '<', 'до'])
    has_min = any(x in text_lower for x in ['min', 'мин', '>=', '>'])

    if has_max and has_min and len(nums) >= 2:
        low = nums[0]
        high = nums[1]
        out = f"{low}-{high}"
        return normalize_range(out, decimal=decimal)
    if has_max and nums:
        out = f"0-{nums[0]}"
        return normalize_range(out, decimal=decimal)

    if len(nums) >= 2 and ('-' in text or '–' in text or '—' in text):
        out = f"{nums[0]}-{nums[1]}"
        return normalize_range(out, decimal=decimal)
    if len(nums) == 1:
        out = nums[0]
        return normalize_range(out, decimal=decimal)
    if len(nums) >= 2:
        out = f"{nums[0]}-{nums[1]}"
        return normalize_range(out, decimal=decimal)

    return ''

def clean_other(value):
    if not value:
        return ''
    text = clean_text(value)
    text = re.sub(r'(?i)остальное\s*Fe', '', text)
    text = re.sub(r'(?i)остальное', '', text)
    text = text.strip(' ,;.')
    return text


def normalize_gost_standard(value):
    text = clean_text(value)
    if not text:
        return ''
    if 'GOST' in text.upper() or 'ГОСТ' in text.upper():
        text = re.sub(r'(?i)GOST', 'ГОСТ', text)
        if 'Россия' not in text:
            if ',' in text:
                text = text + ' Россия'
            else:
                text = text + ', Россия'
    return text

def split_analogues(value):
    if not value:
        return []
    parts = re.split(r'[\s|,;/]+', value)
    cleaned = []
    for part in parts:
        part = clean_text(part)
        if part and part not in ('/', '-'):
            cleaned.append(part)
    return cleaned



def extract_standard_prefix_from_title(title, grade):
    if not title or not grade:
        return None
    title_clean = clean_text(title)
    grade_clean = clean_text(grade)
    idx = title_clean.lower().find(grade_clean.lower())
    if idx == -1:
        return None
    prefix_part = title_clean[:idx].strip()
    if not prefix_part:
        return None
    prefix_part_upper = re.sub(r'\s+', ' ', prefix_part.upper()).strip()
    for prefix in sorted(STANDARD_PREFIXES, key=len, reverse=True):
        if prefix_part_upper.endswith(prefix.upper()):
            return prefix
    return None


def extract_maker_from_title(title, grade):
    if not title or not grade:
        return None
    title_clean = clean_text(title)
    grade_clean = clean_text(grade)
    idx = title_clean.lower().find(grade_clean.lower())
    if idx == -1:
        return None
    maker = title_clean[:idx].strip().rstrip(' -:')
    if not maker:
        return None
    maker_lower = maker.lower().strip()
    if maker_lower in ('knife', 'steel', 'knife steel'):
        return None
    if maker_lower.endswith('knife steel') and len(maker_lower.split()) <= 3:
        return None
    for prefix in STANDARD_PREFIXES:
        if maker.upper() == prefix.upper():
            return None
    return maker


def load_db_maps():
    if not DB_PATH.exists():
        return {}, {}, {}, {}
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute('SELECT grade, standard, manufacturer, link, analogues FROM steel_grades')
    db_by_grade = {}
    db_by_grade_link = {}
    db_by_key = {}
    analogues_raw = defaultdict(list)
    for grade, standard, manufacturer, link, analogues in cur.fetchall():
        g = norm_grade(grade)
        if not g:
            continue
        db_by_grade[g] = {
            'standard': standard or '',
            'manufacturer': manufacturer or '',
            'link': link or '',
        }
        db_by_grade_link[(g, link or '')] = {
            'standard': standard or '',
            'manufacturer': manufacturer or '',
            'link': link or '',
        }
        key = norm_grade_key(g)
        if key:
            if key not in db_by_key or (not db_by_key[key].get('link') and link):
                db_by_key[key] = {'grade': g, 'link': link or ''}
            if analogues:
                analogues_raw[key].append(analogues)
    conn.close()

    db_analogues_by_key = {}
    for key, raw_list in analogues_raw.items():
        combined = []
        for raw in raw_list:
            combined.extend(split_analogues(raw))
        canonical = []
        for ana in combined:
            ana_key = norm_grade_key(ana)
            if ana_key in db_by_key:
                canonical.append(db_by_key[ana_key]['grade'])
        db_analogues_by_key[key] = list(dict.fromkeys(canonical))
    return db_by_grade, db_by_grade_link, db_by_key, db_analogues_by_key

def load_corporate_overrides():
    overrides = {}
    candidates = [
        OUTPUT_DIR / 'corporate_marks_review.xlsx',
        OUTPUT_DIR / 'corporate_marks_review.csv',
    ]
    for path in candidates:
        if not path.exists():
            continue
        if path.suffix.lower() == '.xlsx':
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path, sep=';')
        for _, row in df.iterrows():
            grade = norm_grade(row.get('grade'))
            if not grade:
                continue
            manufacturer = clean_text(row.get('manufacturer') or row.get('manufacturer_expected') or '')
            country = clean_text(row.get('country') or row.get('country_expected') or '')
            standard = clean_text(row.get('standard') or row.get('standard_expected') or '')
            if not (manufacturer or country or standard):
                continue
            overrides[grade] = {
                'manufacturer': manufacturer,
                'country': country,
                'standard': standard,
            }
    return overrides


def parse_splav():
    records = {}
    if not SPLAV_PATH.exists():
        return records
    with SPLAV_PATH.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            grade_raw = row.get('grade')
            grade = norm_grade(grade_raw)
            if not grade:
                continue
            rec = {
                'grade_raw': grade_raw,
                'grade_norm': grade,
                'primary_source': 'splav',
                'sources': 'splav',
                'link': clean_text(row.get('link')),
                'standard_expected': normalize_gost_standard(row.get('standard')),
                'manufacturer_expected': clean_text(row.get('manufacturer')),
                'country_expected': '',
                'standard_expected_source': 'splav_csv',
                'analogues': clean_text(row.get('analogues')),
                'cc': '',
                'country_cc': '',
                'country_card': '',
                'maker_card': '',
                'maker_table': '',
                'standard_db': '',
                'manufacturer_db': '',
                'check_only': '',
            }

            standard_text = rec['standard_expected']
            if standard_text:
                parts = [p.strip() for p in standard_text.split(',') if p.strip()]
                if len(parts) >= 2:
                    rec['country_expected'] = parts[-1]
                elif 'ГОСТ' in standard_text:
                    rec['country_expected'] = 'Россия'

            for key in COMPOSITION_KEYS:
                rec[key] = normalize_limit_value(row.get(key), decimal='.')

            other = clean_other(row.get('other') or row.get('tech'))
            rec['other'] = other
            rec['tech'] = ''

            records[grade] = rec
    return records

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


def parse_zknives():
    records = {}
    if not ZKNIVES_HTML.exists():
        return records

    page_info = {}
    if ZKNIVES_PAGE_INFO.exists():
        with ZKNIVES_PAGE_INFO.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                link = clean_text(row.get('link'))
                if not link:
                    continue
                page_info[link] = {
                    'maker': clean_text(row.get('maker')),
                    'country': clean_text(row.get('country')),
                    'cc': clean_text(row.get('cc')).upper(),
                    'title': clean_text(row.get('title')),
                }

    html = ZKNIVES_HTML.read_text(encoding='iso-8859-1', errors='replace')
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

    for entry in parser.entries:
        anchors = entry.get('anchors') or []
        if not anchors:
            continue
        cells = entry.get('cells') or []
        row_data = {}
        for col_idx, key in index_map.items():
            value = cells[col_idx] if col_idx < len(cells) else ''
            row_data[key] = clean_text(value)

        cc_table = (row_data.get('cc') or '').upper()
        country_cc = CC_COUNTRY_MAP.get(cc_table, '')
        anchor_names = [clean_text(a.get('text')) for a in anchors if clean_text(a.get('text'))]

        for a in anchors:
            grade_raw = clean_text(a.get('text'))
            if not grade_raw:
                continue
            grade = norm_grade(grade_raw)
            href = clean_text(a.get('href'))
            link = href
            if link and not link.startswith('http'):
                link = f"https://zknives.com/knives/steels/{link.lstrip('/')}"

            analogues_list = [g for g in anchor_names if g and g != grade_raw]
            analogues_str = '|'.join(analogues_list)

            card = page_info.get(link, {}) if link else {}
            maker_card = card.get('maker', '')
            country_card = card.get('country', '')
            cc_card = card.get('cc', '')
            title = card.get('title', '')

            maker = maker_card or extract_maker_from_title(title, grade_raw) or ''
            country = country_card or CC_COUNTRY_MAP.get(cc_card, '') or country_cc

            standard = ''
            standard_source = ''

            if maker:
                if country:
                    standard = f"{maker}, {country}"
                else:
                    standard = maker
                standard_source = 'maker_card' if maker_card else 'title_maker'
            else:
                prefix = COUNTRY_STANDARD_DEFAULT.get(country) if country else ''
                if prefix and country:
                    standard = f"{prefix}, {country}"
                    standard_source = 'country_default'

            rec = {
                'grade_raw': grade_raw,
                'grade_norm': grade,
                'primary_source': 'zknives',
                'sources': 'zknives',
                'link': link,
                'standard_expected': standard,
                'manufacturer_expected': maker,
                'country_expected': country,
                'standard_expected_source': standard_source,
                'analogues': analogues_str,
                'cc': cc_table or cc_card,
                'country_cc': country_cc,
                'country_card': country_card,
                'maker_card': maker_card,
                'maker_table': row_data.get('maker_table') or '',
                'standard_db': '',
                'manufacturer_db': '',
                'check_only': '',
            }
            for key in COMPOSITION_KEYS:
                rec[key] = normalize_limit_value(row_data.get(key), decimal='.')
            rec['other'] = ''
            rec['tech'] = ''

            records[grade] = rec

    return records


def split_cell_values(value):
    if not value:
        return []
    parts = re.split(r'[\n\r\*]+|\s*/\s*', value)
    cleaned = []
    for part in parts:
        part = clean_text(part)
        if part and part not in ('/', '-'):
            cleaned.append(part)
    return cleaned


def segment_no_space(text, known_no_space):
    s = text.replace(' ', '')
    if not s:
        return None
    n = len(s)
    best = [None] * (n + 1)
    best[0] = []
    for i in range(n):
        if best[i] is None:
            continue
        for j in range(i + 1, n + 1):
            piece = s[i:j]
            if piece in known_no_space:
                candidate = best[i] + [known_no_space[piece]]
                if best[j] is None or len(candidate) < len(best[j]):
                    best[j] = candidate
    return best[n]


def split_uns_concat(token):
    if not token:
        return None
    match = re.match(r'^([A-Z]\\d{5})(\\d{2,4})$', token)
    if match:
        return [match.group(1), match.group(2)]
    return None


def parse_marki(known_grades, known_no_space):
    records = {}
    ambiguous = []
    if not MARKI_PATH.exists():
        return records, ambiguous

    with MARKI_PATH.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            grade_field = row.get('Grade')
            if not grade_field:
                continue
            raw_parts = split_cell_values(grade_field)
            if not raw_parts:
                continue

            maker = clean_text(row.get('Maker'))
            cc = clean_text(row.get('CC')).upper()
            country = CC_COUNTRY_MAP.get(cc, '') if cc else ''
            standard = f"{maker}, {country}" if maker and country else ''

            comp = {k.lower(): row.get(k.upper()) for k in ['C', 'Cr', 'Mo', 'V', 'W', 'Co', 'Ni', 'Mn', 'Si', 'S', 'P', 'Cu', 'Nb', 'N']}

            expanded = []
            for part in raw_parts:
                part = strip_trademark(part)
                if not part:
                    continue
                part_norm = norm_grade(part)
                if part_norm in known_grades:
                    expanded.append(part_norm)
                    continue

                tokens = part_norm.split()
                if len(tokens) > 1 and all(t in known_grades for t in tokens):
                    expanded.extend(tokens)
                    continue

                seg = segment_no_space(part_norm, known_no_space)
                if seg:
                    expanded.extend(seg)
                    continue

                uns_split = split_uns_concat(part_norm)
                if uns_split:
                    expanded.extend(uns_split)
                    continue

                expanded.append(part_norm)
                ambiguous.append(part_norm)

            all_grades = list(dict.fromkeys(expanded))
            for grade in all_grades:
                if not grade:
                    continue
                analogues = [g for g in all_grades if g != grade]
                rec = {
                    'grade_raw': grade,
                    'grade_norm': grade,
                    'primary_source': 'marki',
                    'sources': 'marki',
                    'link': '',
                    'standard_expected': standard,
                    'manufacturer_expected': maker,
                    'country_expected': country,
                    'standard_expected_source': 'marki',
                    'analogues': '|'.join(analogues),
                    'cc': cc,
                    'country_cc': country,
                    'country_card': '',
                    'maker_card': '',
                    'maker_table': '',
                    'standard_db': '',
                    'manufacturer_db': '',
                    'check_only': '1',
                }
                for key in COMPOSITION_KEYS:
                    rec[key] = normalize_limit_value(comp.get(key), decimal=',')
                rec['other'] = ''
                rec['tech'] = ''
                records[grade] = rec

    return records, ambiguous

def parse_csv_sources(corporate_overrides=None, db_by_key=None, db_analogues_by_key=None):
    records = {}
    corporate_review = []
    corporate_overrides = corporate_overrides or {}
    db_by_key = db_by_key or {}
    db_analogues_by_key = db_analogues_by_key or {}

    for file_name in CSV_FILES:
        path = Path(file_name)
        if not path.exists():
            continue

        with path.open('r', encoding='utf-8-sig') as f:
            if file_name == 'Марки ВЭМ.csv':
                next(f, None)
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                grades_by_std = defaultdict(list)

                if file_name == 'Марки ВЭМ.csv':
                    for key in ['Bohler', 'Uddeholm', 'Buderus', 'EN']:
                        val = row.get(key)
                        if val and val.strip():
                            val = val.strip().replace('~', '').strip()
                            for part in split_cell_values(val):
                                grades_by_std[key].append(part)
                elif file_name in ['Аустенитные стали.csv', 'Мартенситные.csv', 'Ферритные стали.csv']:
                    first_label = 'Марка AISI и брендовые' if file_name != 'Ферритные стали.csv' else 'Марки AISI и брендовые'
                    first = row.get(first_label) or ''
                    if first and first.strip() and first.strip() not in ['Аустенитные', 'Мартенситные', 'Ферритные']:
                        for part in split_cell_values(first.strip()):
                            grades_by_std['AISI'].append(part)
                    if row.get('UNS') and row['UNS'].strip():
                        for part in split_cell_values(row['UNS'].strip()):
                            grades_by_std['UNS'].append(part)
                    if row.get('EN') and row['EN'].strip() and row['EN'].strip() not in ['-', '-']:
                        for part in split_cell_values(row['EN'].strip()):
                            grades_by_std['EN'].append(part)
                elif file_name == 'Дуплексные стали.csv':
                    first = row.get('Марка AISI брендовые') or row.get('Марка AISI и брендовые') or ''
                    if first and first.strip():
                        for part in split_cell_values(first.strip()):
                            grades_by_std['AISI'].append(part)
                    if row.get('UNS') and row['UNS'].strip():
                        for part in split_cell_values(row['UNS'].strip()):
                            grades_by_std['UNS'].append(part)
                    if row.get('EN') and row['EN'].strip() and row['EN'].strip() not in ['-', '-']:
                        for part in split_cell_values(row['EN'].strip()):
                            grades_by_std['EN'].append(part)
                elif file_name == 'Спец сплавы.csv':
                    for key in ['Сплавы', 'UNS', 'EN']:
                        val = row.get(key)
                        if val and val.strip() and val.strip() not in ['-', '-']:
                            for part in split_cell_values(val.strip()):
                                grades_by_std[key].append(part)

                if not grades_by_std:
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
                }

                other_parts = []
                if file_name in ['Аустенитные стали.csv', 'Мартенситные.csv']:
                    other_parts.append(row.get('Прочие элементы'))
                if file_name == 'Ферритные стали.csv':
                    other_parts.append(row.get('Other Elements (прочие элементы)'))
                if file_name == 'Дуплексные стали.csv':
                    other_parts.append(row.get('Другие'))
                if file_name == 'Спец сплавы.csv':
                    for key in ['Fe', 'Al', 'Ti']:
                        val = row.get(key)
                        if val and val.strip() and val.strip() not in ['-', '-']:
                            other_parts.append(f"{key} {val.strip()}")
                    other_parts.append(row.get('Прочие элементы'))

                other = '; '.join([clean_text(p) for p in other_parts if clean_text(p)])

                all_grades = []
                for std_key, grade_list in grades_by_std.items():
                    for grade in grade_list:
                        grade_clean = strip_trademark(grade)
                        grade_clean = norm_grade(grade_clean)
                        if grade_clean:
                            all_grades.append((std_key, grade_clean, grade))

                unique_grades = [g for _, g, _ in all_grades]
                for std_key, grade_clean, grade_raw in all_grades:
                    grade_key = norm_grade_key(grade_clean)
                    grade_canonical = db_by_key.get(grade_key, {}).get('grade', grade_clean)
                    analogues_set = set()
                    for g in unique_grades:
                        if g == grade_clean:
                            continue
                        g_key = norm_grade_key(g)
                        g_canonical = db_by_key.get(g_key, {}).get('grade', g)
                        if g_canonical and g_canonical != grade_canonical:
                            analogues_set.add(g_canonical)
                    for g in list(analogues_set):
                        g_key = norm_grade_key(g)
                        for ana in db_analogues_by_key.get(g_key, []):
                            if ana and ana != grade_canonical:
                                analogues_set.add(ana)
                    analogues = sorted(analogues_set)

                    prefix, country = CSV_STANDARD_MAP.get(std_key, ('', ''))
                    if std_key == 'Сплавы':
                        prefix, country = ('', '')

                    standard = f"{prefix}, {country}" if prefix and country else ''
                    manufacturer = ''
                    if std_key in ['Bohler', 'Uddeholm', 'Buderus']:
                        manufacturer = prefix
                    standard_source = 'csv'

                    override = corporate_overrides.get(grade_clean)
                    if override:
                        manufacturer = override.get('manufacturer') or manufacturer
                        country = override.get('country') or country
                        if override.get('standard'):
                            standard = override.get('standard')
                        elif manufacturer and country:
                            standard = f"{manufacturer}, {country}"
                        standard_source = 'corporate_override'

                    rec = {
                        'grade_raw': grade_clean,
                        'grade_norm': grade_clean,
                        'primary_source': 'csv',
                        'sources': f"csv:{file_name}",
                        'link': '',
                        'standard_expected': standard,
                        'manufacturer_expected': manufacturer,
                        'country_expected': country,
                        'standard_expected_source': standard_source,
                        'analogues': '|'.join(analogues),
                        'cc': '',
                        'country_cc': '',
                        'country_card': '',
                        'maker_card': '',
                        'maker_table': '',
                        'standard_db': '',
                        'manufacturer_db': '',
                        'check_only': '',
                    }

                    for key in COMPOSITION_KEYS:
                        rec[key] = normalize_limit_value(comp.get(key), decimal=',')

                    rec['other'] = clean_other(other)
                    rec['tech'] = ''

                    if not standard:
                        corporate_review.append({
                            'grade': grade_clean,
                            'source_file': file_name,
                            'reason': 'missing_standard',
                            'original_grade': grade_raw,
                            'manufacturer': manufacturer,
                            'country': country,
                            'standard_expected': standard,
                        })

                    if re.search(r'[®™]|\((?:R|TM)\)', str(grade_raw), re.IGNORECASE):
                        corporate_review.append({
                            'grade': grade_clean,
                            'source_file': file_name,
                            'reason': 'trademark',
                            'original_grade': grade_raw,
                            'manufacturer': manufacturer,
                            'country': country,
                            'standard_expected': standard,
                        })

                    records[grade_clean] = rec

    return records, corporate_review


def build_master():
    db_by_grade, _, db_by_key, db_analogues_by_key = load_db_maps()

    splav_records = parse_splav()
    zknives_records = parse_zknives()
    corporate_overrides = load_corporate_overrides()

    splav_set = set(splav_records.keys())
    zknives_set = set(zknives_records.keys())
    splav_keys = {norm_grade_key(g) for g in splav_set}
    zknives_keys = {norm_grade_key(g) for g in zknives_set}


    csv_records, corporate_review = parse_csv_sources(corporate_overrides, db_by_key, db_analogues_by_key)
    csv_records = {g: r for g, r in csv_records.items() if norm_grade_key(g) not in splav_keys and norm_grade_key(g) not in zknives_keys}

    known_grades = set(splav_set) | set(zknives_set) | set(csv_records.keys())
    known_no_space = {g.replace(' ', ''): g for g in known_grades}

    marki_records, ambiguous_marki = parse_marki(known_grades, known_no_space)
    marki_records = {g: r for g, r in marki_records.items() if g not in known_grades}

    source_map = defaultdict(set)
    for g in splav_records:
        source_map[g].add('splav')
    for g in zknives_records:
        source_map[g].add('zknives')
    for g in csv_records:
        source_map[g].add('csv')
    for g in marki_records:
        source_map[g].add('marki')

    master = {}
    for grade in source_map:
        if grade in splav_records:
            rec = splav_records[grade].copy()
        elif grade in zknives_records:
            rec = zknives_records[grade].copy()
        elif grade in csv_records:
            rec = csv_records[grade].copy()
        else:
            rec = marki_records[grade].copy()
        rec['sources'] = '|'.join(sorted(source_map[grade]))

        db_rec = db_by_grade.get(grade)
        if db_rec:
            rec['standard_db'] = db_rec.get('standard', '')
            rec['manufacturer_db'] = db_rec.get('manufacturer', '')
        else:
            rec['standard_db'] = ''
            rec['manufacturer_db'] = ''

        if rec['primary_source'] == 'csv' and rec.get('standard_expected') == 'EN, Европа':
            rec['standard_expected'] = 'W-Nr (DIN), Германия'
            rec['country_expected'] = 'Германия'

        analogues_raw = rec.get('analogues') or ''
        if rec['primary_source'] == 'splav':
            analogues_list = [a for a in analogues_raw.split() if a]
        else:
            analogues_list = [a for a in analogues_raw.split('|') if a]

        master_set = set(source_map.keys())
        present = 0
        missing = []
        for a in analogues_list:
            gnorm = norm_grade(a)
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
        rec['composition_has_range'] = '1' if any(re.search(r'\d\s*-\s*\d', str(v)) for v in values if v) else '0'
        rec['composition_has_qualifier'] = '1' if any(re.search(r'(?:до|макс|max|min|<=|>=|<|>)', str(v), re.IGNORECASE) for v in values if v) else '0'
        rec['composition_has_comma'] = '1' if any(',' in str(v) for v in values if v) else '0'

        master[grade] = rec

    rows = []
    for grade, rec in master.items():
        row = {
            'grade_norm': rec.get('grade_norm') or grade,
            'grade_raw': rec.get('grade_raw') or grade,
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
        row['other'] = rec.get('other') or ''
        row['tech'] = rec.get('tech') or ''
        rows.append(row)

    df = pd.DataFrame(rows)

    ordered_cols = [
        'grade_norm', 'grade_raw', 'primary_source', 'sources', 'link',
        'standard_expected', 'manufacturer_expected', 'country_expected',
        'standard_db', 'manufacturer_db', 'cc', 'country_cc', 'country_card',
        'maker_card', 'maker_table', 'standard_expected_source', 'analogues',
        'analogues_count', 'analogues_present_count', 'analogues_missing_count',
        'analogues_missing_examples', 'composition_any', 'composition_all_empty',
        'composition_has_range', 'composition_has_qualifier', 'composition_has_comma', 'check_only',
    ] + COMPOSITION_KEYS + ['other', 'tech']

    df = df.reindex(columns=ordered_cols)

    out_xlsx = OUTPUT_DIR / 'master_grades_review_fixed.xlsx'
    try:
        df.to_excel(out_xlsx, index=False)
    except PermissionError:
        out_xlsx = OUTPUT_DIR / 'master_grades_review_fixed_v2.xlsx'
        df.to_excel(out_xlsx, index=False)


    out_csv = OUTPUT_DIR / 'master_grades_review_fixed.csv'
    df.to_csv(out_csv, sep=';', index=False)

    if corporate_review:
        corp_df = pd.DataFrame(corporate_review).drop_duplicates()
        corp_df.to_excel(OUTPUT_DIR / 'corporate_marks_review.xlsx', index=False)
        corp_df.to_csv(OUTPUT_DIR / 'corporate_marks_review.csv', sep=';', index=False)

    if ambiguous_marki:
        amb_df = pd.DataFrame(sorted(set(ambiguous_marki)), columns=['grade'])
        amb_df.to_excel(OUTPUT_DIR / 'marki_split_ambiguous.xlsx', index=False)
        amb_df.to_csv(OUTPUT_DIR / 'marki_split_ambiguous.csv', sep=';', index=False)

    print(f'[OK] {out_xlsx.name} written')


if __name__ == '__main__':
    build_master()
