"""
Update 4Х5МФС specifically to verify fix
"""
import sys
from pathlib import Path
import sqlite3
import re

sys.path.append(str(Path(__file__).parent))

from parsers.splav_kharkov_advanced import SplavKharkovParser

# Get database connection
db_path = Path(__file__).parent / 'database' / 'steel_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get 4Х5МФС
cursor.execute('SELECT grade, standard, link FROM steel_grades WHERE grade = ?', ('4Х5МФС',))
result = cursor.fetchone()

if not result:
    print("4Х5МФС not found in database")
    exit(1)

grade, current_standard, link = result

print(f"Grade: {grade}")
print(f"Current Standard: {current_standard}")
print(f"Link: {link}")
print("="*80)

# Extract name_id
match = re.search(r'name_id=(\d+)', link)
if not match:
    print("ERROR: No name_id in link")
    exit(1)

name_id = int(match.group(1))
print(f"Parsing name_id={name_id}...")

# Parse
parser = SplavKharkovParser()
grade_data = parser.parse_grade_page(name_id, grade)

if grade_data:
    print(f"\nNew Standard: {grade_data['standard']}")
    print(f"\nChemistry:")
    for element, value in sorted(grade_data['composition'].items()):
        print(f"  {element.upper()}: {value}")

    # Check if update needed
    new_standard = grade_data['standard']
    has_gost_number = bool(re.search(r'ГОСТ\s+\d+', new_standard))
    current_has_number = bool(re.search(r'ГОСТ\s+\d+', current_standard))

    should_update = (new_standard != current_standard and
                   (has_gost_number or not current_has_number))

    print("\n" + "="*80)
    if should_update:
        print("UPDATE NEEDED!")
        print(f"  Old: {current_standard}")
        print(f"  New: {new_standard}")

        # Update
        cursor.execute("UPDATE steel_grades SET standard = ? WHERE grade = ?",
                     (new_standard, grade))
        conn.commit()
        print("\n[OK] Database updated successfully")
    else:
        print("NO UPDATE NEEDED")
        print(f"  Current: {current_standard}")
        print(f"  Parsed: {new_standard}")
else:
    print("ERROR: Failed to parse grade page")

conn.close()
