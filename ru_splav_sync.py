import argparse
import csv
import re
import sqlite3
import time
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SPLAV_BASE = "http://www.splav-kharkov.com"

COMPOSITION_MARKER = "\u0425\u0438\u043c\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u0441\u043e\u0441\u0442\u0430\u0432"
ANALOGS_MARKER = "\u0417\u0430\u0440\u0443\u0431\u0435\u0436\u043d\u044b\u0435 \u0430\u043d\u0430\u043b\u043e\u0433\u0438"
ANALOGS_SECTION_RE = re.compile(r"\u0417\u0430\u0440\u0443\u0431\u0435\u0436\u043d\u044b\u0435\s+\u0430\u043d\u0430\u043b\u043e\u0433\u0438\s+\u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u0430", re.I)
ANALOGS_END_MARKER = "\u041e\u0431\u043e\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f"
TABLE_OPEN_RE = re.compile(r"<table[^>]*>", re.I)
TABLE_CLOSE_RE = re.compile(r"</table>", re.I)

ELEMENT_MAP = {
    "C": "c",
    "CR": "cr",
    "MO": "mo",
    "V": "v",
    "W": "w",
    "CO": "co",
    "NI": "ni",
    "MN": "mn",
    "SI": "si",
    "S": "s",
    "P": "p",
    "CU": "cu",
    "NB": "nb",
    "N": "n",
}

SKIP_ANALOG_TOKENS = {
    "DIN",
    "WNR",
    "JIS",
    "BS",
    "EN",
    "UNI",
    "UNE",
    "BDS",
    "MSZ",
    "PN",
    "STAS",
    "CSN",
    "ONORM",
    "AS",
    "ISO",
}


def contains_cyrillic(text):
    return any(0x0400 <= ord(ch) <= 0x04FF for ch in text)


def clean_text(value):
    if value is None:
        return ""
    text = value.replace("\xa0", " ").replace("*", "").strip()
    return " ".join(text.split())


def strip_tags(value):
    return re.sub(r"<[^>]+>", " ", value)


def normalize_element(value):
    value = clean_text(value).upper().strip()
    return value.replace(" ", "")


def normalize_value(value):
    value = clean_text(strip_tags(value))
    if not value:
        return None
    value = value.replace(",", ".")
    value = value.replace("≤", "").replace(">=", "").replace("<=", "")
    value = re.sub(r"(?i)\\b(\\u0434\\u043e|\\u043d\\u0435\\u0431\\u043e\\u043b\\u0435\\u0435|\\u043d\\u0435\\u043c\\u0435\\u043d\\u0435\\u0435)\\b", "", value)
    value = value.replace("~", "")
    value = re.sub(r"\\s+", "", value)
    value = value.strip(";-")
    return value or None


class SplavTypeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_anchor = False
        self.in_bold = False
        self.current_href = None
        self.current_text = []
        self.entries = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href", "")
        if "mat_start.php?name_id=" in href:
            self.in_anchor = True
            self.current_href = href
            self.current_text = []

    def handle_endtag(self, tag):
        if tag == "b" and self.in_bold:
            self.in_bold = False
        if tag == "a" and self.in_anchor:
            text = clean_text("".join(self.current_text))
            if text and self.current_href:
                self.entries.append((self.current_href, text))
            self.in_anchor = False
            self.current_href = None
            self.current_text = []

    def handle_data(self, data):
        if self.in_anchor:
            self.current_text.append(data)


def fetch(url, cache_path, encoding, refresh=False, delay=0.0):
    if cache_path.exists() and not refresh:
        raw = cache_path.read_bytes()
    else:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = None
        for attempt in range(3):
            try:
                with urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                break
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                if attempt == 2:
                    print(f"[WARN] Fetch failed: {url} ({exc})")
                    return None
                time.sleep(1)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(raw)
        if delay:
            time.sleep(delay)
    return raw.decode(encoding, errors="replace")


def parse_type_page(html):
    parser = SplavTypeParser()
    parser.feed(html)
    return parser.entries


def extract_tables(html):
    return re.findall(r"<table[^>]*>.*?</table>", html, re.I | re.S)


def extract_table_after(html, start_index):
    open_match = TABLE_OPEN_RE.search(html, start_index)
    if not open_match:
        return None
    pos = open_match.end()
    depth = 1
    while depth > 0:
        next_open = TABLE_OPEN_RE.search(html, pos)
        next_close = TABLE_CLOSE_RE.search(html, pos)
        if not next_close:
            return None
        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            pos = next_close.end()
    return html[open_match.start():pos]


def parse_composition(html):
    tables = extract_tables(html)
    for table in tables:
        rows = re.findall(r"<tr[^>]*>.*?</tr>", table, re.I | re.S)
        if len(rows) < 2:
            continue
        header_cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rows[0], re.I | re.S)
        elements = [normalize_element(strip_tags(cell)) for cell in header_cells]
        if not any(element in ELEMENT_MAP for element in elements):
            continue
        value_cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rows[1], re.I | re.S)
        if not value_cells:
            continue
        composition = {}
        for element, value in zip(elements, value_cells):
            column = ELEMENT_MAP.get(element)
            if not column:
                continue
            normalized = normalize_value(value)
            if normalized:
                composition[column] = normalized
        if composition:
            return composition
    return {}


def parse_analogs(html):
    matches = list(ANALOGS_SECTION_RE.finditer(html))
    if not matches:
        return []
    match = matches[-1]
    table_html = extract_table_after(html, match.end())
    if not table_html:
        return []
    cell_texts = re.findall(r"<td[^>]*>(.*?)</td>", table_html, re.I | re.S)
    tokens = []
    for cell in cell_texts:
        text = clean_text(strip_tags(cell))
        if not text:
            continue
        parts = re.split(r"[\\s,;]+", text)
        for part in parts:
            token = part.strip()
            if token:
                tokens.append(token)
    analogs = []
    seen = set()
    for token in tokens:
        token = token.strip()
        if not token or len(token) < 2:
            continue
        upper = token.upper()
        if upper in SKIP_ANALOG_TOKENS:
            continue
        if not any(ch.isdigit() for ch in token):
            continue
        if upper not in seen:
            seen.add(upper)
            analogs.append(token)
    return analogs


def collect_splav_grades(report_dir, refresh=False, delay=0.0, verbose=False):
    main_url = f"{SPLAV_BASE}/choose_type.php"
    main_html = fetch(
        main_url,
        report_dir / "splav_cache" / "choose_type.html",
        "utf-8",
        refresh=refresh,
        delay=delay,
    )
    if not main_html:
        raise RuntimeError("Failed to load splav choose_type.php")
    type_ids = sorted(set(re.findall(r"choose_type_class\.php\?type_id=(\d+)", main_html)))
    if not type_ids:
        cached = report_dir / "splav_cache"
        type_ids = sorted(
            {
                path.stem.split("_", 1)[1]
                for path in cached.glob("type_*.html")
                if "_" in path.stem
            }
        )

    if verbose:
        print(f"[DEBUG] type_ids: {len(type_ids)}")

    grades = {}
    for type_id in type_ids:
        url = f"{SPLAV_BASE}/choose_type_class.php?type_id={type_id}"
        html = fetch(
            url,
            report_dir / "splav_cache" / f"type_{type_id}.html",
            "utf-8",
            refresh=refresh,
            delay=delay,
        )
        if not html:
            continue
        matches = list(re.finditer(r"mat_start\.php\?name_id=(\d+)[^>]*>\s*<b>([^<]+)", html, re.I))
        if verbose:
            has_marker = "mat_start.php?name_id" in html
            print(f"[DEBUG] type_id {type_id}: {len(matches)} matches (marker={has_marker})")
        for match in matches:
            name_id, grade = match.group(1), clean_text(unescape(match.group(2)))
            if not grade:
                continue
            if grade not in grades:
                grades[grade] = f"{SPLAV_BASE}/mat_start.php?name_id={name_id}"
    return grades


def build_records(grades, report_dir, refresh=False, delay=0.0, limit=None):
    records = []
    items = list(grades.items())
    if limit:
        items = items[:limit]
    total = len(items)

    for index, (grade, url) in enumerate(items, 1):
        name_id_match = re.search(r"name_id=(\d+)", url)
        cache_name = f"mat_{name_id_match.group(1)}.html" if name_id_match else f"mat_{index}.html"
        html = fetch(
            url,
            report_dir / "splav_cache" / "mat" / cache_name,
            "utf-8",
            refresh=refresh,
            delay=delay,
        )
        if not html:
            continue
        composition = parse_composition(html)
        analogs = parse_analogs(html)
        record = {
            "grade": grade,
            "analogues": " ".join(analogs) if analogs else None,
            "base": "Fe",
            "standard": f"GOST {grade}, \u0420\u043e\u0441\u0441\u0438\u044f",
            "manufacturer": None,
            "link": url,
        }
        record.update(composition)
        records.append(record)

        if index % 100 == 0:
            print(f"[INFO] Parsed {index}/{total}")
    return records


def write_csv(path, rows, header):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in header})


def load_csv(path):
    with path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [row for row in reader]


def compare_and_apply(csv_rows, db_path, report_dir, apply_changes=False):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT grade, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n, tech, standard, manufacturer, analogues, link
        FROM steel_grades
        """
    )
    db_rows = {row[0]: row for row in cur.fetchall()}

    missing = []
    mismatches = []
    updates = []

    composition_keys = ["c", "cr", "mo", "v", "w", "co", "ni", "mn", "si", "s", "p", "cu", "nb", "n"]

    def should_update_text(src, db_value):
        if not src:
            return False
        if not db_value:
            return True
        return clean_text(src) != clean_text(db_value)

    def should_update_comp(src, db_value):
        if not src:
            return False
        if not db_value:
            return True
        return normalize_value(src) != normalize_value(db_value)

    for row in csv_rows:
        grade = clean_text(row.get("grade"))
        if not grade:
            continue
        db_row = db_rows.get(grade)
        if not db_row:
            missing.append(row)
            continue

        db_fields = {
            "c": db_row[2],
            "cr": db_row[3],
            "mo": db_row[4],
            "v": db_row[5],
            "w": db_row[6],
            "co": db_row[7],
            "ni": db_row[8],
            "mn": db_row[9],
            "si": db_row[10],
            "s": db_row[11],
            "p": db_row[12],
            "cu": db_row[13],
            "nb": db_row[14],
            "n": db_row[15],
        }

        fields_to_update = {}

        for key in composition_keys:
            src_value = row.get(key)
            db_value = db_fields.get(key)
            if should_update_comp(src_value, db_value):
                fields_to_update[key] = src_value
                if db_value and normalize_value(db_value) != normalize_value(src_value):
                    mismatches.append(
                        {
                            "grade": grade,
                            "field": key,
                            "db_value": db_value,
                            "source_value": src_value,
                        }
                    )

        extra_map = {
            "base": db_row[1],
            "tech": db_row[16],
            "standard": db_row[17],
            "manufacturer": db_row[18],
            "analogues": db_row[19],
            "link": db_row[20],
        }
        for key, db_value in extra_map.items():
            src_value = row.get(key)
            if key == "analogues":
                src_clean = clean_text(src_value or "")
                db_clean = clean_text(db_value or "")
                if src_clean != db_clean:
                    fields_to_update[key] = src_value if src_value else None
                continue
            if should_update_text(src_value, db_value):
                fields_to_update[key] = src_value

        if apply_changes and fields_to_update:
            set_clause = ", ".join([f"{key} = ?" for key in fields_to_update])
            params = list(fields_to_update.values()) + [grade]
            cur.execute(f"UPDATE steel_grades SET {set_clause} WHERE grade = ?", params)
            updates.append(
                {
                    "grade": grade,
                    "updated_fields": ",".join(fields_to_update.keys()),
                }
            )

    if apply_changes:
        if missing:
            insert_sql = """
            INSERT INTO steel_grades (
                grade, analogues, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n, tech,
                standard, manufacturer, link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
            for row in missing:
                cur.execute(
                    insert_sql,
                    (
                        row.get("grade"),
                        row.get("analogues"),
                        row.get("base"),
                        row.get("c"),
                        row.get("cr"),
                        row.get("mo"),
                        row.get("v"),
                        row.get("w"),
                        row.get("co"),
                        row.get("ni"),
                        row.get("mn"),
                        row.get("si"),
                        row.get("s"),
                        row.get("p"),
                        row.get("cu"),
                        row.get("nb"),
                        row.get("n"),
                        row.get("tech"),
                        row.get("standard"),
                        row.get("manufacturer"),
                        row.get("link"),
                    ),
                )
        if updates or missing:
            conn.commit()

    conn.close()

    write_csv(
        report_dir / "splav_db_updates.csv",
        updates,
        ["grade", "updated_fields"],
    )
    write_csv(
        report_dir / "splav_missing_in_db.csv",
        missing,
        [
            "grade",
            "analogues",
            "base",
            "c",
            "cr",
            "mo",
            "v",
            "w",
            "co",
            "ni",
            "mn",
            "si",
            "s",
            "p",
            "cu",
            "nb",
            "n",
            "tech",
            "standard",
            "manufacturer",
            "link",
        ],
    )
    write_csv(
        report_dir / "splav_mismatches.csv",
        mismatches,
        ["grade", "field", "db_value", "source_value"],
    )

    return len(missing), len(mismatches), len(updates)


def main():
    parser = argparse.ArgumentParser(description="Parse splav-kharkov steel grades and sync with DB.")
    parser.add_argument("--db", default="database/steel_database.db", help="SQLite DB path")
    parser.add_argument("--report-dir", default="reports", help="Report directory")
    parser.add_argument("--refresh", action="store_true", help="Re-download cached pages")
    parser.add_argument("--apply", action="store_true", help="Insert missing grades into DB")
    parser.add_argument("--no-compare", action="store_true", help="Skip DB comparison")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay between requests (seconds)")
    parser.add_argument("--limit", type=int, help="Limit number of grades for testing")
    parser.add_argument("--verbose", action="store_true", help="Verbose debug output")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    grades = collect_splav_grades(report_dir, refresh=args.refresh, delay=args.delay, verbose=args.verbose)
    print(f"[INFO] Grades discovered: {len(grades)}")

    records = build_records(grades, report_dir, refresh=args.refresh, delay=args.delay, limit=args.limit)
    header = [
        "grade",
        "analogues",
        "base",
        "c",
        "cr",
        "mo",
        "v",
        "w",
        "co",
        "ni",
        "mn",
        "si",
        "s",
        "p",
        "cu",
        "nb",
        "n",
        "tech",
        "standard",
        "manufacturer",
        "link",
    ]
    output_csv = report_dir / "splav_ru_grades.csv"
    write_csv(output_csv, records, header)
    print(f"[INFO] CSV written: {output_csv} ({len(records)} rows)")

    if args.no_compare:
        print("[INFO] DB comparison skipped (--no-compare)")
        return

    missing, mismatches, updates = compare_and_apply(
        records,
        args.db,
        report_dir,
        apply_changes=args.apply,
    )
    print(f"[INFO] Missing in DB: {missing}")
    print(f"[INFO] Composition mismatches: {mismatches}")
    print(f"[INFO] Updated in DB: {updates}")


if __name__ == "__main__":
    main()
