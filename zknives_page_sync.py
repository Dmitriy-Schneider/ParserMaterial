import argparse
import csv
import hashlib
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from utils.fill_standards_with_ai import detect_standard_pattern, format_standard_value

ZKNIVES_BASE = "https://zknives.com/knives/steels/"

CC_COUNTRY_MAP = {
    "AT": "Австрия",
    "BE": "Бельгия",
    "BR": "Бразилия",
    "CH": "Швейцария",
    "CN": "Китай",
    "CZ": "Чехия",
    "DE": "Германия",
    "EN": "Европа",
    "ES": "Испания",
    "EU": "Европа",
    "FN": "Финляндия",
    "FR": "Франция",
    "IT": "Италия",
    "JP": "Япония",
    "LU": "Люксембург",
    "NO": "Норвегия",
    "PL": "Польша",
    "RU": "Россия",
    "SE": "Швеция",
    "SI": "Словения",
    "UA": "Украина",
    "UK": "Великобритания",
    "US": "США",
    "SW": "Швеция",
    "GR": "Греция",
}

STANDARD_PREFIXES = [
    "BS EN",
    "GB/T",
    "GOST R",
    "AISI",
    "ASTM",
    "UNS",
    "SAE",
    "GOST",
    "DIN",
    "EN",
    "ISO",
    "JIS",
    "GB",
    "BS",
    "AFNOR",
    "NF",
    "UNI",
    "SIS",
    "SS",
    "PN",
    "CSN",
    "KS",
    "AS",
    "SABS",
]


def clean_text(value):
    if value is None:
        return ""
    text = value.replace("\xa0", " ").replace("*", "").strip()
    return " ".join(text.split())


def normalize_href(href):
    if not href:
        return None
    href = href.strip()
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"{ZKNIVES_BASE}{href.lstrip('/')}"


def canonical_link(link):
    if not link:
        return ""
    link = str(link).strip()
    if not link:
        return ""
    if link.startswith("http://") or link.startswith("https://"):
        return link
    if ".shtml" in link:
        return normalize_href(link)
    return link


def normalize_prefix(value):
    return re.sub(r"\s+", " ", value.strip()).upper()


def is_standard_prefix(value):
    if not value:
        return False
    norm = normalize_prefix(value)
    for prefix in STANDARD_PREFIXES:
        if norm == normalize_prefix(prefix):
            return True
    return False


def safe_url(url):
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return url
    safe_path = quote(parts.path, safe="/:%")
    safe_query = quote(parts.query, safe="=&%")
    return urlunsplit((parts.scheme, parts.netloc, safe_path, safe_query, parts.fragment))


def fallback_url(url):
    if "pop's_procut.shtml" in url:
        return url.replace("pop's_procut.shtml", "procut.shtml")
    if "pop%27s_procut.shtml" in url:
        return url.replace("pop%27s_procut.shtml", "procut.shtml")
    return None


def make_cache_filename(link):
    parsed = urlparse(link)
    name = Path(parsed.path).name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    if not safe or safe in {".", ".."}:
        digest = hashlib.md5(link.encode("utf-8")).hexdigest()
        safe = f"page_{digest}.html"
    return safe


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.in_name_cell = False
        self.in_anchor = False
        self.cell_index = -1
        self.current_anchor = []
        self.current_href = None
        self.items = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table" and attrs_dict.get("id") == "steelData":
            self.in_table = True
        if self.in_table and tag == "tr":
            self.in_row = True
            self.cell_index = -1
        if self.in_row and tag in ("td", "th"):
            self.in_cell = True
            self.cell_index += 1
            if self.cell_index == 1:
                self.in_name_cell = True
        if self.in_name_cell and tag == "a":
            self.in_anchor = True
            self.current_anchor = []
            self.current_href = attrs_dict.get("href")

    def handle_endtag(self, tag):
        if self.in_anchor and tag == "a":
            anchor_text = clean_text("".join(self.current_anchor))
            if anchor_text:
                self.items.append(
                    {
                        "grade": anchor_text,
                        "link": canonical_link(self.current_href),
                    }
                )
            self.in_anchor = False
            self.current_href = None
        if self.in_cell and tag in ("td", "th"):
            self.in_cell = False
            if self.cell_index == 1:
                self.in_name_cell = False
        if self.in_row and tag == "tr":
            self.in_row = False
        if tag == "table" and self.in_table:
            self.in_table = False

    def handle_data(self, data):
        if self.in_anchor:
            self.current_anchor.append(data)


def load_link_grades(cache_path):
    html = cache_path.read_text(encoding="iso-8859-1", errors="replace")
    parser = LinkParser()
    parser.feed(html)
    link_grades = {}
    for item in parser.items:
        link = item["link"]
        grade = item["grade"]
        if not link or not grade:
            continue
        link_grades.setdefault(link, set()).add(grade)
    return link_grades


def strip_tags(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def parse_country(html):
    match = re.search(r"<em>\s*Country\s*</em>\s*-\s*(.*?)</p>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None, None, None
    raw = clean_text(unescape(strip_tags(match.group(1))))
    cc_match = re.search(r"\(([^()]+)\)\s*$", raw)
    cc = cc_match.group(1).strip().upper() if cc_match else None
    name = raw
    if cc_match:
        name = raw[: cc_match.start()].strip()
    country = CC_COUNTRY_MAP.get(cc) or (name or None)
    return country, cc, raw or None


def strip_title_suffix(title):
    if not title:
        return ""
    return re.split(r"\bKnife Steel", title, flags=re.IGNORECASE)[0].strip()


def extract_maker_from_title(title, grade_candidates):
    if not title or not grade_candidates:
        return None
    prefix = strip_title_suffix(title)
    if not prefix:
        return None

    title_norm = clean_text(prefix)
    lower_title = title_norm.lower()
    candidates = sorted(grade_candidates, key=len, reverse=True)
    for grade in candidates:
        grade_norm = clean_text(grade)
        if not grade_norm:
            continue
        idx = lower_title.find(grade_norm.lower())
        if idx == -1:
            continue
        maker = title_norm[:idx].strip().rstrip(" -–—:")
        if not maker:
            return None
        if is_standard_prefix(maker):
            return None
        maker_lower = maker.lower().strip()
        if maker_lower in ("knife", "steel", "knife steel"):
            return None
        if maker_lower.endswith("knife steel") and len(maker_lower.split()) <= 3:
            return None
        return maker
    return None


def extract_prefix_from_title(title, grade):
    if not title or not grade:
        return None
    title_clean = clean_text(title)
    lower_title = title_clean.lower()
    lower_grade = grade.lower()
    idx = lower_title.find(lower_grade)
    if idx == -1:
        return None
    prefix_part = title_clean[:idx].strip()
    if not prefix_part:
        return None
    prefix_part_upper = normalize_prefix(prefix_part)
    for prefix in sorted(STANDARD_PREFIXES, key=len, reverse=True):
        if prefix_part_upper.endswith(normalize_prefix(prefix)):
            return prefix
    return None


def build_standard_value(grade, maker, country, title):
    if maker and country:
        return f"{maker}, {country}"

    detection = detect_standard_pattern(grade, None, maker)

    if country:
        if detection.get("type") == "government":
            prefix = detection.get("standard_prefix")
            number = detection.get("standard_number")
            if prefix and number:
                return f"{prefix} {number}, {country}"
            if prefix:
                return f"{prefix}, {country}"
        prefix = extract_prefix_from_title(title, grade)
        if prefix:
            return f"{prefix}, {country}"

    return format_standard_value(
        detection,
        None,
        grade=grade,
        link=None,
        manufacturer=maker,
    )


def fetch_html(url, cache_path, refresh, timeout, retries, delay):
    if cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="iso-8859-1", errors="replace")

    last_err = None
    for _ in range(retries):
        try:
            req = Request(safe_url(url), headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("iso-8859-1", errors="replace")
            cache_path.write_text(html, encoding="iso-8859-1")
            return html
        except HTTPError as exc:
            if exc.code == 404:
                alt = fallback_url(url)
                if alt:
                    try:
                        req = Request(safe_url(alt), headers={"User-Agent": "Mozilla/5.0"})
                        with urlopen(req, timeout=timeout) as resp:
                            html = resp.read().decode("iso-8859-1", errors="replace")
                        cache_path.write_text(html, encoding="iso-8859-1")
                        return html
                    except Exception as alt_exc:
                        last_err = alt_exc
                        time.sleep(delay)
                        continue
            last_err = exc
            time.sleep(delay)
        except Exception as exc:
            last_err = exc
            time.sleep(delay)
    raise last_err


def fetch_and_parse(link, grades, cache_dir, refresh, timeout, retries, delay):
    cache_path = cache_dir / make_cache_filename(link)
    html = fetch_html(link, cache_path, refresh, timeout, retries, delay)

    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
    title = clean_text(strip_tags(title_match.group(1))) if title_match else ""
    country, cc, country_raw = parse_country(html)
    maker = extract_maker_from_title(title, grades)

    return {
        "link": link,
        "title": title or None,
        "maker": maker,
        "country": country,
        "cc": cc,
        "country_raw": country_raw,
    }


def write_dict_csv(path, rows, header):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in header})


def apply_updates(db_path, page_info):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, grade, standard, manufacturer, link
        FROM steel_grades
        WHERE link LIKE 'https://zknives.com/knives/steels/%'
        """
    )
    rows = cur.fetchall()

    updates = []
    missing = []

    for row_id, grade, standard, manufacturer, link in rows:
        info = page_info.get(link)
        if not info:
            missing.append({"grade": grade, "link": link})
            continue

        maker = info.get("maker")
        country = info.get("country")
        title = info.get("title")
        if not maker and not country:
            continue

        new_standard = build_standard_value(grade, maker, country, title)
        fields = {}

        if maker and maker != (manufacturer or ""):
            fields["manufacturer"] = maker

        if new_standard and new_standard != (standard or ""):
            fields["standard"] = new_standard

        if fields:
            set_clause = ", ".join([f"{key} = ?" for key in fields])
            values = list(fields.values()) + [row_id]
            cur.execute(f"UPDATE steel_grades SET {set_clause} WHERE id = ?", values)
            updates.append(
                {
                    "grade": grade,
                    "link": link,
                    "updated_fields": ",".join(fields.keys()),
                    "old_standard": standard or "",
                    "new_standard": new_standard or "",
                    "old_manufacturer": manufacturer or "",
                    "new_manufacturer": maker or "",
                    "country": country or "",
                }
            )

    conn.commit()
    conn.close()
    return updates, missing


def main():
    parser = argparse.ArgumentParser(description="Sync zknives page maker/country data to DB.")
    parser.add_argument("--db", default="database/steel_database.db", help="SQLite DB path")
    parser.add_argument("--report-dir", default="reports", help="Report directory")
    parser.add_argument("--cache-dir", default="reports/zknives_pages", help="Cache dir for pages")
    parser.add_argument("--refresh", action="store_true", help="Re-download pages even if cached")
    parser.add_argument("--workers", type=int, default=4, help="Number of fetch workers")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="Fetch retries")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between retries")
    parser.add_argument("--limit", type=int, default=0, help="Limit pages for debug")
    parser.add_argument("--missing-only", action="store_true", help="Fetch only pages missing from existing page info")
    parser.add_argument("--apply", action="store_true", help="Apply updates to DB")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = report_dir / "zknives_steelchart.html"

    if not cache_path.exists():
        raise SystemExit(f"Missing zknives cache: {cache_path}")

    link_grades = load_link_grades(cache_path)
    links = sorted(link_grades.keys())
    if args.limit:
        links = links[: args.limit]

    existing_info = {}
    if args.missing_only:
        page_info_path = report_dir / "zknives_page_info.csv"
        if page_info_path.exists():
            with page_info_path.open("r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    link = row.get("link")
                    if link:
                        existing_info[link] = row
        if existing_info:
            links = [link for link in links if link not in existing_info]

    results = []
    errors = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                fetch_and_parse,
                link,
                link_grades.get(link, []),
                cache_dir,
                args.refresh,
                args.timeout,
                args.retries,
                args.delay,
            ): link
            for link in links
        }

        total = len(futures)
        completed = 0
        for future in as_completed(futures):
            link = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                errors.append({"link": link, "error": str(exc)})
            completed += 1
            if completed % 100 == 0 or completed == total:
                print(f"Processed {completed}/{total}")

    page_info = {row["link"]: row for row in results}
    if existing_info:
        page_info = {**existing_info, **page_info}
        results = list(page_info.values())

    write_dict_csv(
        report_dir / "zknives_page_info.csv",
        results,
        ["link", "title", "maker", "country", "cc", "country_raw"],
    )
    write_dict_csv(
        report_dir / "zknives_page_errors.csv",
        errors,
        ["link", "error"],
    )

    print(f"Pages parsed: {len(results)}")
    print(f"Errors: {len(errors)}")

    if not args.apply:
        return

    updates, missing = apply_updates(args.db, page_info)

    write_dict_csv(
        report_dir / "zknives_page_updates.csv",
        updates,
        [
            "grade",
            "link",
            "updated_fields",
            "old_standard",
            "new_standard",
            "old_manufacturer",
            "new_manufacturer",
            "country",
        ],
    )
    write_dict_csv(
        report_dir / "zknives_page_missing.csv",
        missing,
        ["grade", "link"],
    )

    print(f"Updates: {len(updates)}")
    print(f"Missing page info: {len(missing)}")


if __name__ == "__main__":
    main()
