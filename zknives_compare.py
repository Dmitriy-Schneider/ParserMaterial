import argparse
import csv
import re
import sqlite3
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

from utils.fill_standards_with_ai import (
    detect_standard_pattern,
    format_standard_value,
    is_valid_proprietary_result,
)

ZKNIVES_URL = "https://zknives.com/knives/steels/steelchart.php"
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
        return ""
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


def normalize_key(value):
    text = clean_text(value).lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def parse_standard_info(standard):
    if not standard:
        return None, None, None

    standard = standard.strip()
    if not standard:
        return None, None, None

    if "," in standard:
        standard_part, country = standard.rsplit(",", 1)
        standard_part = standard_part.strip()
        country = country.strip()
    else:
        standard_part = standard
        country = None

    upper_part = standard_part.upper()
    prefix = None
    for candidate in STANDARD_PREFIXES:
        if upper_part.startswith(candidate):
            prefix = candidate
            break

    if prefix:
        return "government", prefix, country

    return "proprietary", standard_part, country


class SteelTableParser(HTMLParser):
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
        if tag == "table" and attrs_dict.get("id") == "steelData":
            self.in_table = True
        if self.in_table and tag == "tr":
            self.in_row = True
            self.cell_index = -1
            self.current_cells = []
            self.anchor_items = []
        if self.in_row and tag in ("td", "th"):
            self.in_cell = True
            self.cell_index += 1
            self.current_cell = []
            if self.cell_index == 1:
                self.in_name_cell = True
        if self.in_name_cell and tag == "a":
            self.in_anchor = True
            self.current_anchor = []
            self.current_anchor_href = attrs_dict.get("href")

    def handle_endtag(self, tag):
        if tag == "table" and self.in_table:
            self.in_table = False
        if self.in_anchor and tag == "a":
            anchor_text = clean_text("".join(self.current_anchor))
            if anchor_text:
                self.anchor_items.append(
                    {
                        "text": anchor_text,
                        "href": self.current_anchor_href,
                    }
                )
            self.in_anchor = False
            self.current_anchor_href = None
        if self.in_cell and tag in ("td", "th"):
            cell_text = clean_text("".join(self.current_cell))
            self.current_cells.append(cell_text)
            self.in_cell = False
            if self.cell_index == 1:
                self.in_name_cell = False
        if self.in_row and tag == "tr":
            if self.anchor_items:
                self.entries.append(
                    {
                        "anchors": list(self.anchor_items),
                        "cells": list(self.current_cells),
                    }
                )
            self.in_row = False
            self.anchor_items = []

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)
        if self.in_anchor:
            self.current_anchor.append(data)


def fetch_html(cache_path, refresh):
    if cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="iso-8859-1")

    with urlopen(ZKNIVES_URL, timeout=30) as resp:
        html = resp.read().decode("iso-8859-1", errors="replace")
    cache_path.write_text(html, encoding="iso-8859-1")
    return html


def load_db_map(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, grade, link, standard, manufacturer FROM steel_grades")
    by_grade_link = {}
    by_grade = {}
    by_link = {}

    for row in cur.fetchall():
        link = canonical_link(row[2])
        record = {
            "id": row[0],
            "grade": row[1],
            "link": link or None,
            "standard": row[3],
            "manufacturer": row[4],
        }
        by_grade_link[(row[1], link)] = record
        by_grade.setdefault(row[1], []).append(record)
        if link:
            by_link.setdefault(link, []).append(record)

    conn.close()
    return by_grade_link, by_grade, by_link


def resolve_db_record(grade, link, by_grade_link, by_grade, by_link):
    link_key = canonical_link(link)
    if link_key:
        records = by_link.get(link_key) or []
        if records:
            if len(records) == 1:
                return records[0]
            for record in records:
                if record["grade"] == grade:
                    return record

    record = by_grade_link.get((grade, link_key))
    if record:
        return record

    records = by_grade.get(grade) or []
    if len(records) == 1:
        return records[0]

    return None


def write_csv(path, rows, header):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Compare zknives steel chart with local DB.")
    parser.add_argument("--db", default="database/steel_database.db", help="Path to SQLite DB")
    parser.add_argument("--report-dir", default="reports", help="Directory for report CSVs")
    parser.add_argument("--refresh", action="store_true", help="Re-download zknives HTML")
    parser.add_argument("--apply", action="store_true", help="Apply high-confidence updates to DB")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    cache_path = report_dir / "zknives_steelchart.html"

    html = fetch_html(cache_path, args.refresh)
    parser_html = SteelTableParser()
    parser_html.feed(html)

    records = {}
    for entry in parser_html.entries:
        cells = entry.get("cells") or []
        maker = clean_text(cells[18]) if len(cells) > 18 else ""
        cc = clean_text(cells[19]) if len(cells) > 19 else ""
        expected_country = CC_COUNTRY_MAP.get(cc)
        anchors = entry.get("anchors") or []
        for anchor in anchors:
            grade = clean_text(anchor.get("text"))
            if not grade:
                continue
            link = canonical_link(anchor.get("href"))
            key = (grade, link)
            existing = records.get(key)
            if existing:
                if not existing.get("maker") and maker:
                    existing["maker"] = maker
                if not existing.get("cc") and cc:
                    existing["cc"] = cc
                if not existing.get("country") and expected_country:
                    existing["country"] = expected_country
                continue
            records[key] = {
                "grade": grade,
                "link": link,
                "maker": maker,
                "cc": cc,
                "country": expected_country,
            }

    entries = list(records.values())
    by_grade_link, by_grade, by_link = load_db_map(args.db)

    mismatches = []
    missing = []
    unknown_cc = []
    updates = []

    if args.apply:
        conn = sqlite3.connect(args.db)
        cur = conn.cursor()

    for entry in entries:
        grade = entry.get("grade")
        link = entry.get("link") or ""
        maker = clean_text(entry.get("maker"))
        cc = clean_text(entry.get("cc"))
        expected_country = entry.get("country") or CC_COUNTRY_MAP.get(cc)

        if not expected_country:
            unknown_cc.append([grade, link, maker, cc])

        db_row = resolve_db_record(grade, link, by_grade_link, by_grade, by_link)
        if not db_row:
            missing.append([grade, link, maker, cc, expected_country])
            continue

        db_standard = db_row.get("standard")
        db_type, db_prefix_or_maker, db_country = parse_standard_info(db_standard)

        issues = []
        if not db_standard or not db_standard.strip():
            issues.append("missing_standard")
        else:
            if expected_country and db_country and expected_country != db_country:
                issues.append("country_mismatch")

            if maker:
                if db_type == "government":
                    issues.append("expected_proprietary_got_government")
                else:
                    if db_prefix_or_maker:
                        if normalize_key(db_prefix_or_maker) != normalize_key(maker):
                            issues.append("maker_mismatch")
            else:
                if db_type == "proprietary":
                    issues.append("expected_government_got_proprietary")

        if issues:
            mismatches.append([
                grade,
                link,
                maker,
                cc,
                expected_country,
                db_standard or "",
                db_country or "",
                db_type or "",
                ";".join(issues),
            ])

        if args.apply and (not db_standard or not db_standard.strip()):
            if expected_country:
                applied = False
                if maker:
                    is_valid, mfr, country = is_valid_proprietary_result(
                        maker,
                        expected_country,
                        grade=grade,
                        manufacturer=db_row.get("manufacturer"),
                    )
                    if is_valid:
                        cur.execute(
                            "UPDATE steel_grades SET standard = ?, manufacturer = COALESCE(manufacturer, ?) WHERE id = ?",
                            (f"{mfr}, {country}", mfr, db_row["id"]),
                        )
                        updates.append([grade, link, f"{mfr}, {country}", "zknives_maker"])
                        applied = True

                if not applied:
                    detection = detect_standard_pattern(grade, None, maker or db_row.get("manufacturer"))
                    standard_value = format_standard_value(
                        detection,
                        None,
                        grade=grade,
                        link=None,
                        manufacturer=maker or db_row.get("manufacturer"),
                    )
                    if standard_value and standard_value.endswith(expected_country):
                        cur.execute(
                            "UPDATE steel_grades SET standard = ? WHERE id = ?",
                            (standard_value, db_row["id"]),
                        )
                        updates.append([grade, link, standard_value, "pattern_match"])

    if args.apply:
        conn.commit()
        conn.close()

    write_csv(
        report_dir / "zknives_mismatches.csv",
        mismatches,
        ["grade", "link", "zknives_maker", "cc", "zknives_country", "db_standard", "db_country", "db_type", "issues"],
    )
    write_csv(
        report_dir / "zknives_missing_in_db.csv",
        missing,
        ["grade", "link", "zknives_maker", "cc", "zknives_country"],
    )
    write_csv(
        report_dir / "zknives_unknown_cc.csv",
        unknown_cc,
        ["grade", "link", "zknives_maker", "cc"],
    )
    write_csv(
        report_dir / "zknives_updates.csv",
        updates,
        ["grade", "link", "standard", "source"],
    )

    print(f"Parsed records: {len(entries)}")
    print(f"Mismatches: {len(mismatches)}")
    print(f"Missing in DB: {len(missing)}")
    print(f"Unknown CC: {len(unknown_cc)}")
    print(f"Updates applied: {len(updates)}")


if __name__ == "__main__":
    main()
