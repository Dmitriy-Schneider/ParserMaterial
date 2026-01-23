"""
Limited test: Update Standard for a few splav-kharkov grades
"""
import sys
from pathlib import Path
import time
import re
import sqlite3

sys.path.append(str(Path(__file__).parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser

# Get database connection
db_path = Path(__file__).parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get first 10 splav grades that need updating
cursor.execute("""
    SELECT grade, link, standard
    FROM steel_grades
    WHERE link LIKE '%splav%' AND (standard = 'GOST, Россия' OR grade = '4Х5МФС')
    ORDER BY id
    LIMIT 10
""")
grades_to_update = cursor.fetchall()

print(f"Testing update for {len(grades_to_update)} grades")
print("="*80)

parser = SplavKharkovParser()

updated = 0
skipped = 0
errors = 0

for i, (grade, link, current_standard) in enumerate(grades_to_update, 1):
    print(f"\n[{i}/{len(grades_to_update)}] Processing: {grade}")
    print(f"  Current Standard: {current_standard}")

    # Extract name_id from link
    match = re.search(r'name_id=(\d+)', link)
    if not match:
        print(f"  ERROR: No name_id in link")
        errors += 1
        continue

    name_id = int(match.group(1))

    try:
        # Parse grade page
        grade_data = parser.parse_grade_page(name_id, grade)

        if grade_data and grade_data['standard']:
            new_standard = grade_data['standard']
            print(f"  New Standard: {new_standard}")

            # Check if new is better
            has_gost_number = bool(re.search(r'ГОСТ\s+\d+', new_standard))
            current_has_number = bool(re.search(r'ГОСТ\s+\d+', current_standard))

            should_update = (new_standard != current_standard and
                           (has_gost_number or not current_has_number))

            if should_update:
                # Update database
                cursor.execute("UPDATE steel_grades SET standard = ? WHERE grade = ?",
                             (new_standard, grade))
                conn.commit()
                print(f"  [OK] UPDATED")
                updated += 1
            else:
                print(f"  [SKIP] No update needed")
                skipped += 1
        else:
            print(f"  [ERROR] Failed to parse")
            errors += 1

    except Exception as e:
        print(f"  [ERROR] {e}")
        errors += 1

    # Rate limiting
    time.sleep(2)

conn.close()

print("\n" + "="*80)
print("RESULTS:")
print("="*80)
print(f"Updated: {updated}")
print(f"Skipped: {skipped}")
print(f"Errors: {errors}")
