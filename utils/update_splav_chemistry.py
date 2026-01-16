"""
Update chemistry for all existing splav-kharkov grades
This script re-parses all splav grades to add missing chemistry
"""
import sqlite3
from pathlib import Path
import sys
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser
import re

print("="*100)
print("UPDATING CHEMISTRY FOR SPLAV-KHARKOV GRADES")
print("="*100)

# Create parser
parser = SplavKharkovParser()

# Get all splav grades from DB
db_path = Path(__file__).parent.parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT grade, link
    FROM steel_grades
    WHERE link LIKE '%splav%'
      AND (c IS NULL OR c = '')
""")
grades_to_update = cursor.fetchall()

conn.close()

print(f"\nFound {len(grades_to_update)} splav grades without chemistry")
print("\nStarting update process...")
print("This will take several hours (1 second per grade)\n")

updated = 0
errors = 0

for i, (grade, link) in enumerate(grades_to_update, 1):
    # Extract name_id from link
    match = re.search(r'name_id=(\d+)', link)
    if not match:
        print(f"[{i}/{len(grades_to_update)}] ERROR: {grade} - no name_id in link")
        errors += 1
        continue

    name_id = int(match.group(1))

    # Parse grade page
    try:
        grade_data = parser.parse_grade_page(name_id, grade)

        if grade_data and grade_data['composition']:
            grade_data['name_id'] = name_id
            success = parser.insert_grade(grade_data)

            if success:
                updated += 1
                if updated % 10 == 0:
                    print(f"[{i}/{len(grades_to_update)}] Updated {updated} grades so far...")
            else:
                print(f"[{i}/{len(grades_to_update)}] SKIP: {grade} - no chemistry found")
        else:
            print(f"[{i}/{len(grades_to_update)}] SKIP: {grade} - failed to parse")
            errors += 1

    except Exception as e:
        print(f"[{i}/{len(grades_to_update)}] ERROR: {grade} - {e}")
        errors += 1

    # Rate limiting
    time.sleep(1)

    # Save progress every 100 grades
    if i % 100 == 0:
        print(f"\n{'='*100}")
        print(f"PROGRESS: {i}/{len(grades_to_update)} processed")
        print(f"Updated: {updated}, Errors: {errors}")
        print(f"{'='*100}\n")

print("\n" + "="*100)
print("COMPLETE")
print("="*100)
print(f"Total processed: {len(grades_to_update)}")
print(f"Updated with chemistry: {updated}")
print(f"Errors: {errors}")
print(f"Skipped (no chemistry on site): {len(grades_to_update) - updated - errors}")
