import argparse
import codecs
import csv
import re
import sqlite3
import time
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


METAL_BASE = "https://metallicheckiy-portal.ru"
METAL_ROOT = f"{METAL_BASE}/marki_metallov"

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

SKIP_CATEGORY_SLUGS = {
    "search",
    "rss_marki.xml",
}


def clean_text(value):
    if value is None:
        return ""
    text = value.replace("\xa0", " ").replace("*", "").strip()
    return " ".join(text.split())


def strip_tags(value):
    return re.sub(r"<[^>]+>", " ", value)


def normalize_element(value):
    value = clean_text(strip_tags(unescape(value or ""))).upper().strip()
    return value.replace(" ", "")


def normalize_value(value):
    value = clean_text(strip_tags(unescape(value or "")))
    if not value:
        return None
    value = value.replace(",", ".")
    value = value.replace("?", "").replace(">=", "").replace("<=", "")
    value = value.replace("\u2264", "").replace("\u2265", "")
    value = re.sub(r"(?i)\b(до|неболее|не\s*более|неменее|не\s*менее)\b", "", value)
    value = value.replace("~", "")
    value = re.sub(r"\s+", "", value)
    value = value.strip(";-")
    return value or None


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_anchor = False
        self.current_href = None
        self.current_text = []
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self.in_anchor = True
            self.current_href = href
            self.current_text = []

    def handle_endtag(self, tag):
        if tag != "a" or not self.in_anchor:
            return
        text = clean_text("".join(self.current_text))
        self.anchors.append((self.current_href, text))
        self.in_anchor = False
        self.current_href = None
        self.current_text = []

    def handle_data(self, data):
        if self.in_anchor:
            self.current_text.append(data)


def detect_encoding(raw, header_charset=None):
    if header_charset:
        try:
            codecs.lookup(header_charset)
            return header_charset
        except LookupError:
            pass
    head = raw[:2048].decode("ascii", errors="ignore")
    match = re.search(r"charset=([\\w-]+)", head, re.I)
    if match:
        candidate = match.group(1).strip()
        try:
            codecs.lookup(candidate)
            return candidate
        except LookupError:
            pass
    utf8_text = raw.decode("utf-8", errors="replace")
    if utf8_text.count("\ufffd") < 5:
        return "utf-8"
    return "cp1251"


def fetch(url, cache_path, refresh=False, delay=0.0):
    raw = None
    charset = None
    if cache_path.exists() and not refresh:
        raw = cache_path.read_bytes()
    else:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        for attempt in range(3):
            try:
                with urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    charset = resp.headers.get_content_charset()
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
    if raw is None:
        return None
    encoding = detect_encoding(raw, charset)
    return raw.decode(encoding, errors="replace")


def normalize_href(href):
    href = href.strip()
    if href.startswith("//"):
        return f"https:{href}"
    if href.startswith("/"):
        return f"{METAL_BASE}{href}"
    return href


def parse_anchors(html):
    parser = AnchorParser()
    parser.feed(html)
    return parser.anchors


def collect_categories(report_dir, refresh=False, delay=0.0, verbose=False):
    url = METAL_ROOT
    html = fetch(url, report_dir / "metal_cache" / "index.html", refresh=refresh, delay=delay)
    if not html:
        raise RuntimeError("Failed to load metallicheckiy main page")
    categories = set()
    for href, _ in parse_anchors(html):
        if not href:
            continue
        href = normalize_href(href)
        match = re.search(r"/marki_metallov/([^/?#]+)", href)
        if not match:
            continue
        slug = match.group(1)
        if slug in SKIP_CATEGORY_SLUGS:
            continue
        if "." in slug:
            continue
        categories.add(slug)
    if verbose:
        print(f"[DEBUG] categories: {sorted(categories)}")
    return sorted(categories)


def collect_grades(category, report_dir, refresh=False, delay=0.0, verbose=False):
    url = f"{METAL_ROOT}/{category}"
    html = fetch(
        url,
        report_dir / "metal_cache" / f"category_{category}.html",
        refresh=refresh,
        delay=delay,
    )
    if not html:
        return {}
    grades = {}
    for href, text in parse_anchors(html):
        if not href:
            continue
        href = normalize_href(href)
        match = re.search(rf"/marki_metallov/{re.escape(category)}/([^/?#]+)", href)
        if not match:
            continue
        slug = match.group(1)
        if slug.lower() in ("pred", "offer"):
            continue
        grade = clean_text(unescape(text))
        if not grade:
            grade = slug
        if grade not in grades:
            grades[grade] = f"{METAL_ROOT}/{category}/{slug}"
    if verbose:
        print(f"[DEBUG] {category}: {len(grades)} grades")
    return grades


def parse_composition(html):
    elements = re.findall(r"class=\"marochn_m_xs_lev\"[^>]*>\\s*(?:<strong>)?([^<]+)", html, re.I)
    values = re.findall(r"class=\"marochn_m_xs_pro\"[^>]*>\\s*([^<]+)", html, re.I)
    composition = {}
    for element, value in zip(elements, values):
        key = ELEMENT_MAP.get(normalize_element(element))
        if not key:
            continue
        normalized = normalize_value(value)
        if normalized:
            composition[key] = normalized
    return composition


def parse_analogs(html):
    analog_cells = re.findall(r"class=\"marochn_m_anal_dan\"[^>]*>(.*?)</td>", html, re.I | re.S)
    tokens = []
    for cell in analog_cells:
        text = clean_text(strip_tags(unescape(cell)))
        if not text:
            continue
        parts = re.split(r"[\\s,;]+", text)
        for part in parts:
            part = part.strip()
            if len(part) < 2:
                continue
            tokens.append(part)
    seen = set()
    analogs = []
    for token in tokens:
        key = token.upper()
        if key in seen:
            continue
        seen.add(key)
        analogs.append(token)
    return analogs


def cache_name_from_url(url):
    match = re.search(r"/marki_metallov/[^/]+/([^/?#]+)", url)
    if match:
        return match.group(1)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", url)
    return safe[:120]


def build_records(grades, report_dir, refresh=False, delay=0.0, limit=None):
    records = []
    items = list(grades.items())
    if limit:
        items = items[:limit]
    total = len(items)

    for index, (grade, url) in enumerate(items, 1):
        cache_name = cache_name_from_url(url)
        html = fetch(
            url,
            report_dir / "metal_cache" / "grade" / f"{cache_name}.html",
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
        report_dir / "metallicheckiy_db_updates.csv",
        updates,
        ["grade", "updated_fields"],
    )
    write_csv(
        report_dir / "metallicheckiy_missing_in_db.csv",
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
        report_dir / "metallicheckiy_mismatches.csv",
        mismatches,
        ["grade", "field", "db_value", "source_value"],
    )

    return len(missing), len(mismatches), len(updates)


def main():
    parser = argparse.ArgumentParser(description="Parse metallicheckiy-portal steel grades and sync with DB.")
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

    categories = collect_categories(report_dir, refresh=args.refresh, delay=args.delay, verbose=args.verbose)
    print(f"[INFO] Categories discovered: {len(categories)}")

    grades = {}
    for category in categories:
        grades.update(
            collect_grades(
                category,
                report_dir,
                refresh=args.refresh,
                delay=args.delay,
                verbose=args.verbose,
            )
        )
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
    output_csv = report_dir / "metallicheckiy_ru_grades.csv"
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
