"""Restore database from CSV export"""
import sqlite3
import csv
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
csv_path = Path(__file__).parent.parent / 'database' / 'steel_database_export_20251029_153843.csv'

print("="*100)
print("RESTORING DATABASE FROM CSV EXPORT")
print("="*100)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Clear existing data
print("\nClearing existing data...")
cursor.execute("DELETE FROM steel_grades")
conn.commit()

# Read CSV and import
print(f"\nReading CSV from: {csv_path}")

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter=';')

    rows = list(reader)
    print(f"Found {len(rows)} rows in CSV")

    imported = 0
    errors = 0

    for row in rows:
        try:
            # Parse values
            grade = row['grade']
            analogues = row['analogues'] if row['analogues'] else None
            base = row['base'] if row['base'] else None
            c = row['c'] if row['c'] else None
            cr = row['cr'] if row['cr'] else None
            mo = row['mo'] if row['mo'] else None
            v = row['v'] if row['v'] else None
            w = row['w'] if row['w'] else None
            co = row['co'] if row['co'] else None
            ni = row['ni'] if row['ni'] else None
            mn = row['mn'] if row['mn'] else None
            si = row['si'] if row['si'] else None
            s = row['s'] if row['s'] else None
            p = row['p'] if row['p'] else None
            cu = row['cu'] if row['cu'] else None
            nb = row['nb'] if row['nb'] else None
            n = row['n'] if row['n'] else None
            # other_elements stored in tech column
            tech = row['other_elements'] if row.get('other_elements') else None
            link = row['link'] if row['link'] else None

            # Insert
            cursor.execute('''
                INSERT INTO steel_grades
                (grade, analogues, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n, tech, link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (grade, analogues, base, c, cr, mo, v, w, co, ni, mn, si, s, p, cu, nb, n, tech, link))

            imported += 1

            if imported % 1000 == 0:
                print(f"  Imported {imported}/{len(rows)} rows...")

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error importing {row.get('grade', 'UNKNOWN')}: {e}")

conn.commit()

print(f"\n" + "="*100)
print("IMPORT COMPLETE")
print("="*100)
print(f"Total rows: {len(rows)}")
print(f"Imported: {imported}")
print(f"Errors: {errors}")

# Verify
cursor.execute("SELECT COUNT(*) FROM steel_grades")
total = cursor.fetchone()[0]
print(f"\nTotal grades in database: {total}")

# Check specific grades
print("\nVerifying specific grades:")
for grade_name in ['#20', 'Conqueror SuperClean', '1.2343']:
    cursor.execute("SELECT grade, analogues FROM steel_grades WHERE grade = ?", (grade_name,))
    r = cursor.fetchone()
    if r:
        ana_preview = r[1][:80] + "..." if r[1] and len(r[1]) > 80 else r[1]
        print(f"  {r[0]}: {ana_preview}")
    else:
        print(f"  {grade_name}: NOT FOUND")

conn.close()

print("\n" + "="*100)
print("DATABASE RESTORED")
print("="*100)
