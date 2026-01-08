import argparse
import csv
import sqlite3
from html.parser import HTMLParser
from pathlib import Path

from fix_ru_zknives_mismatches import latin_to_cyrillic_grade
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
}


def clean_text(value):
    if value is None:
        return ""
    text = value.replace("\xa0", " ").replace("*", "").strip()
    return " ".join(text.split())


def normalize_value(value):
    value = clean_text(value)
    if not value or value == "?":
        return None
    value = value.replace(",", ".")
    value = value.replace("?", "").replace(">=", "").replace("<=", "")
    value = value.strip()
    return value or None


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


class ZknivesTableParser(HTMLParser):
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
        if tag == "table" and self.in_table:
            self.in_table = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)
        if self.in_anchor:
            self.current_anchor.append(data)


def merge_analogues_value(existing, incoming):
    if incoming and (not existing or len(incoming) > len(existing)):
        return incoming
    return existing


def merge_zknives_record(existing, incoming):
    existing["analogues"] = merge_analogues_value(
        existing.get("analogues"),
        incoming.get("analogues"),
    )

    for key in (
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
        "maker",
        "cc",
        "country",
    ):
        if not existing.get(key) and incoming.get(key):
            existing[key] = incoming[key]

    return existing


def load_zknives_map(cache_path):
    html = cache_path.read_text(encoding="iso-8859-1")
    parser = ZknivesTableParser()
    parser.feed(html)
    records_by_key = {}

    index_map = {
        2: "base",
        3: "c",
        4: "cr",
        5: "mo",
        6: "v",
        7: "w",
        8: "co",
        9: "ni",
        10: "mn",
        11: "si",
        12: "s",
        13: "p",
        14: "cu",
        15: "nb",
        16: "n",
        17: "tech",
        18: "maker",
        19: "cc",
    }

    for entry in parser.entries:
        anchors = entry.get("anchors") or []
        if not anchors:
            continue

        cells = entry.get("cells") or []
        row_data = {}
        for idx, key in index_map.items():
            value = cells[idx] if idx < len(cells) else ""
            if key in ("base", "tech", "maker", "cc"):
                row_data[key] = clean_text(value) or None
            else:
                row_data[key] = normalize_value(value)

        cc = (row_data.get("cc") or "").upper()
        row_data["cc"] = cc or None
        row_data["country"] = CC_COUNTRY_MAP.get(cc)

        name_items = []
        seen_names = set()
        for anchor in anchors:
            name = clean_text(anchor.get("text"))
            if not name:
                continue
            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            name_items.append(
                {
                    "name": name,
                    "href": normalize_href(anchor.get("href")),
                }
            )

        names = [item["name"] for item in name_items]
        for item in name_items:
            grade = item["name"]
            link = canonical_link(item["href"])
            analogs = [n for n in names if n != grade]

            if cc == "RU":
                grade = latin_to_cyrillic_grade(grade)
                analogs = [latin_to_cyrillic_grade(a) for a in analogs]

            analogs_clean = []
            seen = set()
            for analog in analogs:
                if analog == grade:
                    continue
                key = analog.lower()
                if key in seen:
                    continue
                seen.add(key)
                analogs_clean.append(analog)

            record = {
                "grade": grade,
                "link": link,
                "analogues": " ".join(analogs_clean) if analogs_clean else None,
            }
            record.update(row_data)
            key = (grade, link)
            existing = records_by_key.get(key)
            if existing:
                merge_zknives_record(existing, record)
            else:
                records_by_key[key] = record

    return list(records_by_key.values())


def load_rows(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            grade = clean_text(row.get("grade", ""))
            if not grade:
                continue
            link = canonical_link(row.get("link", ""))
            rows.append(
                {
                    "grade": grade,
                    "maker": clean_text(row.get("zknives_maker", "")),
                    "cc": clean_text(row.get("cc", "")).upper(),
                    "country": clean_text(row.get("zknives_country", "")),
                    "link": link,
                    "source": path.name,
                }
            )
    return rows


def build_db_grade_maps(cursor):
    cursor.execute(
        """
        SELECT id, grade, link, standard, manufacturer, analogues, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n, tech
        FROM steel_grades
        """
    )
    rows = cursor.fetchall()
    by_grade_link = {}
    by_grade = {}
    by_link = {}
    cyr_map = {}
    collisions = set()

    for row in rows:
        row_id, grade, link_raw = row[0], row[1], row[2]
        link = canonical_link(link_raw)
        record = {
            "id": row_id,
            "grade": grade,
            "link": link or None,
            "standard": row[3],
            "manufacturer": row[4],
            "analogues": row[5],
            "base": row[6],
            "c": row[7],
            "cr": row[8],
            "mo": row[9],
            "v": row[10],
            "w": row[11],
            "co": row[12],
            "ni": row[13],
            "mn": row[14],
            "si": row[15],
            "s": row[16],
            "p": row[17],
            "cu": row[18],
            "nb": row[19],
            "n": row[20],
            "tech": row[21],
        }
        by_grade_link[(grade, link)] = record
        by_grade.setdefault(grade, []).append(record)
        if link:
            by_link.setdefault(link, []).append(record)

        cyr = latin_to_cyrillic_grade(grade)
        if cyr == grade:
            continue
        if cyr in cyr_map:
            collisions.add(cyr)
        else:
            cyr_map[cyr] = grade

    return by_grade_link, by_grade, by_link, cyr_map, collisions


def choose_analogues_value(existing, incoming):
    if not incoming:
        return existing
    if not existing:
        return incoming
    if incoming == existing:
        return existing
    if len(incoming) > len(existing):
        return incoming
    return existing


def should_update_field(existing, incoming):
    if incoming is None:
        return False
    if str(incoming).strip() == "":
        return False
    if existing is None:
        return True
    if str(existing).strip() == "":
        return True
    return False


def build_zknives_maps(records):
    by_key = {}
    by_grade = {}
    by_link = {}

    for record in records:
        link = canonical_link(record.get("link"))
        record["link"] = link or None
        key = (record["grade"], link)
        by_key[key] = record
        by_grade.setdefault(record["grade"], []).append(record)
        if link:
            by_link.setdefault(link, []).append(record)

    return by_key, by_grade, by_link


def build_grade_candidates(grade, cc, cyr_map, collisions):
    candidates = []

    def add(value):
        if value and value not in candidates:
            candidates.append(value)

    add(grade)
    if cc == "RU":
        cyr = latin_to_cyrillic_grade(grade)
        add(cyr)
        if grade in cyr_map and grade not in collisions:
            add(cyr_map[grade])
        if cyr in cyr_map and cyr not in collisions:
            add(cyr_map[cyr])

    return candidates


def resolve_record_by_link(by_link, link, grade_candidates=None):
    if not link:
        return None
    records = by_link.get(link) or []
    if not records:
        return None
    if grade_candidates:
        for grade in grade_candidates:
            for record in records:
                if record["grade"] == grade:
                    return record
    if len(records) == 1:
        return records[0]
    return None


def resolve_db_record(grade_candidates, link, by_grade_link, by_grade, by_link):
    if link:
        record = resolve_record_by_link(by_link, link, grade_candidates)
        if record:
            return record, "link"
        for grade in grade_candidates:
            record = by_grade_link.get((grade, link))
            if record:
                return record, "grade_link"

    for grade in grade_candidates:
        records = by_grade.get(grade) or []
        if records:
            if len(records) == 1:
                return records[0], "grade"
            return None, "grade_ambiguous"

    return None, "not_found"


def resolve_zknives_record(grade_candidates, link, by_key, by_grade, by_link):
    if link:
        record = resolve_record_by_link(by_link, link, grade_candidates)
        if record:
            return record
        for grade in grade_candidates:
            record = by_key.get((grade, link))
            if record:
                return record

    for grade in grade_candidates:
        records = by_grade.get(grade) or []
        if len(records) == 1:
            return records[0]

    return None


def write_csv(path, rows, header):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def write_dict_csv(path, rows, header):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in header})


def build_standard_value(grade, maker, cc, country=None):
    country = country or CC_COUNTRY_MAP.get(cc or "")
    if maker and country:
        return f"{maker}, {country}"
    if country:
        detection = detect_standard_pattern(grade, None, maker)
        standard_value = format_standard_value(
            detection,
            None,
            grade=grade,
            link=None,
            manufacturer=maker,
        )
        if standard_value and standard_value.endswith(country):
            return standard_value
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Apply zknives mismatches to DB and insert missing grades."
    )
    parser.add_argument("--db", default="database/steel_database.db", help="SQLite DB path")
    parser.add_argument("--report-dir", default="reports", help="Report directory")
    parser.add_argument("--apply", action="store_true", help="Apply updates to DB")
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    mismatches_path = report_dir / "zknives_mismatches.csv"
    missing_path = report_dir / "zknives_missing_in_db.csv"
    cache_path = report_dir / "zknives_steelchart.html"

    if not mismatches_path.exists():
        raise SystemExit(f"Missing mismatches report: {mismatches_path}")
    if not cache_path.exists():
        raise SystemExit(f"Missing zknives cache: {cache_path}")

    zknives_records = load_zknives_map(cache_path)
    z_by_key, z_by_grade, z_by_link = build_zknives_maps(zknives_records)

    rows = []
    seen = set()
    for path in (mismatches_path, missing_path):
        for row in load_rows(path):
            key = (row["grade"], row.get("link") or "")
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

    print(f"Zknives records: {len(zknives_records)}")
    if not args.apply:
        print(f"Rows loaded: {len(rows)}")
        return

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    by_grade_link, by_grade, by_link, cyr_map, collisions = build_db_grade_maps(cur)

    updates = []
    inserts = []
    unresolved = []

    composition_keys = [
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
    ]

    for row in rows:
        grade = row["grade"]
        cc = row["cc"]
        country = row["country"]
        maker = row["maker"]
        link = canonical_link(row.get("link"))

        grade_candidates = build_grade_candidates(grade, cc, cyr_map, collisions)
        db_record, db_note = resolve_db_record(
            grade_candidates,
            link,
            by_grade_link,
            by_grade,
            by_link,
        )
        z_record = resolve_zknives_record(
            grade_candidates,
            link,
            z_by_key,
            z_by_grade,
            z_by_link,
        )

        if not country:
            if cc:
                country = CC_COUNTRY_MAP.get(cc)
            elif z_record:
                country = z_record.get("country")

        if not db_record and db_note == "grade_ambiguous":
            unresolved.append(
                [grade, link or "", cc, country or "", "db_grade_ambiguous", row["source"]]
            )
            continue

        if db_record:
            fields = {}

            standard_value = build_standard_value(db_record["grade"], maker, cc, country)
            if maker and maker != (db_record.get("manufacturer") or ""):
                fields["manufacturer"] = maker
            if standard_value and standard_value != (db_record.get("standard") or ""):
                fields["standard"] = standard_value

            if z_record:
                for key in composition_keys:
                    if should_update_field(db_record.get(key), z_record.get(key)):
                        fields[key] = z_record.get(key)

                analogues_value = choose_analogues_value(
                    db_record.get("analogues"),
                    z_record.get("analogues"),
                )
                if analogues_value and analogues_value != db_record.get("analogues"):
                    fields["analogues"] = analogues_value

                new_link = z_record.get("link") or link
                if new_link and not db_record.get("link"):
                    new_link_key = canonical_link(new_link)
                    if (db_record["grade"], new_link_key) not in by_grade_link:
                        fields["link"] = new_link
                    else:
                        unresolved.append(
                            [grade, link or "", cc, country or "", "link_conflict", row["source"]]
                        )

            if fields:
                set_clause = ", ".join([f"{key} = ?" for key in fields])
                values = list(fields.values()) + [db_record["id"]]
                cur.execute(
                    f"UPDATE steel_grades SET {set_clause} WHERE id = ?",
                    values,
                )
                updates.append(
                    [
                        grade,
                        db_record["grade"],
                        link or "",
                        ",".join(fields.keys()),
                        row["source"],
                        db_note,
                    ]
                )
                for key, value in fields.items():
                    db_record[key] = value
                if "link" in fields:
                    link_key = canonical_link(fields["link"])
                    by_grade_link[(db_record["grade"], link_key)] = db_record
                    if link_key:
                        by_link.setdefault(link_key, []).append(db_record)
            continue

        if not z_record:
            unresolved.append(
                [grade, link or "", cc, country or "", "missing_in_zknives_cache", row["source"]]
            )
            continue

        insert_grade = z_record.get("grade") or (grade_candidates[0] if grade_candidates else grade)
        insert_link = z_record.get("link") or link or None
        insert_link_key = canonical_link(insert_link)
        if (insert_grade, insert_link_key) in by_grade_link:
            unresolved.append([grade, link or "", cc, country or "", "insert_conflict", row["source"]])
            continue

        standard_value = build_standard_value(insert_grade, maker, cc, country)
        analogues_value = z_record.get("analogues")

        cur.execute(
            """
            INSERT INTO steel_grades (
                grade, analogues, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n, tech,
                standard, manufacturer, link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                insert_grade,
                analogues_value,
                z_record.get("base"),
                z_record.get("c"),
                z_record.get("cr"),
                z_record.get("mo"),
                z_record.get("v"),
                z_record.get("w"),
                z_record.get("co"),
                z_record.get("ni"),
                z_record.get("mn"),
                z_record.get("si"),
                z_record.get("s"),
                z_record.get("p"),
                z_record.get("cu"),
                z_record.get("nb"),
                z_record.get("n"),
                z_record.get("tech"),
                standard_value,
                maker or None,
                insert_link,
            ),
        )
        inserts.append(
            [
                insert_grade,
                insert_link or "",
                standard_value or "",
                maker or "",
                len((analogues_value or "").split()),
                row["source"],
            ]
        )
        new_record = {
            "id": cur.lastrowid,
            "grade": insert_grade,
            "link": insert_link,
            "standard": standard_value,
            "manufacturer": maker or None,
            "analogues": analogues_value,
            "base": z_record.get("base"),
            "c": z_record.get("c"),
            "cr": z_record.get("cr"),
            "mo": z_record.get("mo"),
            "v": z_record.get("v"),
            "w": z_record.get("w"),
            "co": z_record.get("co"),
            "ni": z_record.get("ni"),
            "mn": z_record.get("mn"),
            "si": z_record.get("si"),
            "s": z_record.get("s"),
            "p": z_record.get("p"),
            "cu": z_record.get("cu"),
            "nb": z_record.get("nb"),
            "n": z_record.get("n"),
            "tech": z_record.get("tech"),
        }
        by_grade_link[(insert_grade, insert_link_key)] = new_record
        by_grade.setdefault(insert_grade, []).append(new_record)
        if insert_link_key:
            by_link.setdefault(insert_link_key, []).append(new_record)

    conn.commit()
    conn.close()

    write_csv(
        report_dir / "zknives_db_updates.csv",
        updates,
        ["grade", "db_grade", "link", "updated_fields", "source", "note"],
    )
    write_csv(
        report_dir / "zknives_db_inserts.csv",
        inserts,
        ["grade", "link", "standard", "manufacturer", "analogues_count", "source"],
    )
    write_csv(
        report_dir / "zknives_db_unresolved.csv",
        unresolved,
        ["grade", "link", "cc", "country", "reason", "source"],
    )

    print(f"Updates: {len(updates)}")
    print(f"Inserts: {len(inserts)}")
    print(f"Unresolved: {len(unresolved)}")


if __name__ == "__main__":
    main()
