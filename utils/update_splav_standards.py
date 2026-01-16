"""
Update Standard column for splav-kharkov grades
Extracts GOST from chemistry section (not from other parts of page)
"""
import sys
from pathlib import Path
import time
import re

sys.path.append(str(Path(__file__).parent.parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser
import sqlite3

print("="*100)
print("UPDATING STANDARD COLUMN FOR SPLAV-KHARKOV GRADES")
print("="*100)
print("\nRe-parsing splav grades to get correct GOST from chemistry section")
print("Example: 4X5MFS should get GOST 5950, not GOST 1133-71\n")

# Get all splav grades
db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT grade, link, standard
    FROM steel_grades
    WHERE link LIKE '%splav%'
    ORDER BY id
""")
splav_grades = cursor.fetchall()

print(f"Found {len(splav_grades)} splav-kharkov grades")
print("\nStarting update...")

# Create parser
parser = SplavKharkovParser()

updated = 0
skipped = 0
errors = 0

for i, (grade, link, current_standard) in enumerate(splav_grades, 1):
    # Extract name_id from link
    match = re.search(r'name_id=(\d+)', link)
    if not match:
        print(f"[{i}/{len(splav_grades)}] ERROR: {grade} - no name_id in link")
        errors += 1
        continue

    name_id = int(match.group(1))

    try:
        # Parse grade page to get correct standard
        grade_data = parser.parse_grade_page(name_id, grade)

        if grade_data and grade_data['standard']:
            new_standard = grade_data['standard']

            # Check if different from current
            if new_standard != current_standard:
                # Update in database
                cursor.execute("UPDATE steel_grades SET standard = ? WHERE grade = ?",
                             (new_standard, grade))
                conn.commit()

                updated += 1
                if updated <= 20:  # Show first 20 changes
                    print(f"[{i}/{len(splav_grades)}] {grade}:")
                    print(f"    OLD: {current_standard}")
                    print(f"    NEW: {new_standard}")
            else:
                skipped += 1
        else:
            print(f"[{i}/{len(splav_grades)}] SKIP: {grade} - failed to parse standard")
            errors += 1

    except Exception as e:
        print(f"[{i}/{len(splav_grades)}] ERROR: {grade} - {e}")
        errors += 1

    # Rate limiting
    time.sleep(1)

    # Progress report every 100 grades
    if i % 100 == 0:
        print(f"\n{'='*100}")
        print(f"PROGRESS: {i}/{len(splav_grades)} processed")
        print(f"Updated: {updated}, Skipped (same): {skipped}, Errors: {errors}")
        print(f"{'='*100}\n")

conn.close()

print("\n" + "="*100)
print("COMPLETE")
print("="*100)
print(f"Total processed: {len(splav_grades)}")
print(f"Updated: {updated}")
print(f"Skipped (same standard): {skipped}")
print(f"Errors: {errors}")

# Show some examples of updated grades
print("\n" + "="*100)
print("VERIFICATION - Sample updated grades:")
print("="*100)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT grade, standard
    FROM steel_grades
    WHERE link LIKE '%splav%'
    ORDER BY RANDOM()
    LIMIT 10
""")

for grade, standard in cursor.fetchall():
    print(f"  {grade}: {standard}")

conn.close()
