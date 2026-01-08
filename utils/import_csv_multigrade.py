"""
Улучшенный импортер CSV с поддержкой множественных марок в одном поле
Разбивает марки, разделенные символами новой строки или *
"""
import csv
import sqlite3
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from database_schema import get_connection
import config


def clean_value(value):
    """Clean and normalize value"""
    if not value:
        return None

    value = value.strip()

    # Remove quotes
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]

    # Empty or placeholder values
    if value in ('', '-', 'N/A', 'n/a', '0', '0.00'):
        return None

    return value


def split_grades(grade_field):
    """
    Split multiple grades from single field
    Handles formats like: "A11*R0M2SF10*\nR0M2SF10-MP"
    """
    if not grade_field:
        return []

    # Replace newlines and * with |
    grade_field = grade_field.replace('\n', '|').replace('*', '|')

    # Split by |
    grades = [g.strip() for g in grade_field.split('|') if g.strip()]

    # Remove duplicates while preserving order
    seen = set()
    unique_grades = []
    for grade in grades:
        # Clean grade name
        grade = grade.strip('"').strip()
        if grade and grade not in seen and len(grade) > 1:
            seen.add(grade)
            unique_grades.append(grade)

    return unique_grades


def import_csv_with_multigrades(csv_path, source="Unknown"):
    """
    Import CSV with multiple grades per row
    """
    print(f"Importing {csv_path} with multigrade support...")

    if not os.path.exists(csv_path):
        print(f"ERROR: File not found: {csv_path}")
        return {"imported": 0, "skipped": 0, "errors": 0}

    conn = get_connection()
    cursor = conn.cursor()

    imported_count = 0
    skipped_count = 0
    error_count = 0

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # Detect delimiter
            first_line = f.readline()
            delimiter = ';' if ';' in first_line else ','
            f.seek(0)

            reader = csv.DictReader(f, delimiter=delimiter)

            for row_num, row in enumerate(reader, 1):
                try:
                    # Get all grades from this row
                    grade_field = row.get('Grade', '').strip()
                    grades = split_grades(grade_field)

                    if not grades:
                        skipped_count += 1
                        continue

                    # Prepare common data for all grades from this row
                    common_data = {
                        'base': clean_value(row.get('Base', 'Fe')),
                        'c': clean_value(row.get('C')),
                        'cr': clean_value(row.get('Cr')),
                        'mo': clean_value(row.get('Mo')),
                        'v': clean_value(row.get('V')),
                        'w': clean_value(row.get('W')),
                        'co': clean_value(row.get('Co')),
                        'ni': clean_value(row.get('Ni')),
                        'mn': clean_value(row.get('Mn')),
                        'si': clean_value(row.get('Si')),
                        's': clean_value(row.get('S')),
                        'p': clean_value(row.get('P')),
                        'cu': clean_value(row.get('Cu')),
                        'nb': clean_value(row.get('Nb')),
                        'n': clean_value(row.get('N')),
                        'tech': clean_value(row.get('Tech')),
                        'standard': source,
                        'manufacturer': clean_value(row.get('Maker')),
                        'link': None
                    }

                    # Build analogues list from other grades in the same row
                    analogues = ' '.join([g for g in grades[1:] if g])
                    if row.get('CC'):
                        cc = clean_value(row.get('CC'))
                        if cc:
                            analogues = (analogues + ' ' + cc).strip()

                    # Import first grade as main, others as analogues
                    main_grade = grades[0]

                    # Check if exists
                    cursor.execute("SELECT id FROM steel_grades WHERE grade = ?", (main_grade,))
                    if cursor.fetchone():
                        skipped_count += 1
                    else:
                        data = common_data.copy()
                        data['grade'] = main_grade
                        data['analogues'] = analogues if analogues else None

                        cursor.execute("""
                            INSERT INTO steel_grades (
                                grade, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n,
                                tech, standard, manufacturer, analogues, link
                            ) VALUES (
                                :grade, :base, :c, :cr, :mo, :v, :w, :co, :ni, :mn, :si, :s, :p, :cu, :nb, :n,
                                :tech, :standard, :manufacturer, :analogues, :link
                            )
                        """, data)

                        imported_count += 1

                        if imported_count % 1000 == 0:
                            print(f"  Imported {imported_count} grades...")

                    # Import other grades as separate entries (with main grade in analogues)
                    for alt_grade in grades[1:]:
                        cursor.execute("SELECT id FROM steel_grades WHERE grade = ?", (alt_grade,))
                        if cursor.fetchone():
                            skipped_count += 1
                        else:
                            data = common_data.copy()
                            data['grade'] = alt_grade
                            # Link to main grade
                            data['analogues'] = main_grade

                            cursor.execute("""
                                INSERT INTO steel_grades (
                                    grade, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n,
                                    tech, standard, manufacturer, analogues, link
                                ) VALUES (
                                    :grade, :base, :c, :cr, :mo, :v, :w, :co, :ni, :mn, :si, :s, :p, :cu, :nb, :n,
                                    :tech, :standard, :manufacturer, :analogues, :link
                                )
                            """, data)

                            imported_count += 1

                            if imported_count % 1000 == 0:
                                print(f"  Imported {imported_count} grades...")

                except Exception as e:
                    print(f"Error at row {row_num}: {e}")
                    error_count += 1
                    continue

            conn.commit()
            print(f"[OK] Imported: {imported_count}, Skipped: {skipped_count}, Errors: {error_count}")

    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        error_count += 1

    finally:
        conn.close()

    return {
        "imported": imported_count,
        "skipped": skipped_count,
        "errors": error_count
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Import CSV with multiple grades per row')
    parser.add_argument('file', help='CSV file to import')
    parser.add_argument('--source', '-s', default='CSV', help='Source/standard name')

    args = parser.parse_args()

    result = import_csv_with_multigrades(args.file, args.source)

    print(f"\n{'='*60}")
    print(f"FINAL RESULTS:")
    print(f"  Imported: {result['imported']:,}")
    print(f"  Skipped:  {result['skipped']:,}")
    print(f"  Errors:   {result['errors']:,}")
    print(f"{'='*60}")
